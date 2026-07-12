import uuid

from django.conf import settings
from django.db import models

from .fields import EncryptedTextField


class SampleStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Borrador'
    PENDING_AI = 'PENDING_AI', 'Pendiente de IA'
    PROCESSING = 'PROCESSING', 'En procesamiento'
    READY = 'READY', 'Listo'
    VALIDATED = 'VALIDATED', 'Validado'
    REJECTED = 'REJECTED', 'Rechazado'


class SampleType(models.TextChoices):
    SANGRE = 'sangre', 'Sangre periférica'
    MEDULA = 'medula', 'Médula ósea'
    AMNIOTICO = 'amniotico', 'Líquido amniótico'
    VELLOSIDADES = 'vellosidades', 'Vellosidades coriales'


class Sample(models.Model):
    """Catálogo de muestras del bounded context clínico (ADR-0015, ADR-0016).

    RN-04: iscn_nomenclature NO vive acá — la genera el FastAPI clínico.
    RN-05: edits NO vive acá — es tabla append-only del FastAPI clínico.
    RN-03: datos de paciente (PII) viven en PatientVault, NO en este modelo.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chn_code = models.CharField(max_length=20, unique=True)
    patient_ref = models.CharField(max_length=64, blank=True, default='')
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

    # --- Campos del flujo de Registro (ADR-0016 D5, no-PII) ---
    sample_code = models.CharField(max_length=32, unique=True, null=True, blank=True)
    sample_type = models.CharField(max_length=20, choices=SampleType.choices, blank=True, default='')
    culture_method = models.CharField(max_length=64, blank=True, default='')
    collection_date = models.DateField(null=True, blank=True)
    reception_date = models.DateField(null=True, blank=True)
    requesting_doctor = models.CharField(max_length=128, blank=True, default='')
    department = models.CharField(max_length=128, blank=True, default='')
    analysis_requests = models.JSONField(default=list, blank=True)

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


class PatientVault(models.Model):
    """Bóveda cifrada de datos de paciente (ADR-0016 D2, ADR-0003, RN-03).

    Vinculada por chn_code (clave de negocio), NO por ForeignKey a Sample:
    evita que un select_related/serializer de Sample exponga PII por accidente.
    Sin endpoint GET/list — solo se escribe vía el flujo de Registro.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chn_code = models.CharField(max_length=20, unique=True)
    full_name = EncryptedTextField()
    birth_date = EncryptedTextField(blank=True, default='')
    document_id = EncryptedTextField(blank=True, default='')
    phone = EncryptedTextField(blank=True, default='')
    indication = EncryptedTextField(blank=True, default='')
    family_history = EncryptedTextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'clinic_patient_vault'

    def __str__(self):
        return f'PatientVault({self.chn_code})'


class SampleImageSource(models.TextChoices):
    CAMERA = 'camera', 'Cámara'
    UPLOAD = 'upload', 'Archivo subido'


class SampleImage(models.Model):
    """Galería de imágenes de metafase de una muestra (ADR-0016 D3)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sample = models.ForeignKey(Sample, on_delete=models.CASCADE, related_name='images')
    image_path = models.CharField(max_length=512)
    order = models.PositiveIntegerField(default=0)
    source = models.CharField(max_length=10, choices=SampleImageSource.choices)
    captured_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'clinic_sample_images'
        ordering = ['order', 'captured_at']

    def __str__(self):
        return f'SampleImage({self.sample_id}, order={self.order})'
