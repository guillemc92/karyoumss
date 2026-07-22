"""
Modelos de apps/config (DD-ADMIN-002).

P0: skeleton con helper re-exportado.
P1: AdminProfile (este modelo).
P2: PasswordHistory (este archivo). two_factor_enabled/two_factor_secret/
    password_changed_at viven en apps.users.models.User, no acá.
P3: ModelConfig, ModelMetric (este archivo).
P4–P6: NotificationPreference, Integration, AppearancePreference — pendiente.
"""
import uuid
import re
from decimal import Decimal

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


# =============================================================================
# P2 — PasswordHistory (DD-ADMIN-002 §3.3)
# =============================================================================

class PasswordHistory(models.Model):
    """Historial de hashes de contraseña para forzar no-reutilización.

    services.py::rotate_password rechaza una nueva contraseña si su hash
    coincide con cualquiera de las últimas 5 entradas de este historial.
    """
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        'users.User', on_delete=models.CASCADE, related_name='password_history',
    )
    password_hash = models.CharField(max_length=128)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = _admin_schema_table('admin_password_history')
        indexes = [models.Index(fields=['user', '-changed_at'])]
        ordering = ['-changed_at']

    def __str__(self):
        return f'PasswordHistory<{self.user.email}, {self.changed_at}>'


# =============================================================================
# P3 — ModelConfig + ModelMetric (DD-ADMIN-002 §4)
# =============================================================================

ANALYSIS_MODE_CHOICES = [
    ('fast', 'Rápido (prioriza velocidad)'),
    ('balanced', 'Balanceado'),
    ('accurate', 'Precisión máxima (más lento)'),
]

LOG_LEVEL_CHOICES = [
    ('WARNING', 'Mínimo'),
    ('INFO', 'Normal'),
    ('DEBUG', 'Detallado'),
]

COMPLIANCE_THRESHOLD = Decimal('0.850')  # RN-02


class ModelConfig(models.Model):
    """
    Configuración activa del pipeline IA (U-Net + EfficientNet-B3, AGENTS
    §9 — nunca Mask R-CNN/ResNet50). Singleton lógico: `is_active=True`
    tiene un `UniqueConstraint` que garantiza a lo sumo 1 fila activa
    (protege contra race condition en creación concurrente, DD §4.2 nota
    de riesgo — el `get_or_create` de la vista además usa
    `select_for_update`).

    RN-02: `confidence_threshold` < 0.85 no bloquea, pero
    `ModelConfigSerializer.compliance_warning` lo señala para que la UI
    muestre un banner (el bloqueo real de emisión de reportes es RN-01/02
    a nivel de flujo clínico, no de esta configuración).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    is_active = models.BooleanField(default=True)

    unet_version = models.CharField(max_length=40, default='u-net-v2.1')
    unet_enabled = models.BooleanField(default=True)
    classifier_version = models.CharField(max_length=40, default='efficientnet-b3-v1.4')
    classifier_enabled = models.BooleanField(default=True)

    confidence_threshold = models.DecimalField(
        max_digits=4, decimal_places=3, default=Decimal('0.850'),
    )
    detection_sensitivity = models.DecimalField(
        max_digits=4, decimal_places=3, default=Decimal('0.500'),
    )
    analysis_mode = models.CharField(
        max_length=16, choices=ANALYSIS_MODE_CHOICES, default='balanced',
    )
    log_level = models.CharField(
        max_length=10, choices=LOG_LEVEL_CHOICES, default='INFO',
    )

    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='model_configs',
    )

    class Meta:
        db_table = _admin_schema_table('admin_model_config')
        constraints = [
            models.CheckConstraint(
                check=models.Q(confidence_threshold__gte=0) & models.Q(confidence_threshold__lte=1),
                name='admin_model_config_confidence_0_1',
            ),
            models.CheckConstraint(
                check=models.Q(detection_sensitivity__gte=0) & models.Q(detection_sensitivity__lte=1),
                name='admin_model_config_sensitivity_0_1',
            ),
            models.CheckConstraint(
                check=models.Q(analysis_mode__in=['fast', 'balanced', 'accurate']),
                name='admin_model_config_mode_valid',
            ),
            models.UniqueConstraint(
                fields=['is_active'],
                condition=models.Q(is_active=True),
                name='admin_model_config_single_active',
            ),
        ]

    def __str__(self):
        return f'ModelConfig<{self.unet_version}+{self.classifier_version}, active={self.is_active}>'

    @property
    def compliance_warning(self) -> bool:
        return self.confidence_threshold < COMPLIANCE_THRESHOLD


class ModelMetric(models.Model):
    """
    Snapshot append-only de precisión/rendimiento del pipeline IA
    (RN-05: Append-Only — sin PATCH/DELETE en el viewset). Cada fila la
    escribe el pipeline de entrenamiento/evaluación (fuera del alcance de
    este DD); `apps/config` solo expone lectura + un endpoint de escritura
    restringido a `IsAdminRole` para uso operativo/manual.
    """
    id = models.BigAutoField(primary_key=True)
    measured_at = models.DateTimeField(db_index=True)
    precision_overall = models.DecimalField(max_digits=5, decimal_places=4)
    precision_per_class = models.JSONField(default=dict, blank=True)
    recall_overall = models.DecimalField(max_digits=5, decimal_places=4)
    f1_overall = models.DecimalField(max_digits=5, decimal_places=4)
    latency_p50_ms = models.IntegerField()
    latency_p95_ms = models.IntegerField()
    latency_p99_ms = models.IntegerField()
    samples_evaluated = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = _admin_schema_table('admin_model_metrics')
        ordering = ['-measured_at']
        indexes = [models.Index(fields=['-measured_at'])]

    def __str__(self):
        return f'ModelMetric<{self.measured_at:%Y-%m-%d}, precision={self.precision_overall}>'
