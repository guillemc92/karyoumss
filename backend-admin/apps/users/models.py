"""
Modelos del bounded context admin (apps/users).

Dos modelos:

1. **User** — Django custom auth user. Username = email (mapeado desde FastAPI JWT).
   Se usa para DRF Token auth y django-auditlog tracking. Vive en schema 'admin'.

2. **AdminUser** — modelo de dominio (cuenta institucional). FK a User para los datos
   de auth, más campos específicos (full_name, role, active, deactivated_at, created_by).
   Es la "tabla" que se expone via /api/admin/users/* en el CRUD principal.

Decisión: separar User (auth) y AdminUser (dominio) evita acoplar el modelo de auth
de Django a la lógica de negocio. Si mañana cambia el auth (LDAP, OAuth), solo cambia User.

ADR-0012 §Decisión: schema 'admin' separado del clínico.
ADR-0013: stack Django + DRF.
FSD-UC-ADMIN-001: contrato funcional (no cambia).

db_table dinámico: en PostgreSQL usa `admin"."users_user` (producción, recomendado —
esquema 'admin' separado del clínico). En SQLite (tests) usa `users_user` plano.
La decisión se aplica en runtime consultando `connection.vendor` y NO en `Meta.db_table`
para que `makemigrations` no genere migrations rígidas por vendor.
"""

import re
import uuid

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from auditlog.registry import auditlog


# =============================================================================
# Constantes
# =============================================================================

EMAIL_RE = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
ROLE_CHOICES = [
    ('analista', 'Analista Citogenetista'),
    ('supervisor', 'Supervisor Clínico'),
    ('admin', 'Administrador TI'),
]
VALID_ROLES = [r for r, _ in ROLE_CHOICES]


def _normalize_email(email: str) -> str:
    return (email or '').strip().lower()


def _validate_full_name(name: str) -> str:
    n = (name or '').strip()
    if len(n) < 3 or len(n) > 80:
        raise ValidationError({'full_name': 'Nombre 3-80 caracteres'})
    return n


def _admin_schema_table(base_name: str) -> str:
    """
    Devuelve el nombre de tabla apropiado según el ENGINE de la DB configurada
    en settings.DATABASES (no en tiempo de query — eso es perezosamente correcto
    pero rompe `migrate` cuando la conexión aún no existe).

    Cómo decidimos el vendor sin conexión activa:
    - En producción, settings.DATABASES['default']['ENGINE'] es
      'django.db.backends.postgresql' → schema 'admin'.
    - En tests, settings_test.py sobreescribe con
      'django.db.backends.sqlite3' → tabla plana.
    - DJANGO_TEST_VENDOR_FORCE=sqlite permite forzar vendor plano en CI
      aunque el settings diga postgresql (workaround para devs sin Postgres local).

    Why no `connection.vendor` en runtime:
    - `Meta.db_table` se evalúa en tiempo de import, no por instancia. En ese
      momento `connection` no está necesariamente inicializado. Si usáramos
      `connection.vendor` y migramos con conexión a Postgres, la migración
      generada tendría el nombre plano; al volver a SQLite para tests, Django
      no recrearía la tabla porque el nombre cambió. Es un foot-gun.
    """
    from django.conf import settings
    import os
    forced = os.environ.get('DJANGO_TEST_VENDOR_FORCE', '').lower()
    if forced == 'sqlite':
        return base_name
    engine = settings.DATABASES.get('default', {}).get('ENGINE', '')
    if 'postgresql' in engine or 'postgres' in engine:
        # Comillas estilo Postgres: schema.table con identificadores seguros.
        return f'admin"."{base_name}'
    if 'mysql' in engine:
        return f'`admin`.`{base_name}`'
    # sqlite (default para tests) y otros vendors: nombre plano.
    return base_name


# =============================================================================
# User — custom auth user (Django auth)
# =============================================================================

