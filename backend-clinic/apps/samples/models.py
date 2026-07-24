import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from .fields import EncryptedTextField

# Umbral único de semaforización (RN-02, ADR-0006 / ADR-0021 D2). Debe
# coincidir con ModelConfig.confidence_threshold del panel admin (ADR-0014 P3).
CONFIDENCE_THRESHOLD = Decimal('0.850')


class SampleStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Borrador'
    PENDING_AI = 'PENDING_AI', 'Pendiente de IA'
    PROCESSING = 'PROCESSING', 'En procesamiento'
    READY = 'READY', 'Listo'
    # Estados del flujo de validación de cariotipo (FSD-UC-004, ADR-0021 D3).
    # Declarados en P1; las transiciones se implementan en P2 (no inertes por
    # error: es una decisión documentada para evitar una 2da migración).
    BLOCKED_BY_CONFIDENCE = 'BLOCKED_BY_CONFIDENCE', 'Bloqueado por confianza'
    ANALYST_VALIDATED = 'ANALYST_VALIDATED', 'Validado por analista'
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
        max_length=24, choices=SampleStatus.choices, default=SampleStatus.PENDING_AI,
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


# ============================================================================
# Cariotipo (ADR-0021, DD-KARYO-001) — P1: modelo + semaforización derivada
# ============================================================================

CHROMOSOME_CLASSES = [(str(n), str(n)) for n in range(1, 23)] + [('X', 'X'), ('Y', 'Y')]


class ChromosomeResolution(models.TextChoices):
    AUTO = 'AUTO', 'Automático (verde)'      # confidence >= umbral
    PENDING = 'PENDING', 'Pendiente (naranja)'  # confidence < umbral, sin resolver
    RESOLVED = 'RESOLVED', 'Resuelto'         # naranja resuelto por analista (P2)


class Karyotype(models.Model):
    """Resultado del pipeline IA (U-Net + EfficientNet-B3) para una Sample.

    1:1 con Sample. El conteo esperado es 46 (23 pares) pero NO se fuerza:
    aneuploidías reales (+21, monosomías) tienen ≠46 cromosomas.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sample = models.OneToOneField(Sample, on_delete=models.CASCADE, related_name='karyotype')
    model_version = models.CharField(max_length=80, default='u-net-v2.1+efficientnet-b3-v1.4')
    image_path = models.CharField(max_length=512, blank=True, default='')
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'clinic_karyotypes'

    def __str__(self):
        return f'Karyotype({self.sample.chn_code})'


class Chromosome(models.Model):
    """Un cromosoma segmentado y clasificado dentro de un cariotipo.

    RN-02: la semaforización (verde/naranja/rojo) se DERIVA de
    confidence_score en tiempo de lectura (`semaphore`), no se persiste
    como campo — evita deriva si el umbral cambia (ADR-0021 D2).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    karyotype = models.ForeignKey(Karyotype, on_delete=models.CASCADE, related_name='chromosomes')
    predicted_class = models.CharField(max_length=2, choices=CHROMOSOME_CLASSES)
    position_index = models.IntegerField(default=0)  # copia dentro del par (0/1)
    # null = clasificación fallida → semáforo rojo (intervención manual, ADR-0006)
    confidence_score = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True)
    bbox = models.JSONField(default=dict, blank=True)      # {x,y,w,h} crop en la metafase (P3)
    measures = models.JSONField(default=dict, blank=True)  # {length_um, centromeric_index, band_count, quality}
    resolution_status = models.CharField(
        max_length=10, choices=ChromosomeResolution.choices, default=ChromosomeResolution.AUTO,
    )
    xai_viewed = models.BooleanField(default=False)  # gate FSD-UC-003 (P2)
    is_anomaly = models.BooleanField(default=False)  # marcador estructural (M), P2
    # P3 (DD-KARYO-003 §2.1): JOIN hace soft-remove del fragmento absorbido en
    # vez de DELETE físico, para no romper el FK SET_NULL de AuditEvent (RN-05).
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)           # orden estable de render

    class Meta:
        db_table = 'clinic_chromosomes'
        ordering = ['order', 'position_index']

    def __str__(self):
        return f'Chromosome({self.predicted_class}, conf={self.confidence_score})'

    @property
    def semaphore(self) -> str:
        """Verde ≥0.85, naranja <0.85, rojo si la clasificación falló."""
        if self.confidence_score is None:
            return 'red'
        return 'green' if self.confidence_score >= CONFIDENCE_THRESHOLD else 'orange'


