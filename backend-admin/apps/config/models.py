"""
Modelos de apps/config (DD-ADMIN-002).

P0: skeleton con helper re-exportado.
P1: AdminProfile (este modelo).
P2–P6: PasswordHistory, ModelConfig, ModelMetric, NotificationPreference,
       Integration, AppearancePreference.
"""
import uuid
import re

from django.core.exceptions import ValidationError
from django.db import models

from apps.users.models import _admin_schema_table  # noqa: F401  (re-export)


EMAIL_RE = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
PHONE_RE = re.compile(r'^\+?[\d\s\-()]{6,30}$')


def _normalize_email(email: str) -> str:
    return (email or '').strip().lower()


def _validate_full_name(name: str) -> str:
    n = (name or '').strip()
    if len(n) < 3 or len(n) > 80:
        raise ValidationError({'full_name': 'Nombre 3-80 caracteres'})
    return n


def _validate_phone(phone: str) -> str:
    p = (phone or '').strip()
    if p and not PHONE_RE.match(p):
        raise ValidationError({'phone': 'Teléfono inválido'})
    return p


# =============================================================================
# P1 — AdminProfile
# =============================================================================

class AdminProfile(models.Model):
    """
    Datos de perfil visibles/editables por el propio usuario.
    Separado de AdminUser (que es la "cuenta institucional") y de
    User (auth Django). El FK user es OneToOne para que cada User
    tenga a lo sumo un perfil.

    Endpoints:
    - GET   /api/admin/me/profile/  → detalle (crea si no existe)
    - PATCH /api/admin/me/profile/  → edición parcial
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        'users.User',
        on_delete=models.CASCADE,
        related_name='profile',
    )
    full_name = models.CharField(max_length=80)
    email = models.EmailField()
    specialty = models.CharField(max_length=80, blank=True, default='')
    professional_license = models.CharField(max_length=40, blank=True, default='')
    phone = models.CharField(max_length=30, blank=True, default='')
    location = models.CharField(max_length=120, blank=True, default='')
    avatar_url = models.URLField(blank=True, default='')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = _admin_schema_table('admin_profiles')
        verbose_name = 'Perfil de usuario'
        verbose_name_plural = 'Perfiles de usuario'

    def clean(self):
        if self.full_name:
            self.full_name = _validate_full_name(self.full_name)
        if self.email:
            self.email = _normalize_email(self.email)
        if self.phone:
            self.phone = _validate_phone(self.phone)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Perfil<{self.user.email}>'