class User(AbstractUser):
    """
    Custom user. Username = email (lowercase). Role sincronizado desde FastAPI JWT.

    No se crea por signup público: viene de /api/admin/auth/exchange.
    """
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=16, choices=ROLE_CHOICES, default='analista')

    # AbstractUser ya provee: username, first_name, last_name, password (no usado),
    # is_active, is_staff, is_superuser, date_joined, last_login.
    # Pero como nuestro flujo no usa password, redefinimos USERNAME_FIELD = email.

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']  # Para createsuperuser (Django admin CLI)

    class Meta:
        # db_table derivado del ENGINE configurado (ver _admin_schema_table).
        db_table = _admin_schema_table('users_user')
        verbose_name = 'Usuario (auth)'
        verbose_name_plural = 'Usuarios (auth)'

    def __str__(self):
        return f'{self.email} ({self.role})'

    def save(self, *args, **kwargs):
        # Normaliza email siempre
        if self.email:
            self.email = _normalize_email(self.email)
        if not self.username and self.email:
            self.username = self.email
        super().save(*args, **kwargs)


# =============================================================================
# AdminUser — modelo de dominio (cuenta institucional)
# =============================================================================

class AdminUser(models.Model):
    """
    Cuenta institucional gestionada por el Admin TI.

    Endpoints:
    - GET    /api/admin/users/                 → lista
    - POST   /api/admin/users/                 → alta
    - GET    /api/admin/users/{uuid}/          → detalle
    - PATCH  /api/admin/users/{uuid}/          → edición
    - DELETE /api/admin/users/{uuid}/          → soft-delete (set deactivated_at)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # FK al User de auth (1:1 lógico pero no enforced — un User puede existir sin AdminUser
    # si recién hizo exchange y aún no fue dado de alta como cuenta institucional)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='admin_profile',
        null=True,
        blank=True,
    )

    full_name = models.CharField(max_length=80)
    email = models.EmailField(unique=True)  # DB constraint UNIQUE LOWER(email) en migración raw
    role = models.CharField(max_length=16, choices=ROLE_CHOICES, default='analista')
    active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_users',
    )

    class Meta:
        # db_table derivado del ENGINE configurado (ver _admin_schema_table).
        db_table = _admin_schema_table('admin_users')
        verbose_name = 'Cuenta institucional'
        verbose_name_plural = 'Cuentas institucionales'
        constraints = [
            models.CheckConstraint(
                check=models.Q(role__in=VALID_ROLES),
                name='admin_users_role_valid',
            ),
            models.CheckConstraint(
                check=models.Q(deactivated_at__isnull=True) | models.Q(active=False),
                name='admin_users_deactivated_implies_inactive',
            ),
        ]
        indexes = [
            models.Index(
                fields=['active'],
                name='admin_users_active_idx',
                condition=models.Q(deactivated_at__isnull=True),
            ),
            models.Index(fields=['role'], name='admin_users_role_idx'),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.full_name} <{self.email}> ({self.role})'

    def clean(self):
        # Normalización (DD-ADMIN-001 §2 validaciones)
        if self.full_name:
            self.full_name = _validate_full_name(self.full_name)
        if self.email:
            self.email = _normalize_email(self.email)
        if self.role and self.role not in VALID_ROLES:
            raise ValidationError({'role': f'Rol inválido. Debe ser uno de: {VALID_ROLES}'})

    def save(self, *args, **kwargs):
        self.full_clean()  # Llama clean() + valida constraints del modelo
        super().save(*args, **kwargs)

    def soft_delete(self, actor: 'AdminUser' = None):
        """
        Soft-delete: setea deactivated_at y active=False. NO elimina la fila.

        Idempotente: si ya está desactivado, raise ValidationError.
        """
        if self.deactivated_at is not None:
            raise ValidationError('El usuario ya está desactivado')
        from django.utils import timezone
        self.deactivated_at = timezone.now()
        self.active = False
        if self.user:
            self.user.is_active = False
            self.user.save(update_fields=['is_active'])
        self.save(update_fields=['deactivated_at', 'active', 'updated_at'])

    def reactivate(self, actor: 'AdminUser' = None):
        """Reactivar un usuario soft-deleted."""
        if self.deactivated_at is None:
            raise ValidationError('El usuario no está desactivado')
        self.deactivated_at = None
        self.active = True
        if self.user:
            self.user.is_active = True
            self.user.save(update_fields=['is_active'])
        self.save(update_fields=['deactivated_at', 'active', 'updated_at'])


# =============================================================================
# Audit tracking (django-auditlog)
# =============================================================================

# Registra cambios en User y AdminUser. Append-Only vía LogEntry (apps.audit).
auditlog.register(
    User,
    include_fields=['email', 'role', 'is_active'],
)
auditlog.register(
    AdminUser,
    include_fields=['full_name', 'email', 'role', 'active', 'deactivated_at'],
)