# ============================================================================
# Audit Trail append-only (ADR-0022, DD-KARYO-002) — P2
# ============================================================================

import hashlib  # noqa: E402
import json     # noqa: E402


class AuditEventType(models.TextChoices):
    XAI_VIEWED = 'XAI_VIEWED', 'XAI consultado'
    ACCEPT_CHROMOSOME = 'ACCEPT_CHROMOSOME', 'Cromosoma aceptado'
    RECLASSIFY = 'RECLASSIFY', 'Reclasificado'          # P3
    CORRECT_CLASS = 'CORRECT_CLASS', 'Clase corregida'  # P3
    MARK_ANOMALY = 'MARK_ANOMALY', 'Anomalía marcada'
    SPLIT = 'SPLIT', 'Separado'                          # P3
    JOIN = 'JOIN', 'Unido'                              # P3
    RESOLVE_CROSS = 'RESOLVE_CROSS', 'Cruce resuelto'    # P3
    ANALYST_VALIDATED = 'ANALYST_VALIDATED', 'Validado por analista'
    AUDIT_DECISION = 'AUDIT_DECISION', 'Decisión de auditoría'  # futuro
    ISCN_OVERRIDE = 'ISCN_OVERRIDE', 'Override ISCN'            # futuro
    SIGN_REPORT = 'SIGN_REPORT', 'Reporte firmado'             # futuro


class AuditEventError(Exception):
    """Se intentó mutar un AuditEvent existente (RN-05 append-only)."""


class AuditEvent(models.Model):
    """Evento de auditoría inmutable con hash chain lineal SHA256 por-caso
    (ADR-0022 §D1/D2, materializa ADR-0008 Nivel 1 en Django).

    RN-05: append-only — `save()` rechaza cualquier UPDATE. El `current_hash`
    encadena contra el `current_hash` del evento anterior de la MISMA sample.
    NO instanciar directo: usar `services.emit_audit_event()` (calcula el
    encadenamiento bajo lock).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sample = models.ForeignKey(Sample, on_delete=models.CASCADE, related_name='audit_events')
    chromosome = models.ForeignKey(
        Chromosome, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_events',
    )
    event_type = models.CharField(max_length=20, choices=AuditEventType.choices)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='audit_events')
    payload = models.JSONField(default=dict, blank=True)
    # default=timezone.now (no auto_now_add): el service necesita created_at
    # poblado ANTES de save() para computar el hash de forma determinística.
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    previous_hash = models.CharField(max_length=64, blank=True, default='')
    current_hash = models.CharField(max_length=64, blank=True, default='')

    class Meta:
        db_table = 'clinic_audit_events'
        ordering = ['created_at']
        indexes = [models.Index(fields=['sample', 'created_at'])]

    def __str__(self):
        return f'AuditEvent({self.event_type}, sample={self.sample_id})'

    def compute_hash(self) -> str:
        """SHA256(canonical(fila sin hashes) || previous_hash). Determinístico:
        claves ordenadas, timestamp ISO-8601 UTC."""
        canonical = json.dumps({
            'sample': str(self.sample_id),
            'chromosome': str(self.chromosome_id) if self.chromosome_id else None,
            'event_type': self.event_type,
            'actor': self.actor_id,
            'payload': self.payload,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        return hashlib.sha256((canonical + self.previous_hash).encode('utf-8')).hexdigest()

    def save(self, *args, **kwargs):
        # RN-05: bloquea cualquier re-guardado (UPDATE) tras la creación.
        if not self._state.adding:
            raise AuditEventError('AuditEvent es append-only (RN-05): no se puede modificar.')
        super().save(*args, **kwargs)


# RBAC jerárquico (ADR-0019, DD-RBAC-001) — re-exportado para que Django
# los detecte como parte de esta app sin fusionar el archivo (models_rbac.py
# se mantiene separado por volumen: 7 modelos nuevos vs. los 3 existentes).
from .models_rbac import (  # noqa: E402,F401
    Grupo,
    Objeto,
    Opcion,
    PrivilegioGrupo,
    PrivilegioIndividual,
    TipoObjeto,
    UsuarioGrupo,
)
