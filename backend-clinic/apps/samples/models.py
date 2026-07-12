import uuid

from django.conf import settings
from django.db import models


class SampleStatus(models.TextChoices):
    PENDING_AI = 'PENDING_AI', 'Pendiente de IA'
    PROCESSING = 'PROCESSING', 'En procesamiento'
    READY = 'READY', 'Listo'
    VALIDATED = 'VALIDATED', 'Validado'
    REJECTED = 'REJECTED', 'Rechazado'


class Sample(models.Model):
    """Catálogo de muestras del bounded context clínico (ADR-0015).

    RN-04: iscn_nomenclature NO vive acá — la genera el FastAPI clínico.
    RN-05: edits NO vive acá — es tabla append-only del FastAPI clínico.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chn_code = models.CharField(max_length=20, unique=True)
    patient_ref = models.CharField(max_length=64)
    image_path = models.CharField(max_length=512, blank=True, default='')
    status = models.CharField(
        max_length=20, choices=SampleStatus.choices, default=SampleStatus.PENDING_AI,
    )
    analyst = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='samples_as_analyst',
    )
    supervisor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name='samples_as_supervisor',
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'clinic_samples'
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                check=~(models.Q(is_active=False) & models.Q(deleted_at__isnull=True)),
                name='samples_deactivated_implies_deleted_at',
            ),
        ]

    def __str__(self):
        return f'{self.chn_code} ({self.status})'
