import base64
import binascii
from datetime import datetime, timezone

from django.db import transaction

from .models import PatientVault, Sample, SampleImage, SampleStatus
from .pipeline_client import MLDegradedError, pipeline_client


class ChnDuplicateError(Exception):
    pass


class SampleRegistrationService:
    """Orquesta el registro compuesto (ADR-0016 D7, SPEC-009 §5).

    Transacción atómica: Sample + PatientVault + N SampleImage.
    RN-07: si el pipeline está degradado, el registro se persiste igual.
    """

    def register(self, data: dict, user) -> dict:
        chn_code = data['sample']['chn_code']
        is_draft = data.get('is_draft', False)

        if Sample.objects.filter(chn_code=chn_code, is_active=True).exists():
            raise ChnDuplicateError(chn_code)

        with transaction.atomic():
            sample = self._create_sample(data, user, is_draft)
            self._create_patient_vault(data, chn_code)
            image_count = self._create_images(data.get('images', []), sample, chn_code)

        degraded = False
        task_id = None
        if not is_draft:
            try:
                result = pipeline_client.trigger_processing(str(sample.id))
                task_id = result.get('task_id')
            except MLDegradedError:
                degraded = True

        return {
            'id': str(sample.id),
            'chn_code': sample.chn_code,
            'sample_code': sample.sample_code,
            'status': sample.status,
            'task_id': task_id,
            'image_count': image_count,
            'degraded': degraded,
            'created_at': sample.created_at,
        }

    def _generate_sample_code(self) -> str:
        today = datetime.now(timezone.utc).strftime('%Y%m%d')
        prefix = f'BM-{today}-'
        count = Sample.objects.filter(sample_code__startswith=prefix).count()
        return f'{prefix}{count + 1:03d}'

    def _create_sample(self, data: dict, user, is_draft: bool) -> Sample:
        sample_data = data['sample']
        status = SampleStatus.DRAFT if is_draft else SampleStatus.PENDING_AI
        return Sample.objects.create(
            chn_code=sample_data['chn_code'],
            patient_ref=data['patient'].get('full_name', ''),
            status=status,
            analyst=user,
            sample_code=self._generate_sample_code(),
            sample_type=sample_data.get('sample_type', ''),
            culture_method=sample_data.get('culture_method', ''),
            collection_date=sample_data.get('collection_date'),
            reception_date=sample_data.get('reception_date'),
            requesting_doctor=sample_data.get('requesting_doctor', ''),
            department=sample_data.get('department', ''),
            analysis_requests=data.get('analysis_requests', []),
            metadata={'gender': sample_data.get('gender', '')},
        )

    def _create_patient_vault(self, data: dict, chn_code: str) -> PatientVault | None:
        patient = data.get('patient', {})
        history = data.get('clinical_history', {})
        if not patient.get('full_name'):
            return None
        return PatientVault.objects.create(
            chn_code=chn_code,
            full_name=patient.get('full_name', ''),
            birth_date=patient.get('birth_date', ''),
            document_id=patient.get('document_id', ''),
            phone=patient.get('phone', ''),
            indication=history.get('indication', ''),
            family_history=history.get('family_history', ''),
        )

    def _create_images(self, images: list, sample: Sample, chn_code: str) -> int:
        timestamp = int(datetime.now(timezone.utc).timestamp())
        created = 0
        for idx, img in enumerate(images):
            try:
                self._decode_base64(img['data_base64'])
            except (binascii.Error, ValueError):
                continue
            SampleImage.objects.create(
                sample=sample,
                image_path=f'{chn_code}/{timestamp}_{idx}.jpg',
                order=idx,
                source=img['source'],
            )
            created += 1
        return created

    @staticmethod
    def _decode_base64(data_url: str) -> bytes:
        if ',' in data_url:
            data_url = data_url.split(',', 1)[1]
        return base64.b64decode(data_url, validate=False)


sample_registration_service = SampleRegistrationService()


# ============================================================================
# Cariotipo P2 (ADR-0021 P2, ADR-0022, DD-KARYO-002) — XAI + resolución + audit
# ============================================================================

from .models import (  # noqa: E402
    AuditEvent,
    AuditEventType,
    Chromosome,
    Karyotype,
)


class XaiRequiredError(Exception):
    """Se intentó resolver un naranja sin haber consultado XAI (BR-004)."""


class NotOrangeError(Exception):
    """Se intentó resolver un cromosoma que no es naranja."""


class CaseBlockedError(Exception):
    """Se intentó validar el caso con naranjas sin resolver (RN-01)."""


def emit_audit_event(sample, actor, event_type, chromosome=None, payload=None) -> AuditEvent:
    """Emite un evento de auditoría encadenado (ADR-0022 D1). Debe llamarse
    DENTRO de una transacción atómica junto con la acción de dominio.

    `select_for_update` sobre el último evento del caso serializa dos
    acciones concurrentes sobre la misma sample (evita cadenas divergentes).
    """
    last = (
        AuditEvent.objects.select_for_update()
        .filter(sample=sample)
        .order_by('-created_at', '-id')
        .first()
    )
    event = AuditEvent(
        sample=sample,
        chromosome=chromosome,
        event_type=event_type,
        actor=actor,
        payload=payload or {},
        previous_hash=last.current_hash if last else '',
    )
    event.current_hash = event.compute_hash()
    event.save()
    return event


def verify_audit_chain(sample) -> bool:
    """Recorre la cadena del caso y verifica que cada hash sea consistente
    (integridad O(n), ADR-0022 D2)."""
    prev = ''
    for event in AuditEvent.objects.filter(sample=sample).order_by('created_at', 'id'):
        if event.previous_hash != prev:
            return False
        if event.current_hash != event.compute_hash():
            return False
        prev = event.current_hash
    return True


def _unresolved_count(karyotype: Karyotype) -> int:
    """Naranjas sin resolver + rojos (bloquean la emisión, RN-01/RN-02)."""
    count = 0
    for c in karyotype.chromosomes.all():
        sem = c.semaphore
        if sem == 'red':
            count += 1
        elif sem == 'orange' and c.resolution_status != 'RESOLVED':
            count += 1
    return count


def view_xai(sample, chromosome, actor) -> dict:
    """Registra XAI_VIEWED y marca el cromosoma como visto (gate BR-004).
    El heatmap Grad-CAM real lo genera el microservicio de inferencia
    (ADR-0007); acá se devuelve una referencia mock."""
    with transaction.atomic():
        if not chromosome.xai_viewed:
            chromosome.xai_viewed = True
            chromosome.save(update_fields=['xai_viewed'])
        emit_audit_event(
            sample, actor, AuditEventType.XAI_VIEWED, chromosome=chromosome,
            payload={'confidence_pre_xai': str(chromosome.confidence_score)},
        )
    return {
        'chromosome_id': str(chromosome.id),
        'predicted_class': chromosome.predicted_class,
        'confidence_score': str(chromosome.confidence_score) if chromosome.confidence_score is not None else None,
        # Heatmap mock (el ML service produce el real). PNG 1x1 rojo base64.
        'heatmap_base64': (
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='
        ),
    }


def resolve_chromosome(sample, chromosome, actor) -> Chromosome:
    """Resuelve (acepta) un cromosoma naranja. Exige XAI previo (BR-004)."""
    if chromosome.semaphore != 'orange':
        raise NotOrangeError('Solo los cromosomas naranja requieren resolución.')
    if not chromosome.xai_viewed:
        raise XaiRequiredError('Debe consultar la explicabilidad (XAI) antes de resolver.')
    with transaction.atomic():
        chromosome.resolution_status = 'RESOLVED'
        chromosome.save(update_fields=['resolution_status'])
        emit_audit_event(
            sample, actor, AuditEventType.ACCEPT_CHROMOSOME, chromosome=chromosome,
            payload={'predicted_class': chromosome.predicted_class},
        )
    return chromosome


def mark_anomaly(sample, chromosome, actor) -> Chromosome:
    """Marca un cromosoma con anomalía estructural (M)."""
    with transaction.atomic():
        chromosome.is_anomaly = True
        chromosome.save(update_fields=['is_anomaly'])
        emit_audit_event(
            sample, actor, AuditEventType.MARK_ANOMALY, chromosome=chromosome,
            payload={'predicted_class': chromosome.predicted_class},
        )
    return chromosome


def validate_case(sample, actor) -> Sample:
    """Transición a ANALYST_VALIDATED (FSD-UC-004). Rechaza si el caso está
    bloqueado por naranjas sin resolver (RN-01)."""
    karyotype = getattr(sample, 'karyotype', None)
    if karyotype is None:
        raise CaseBlockedError('La muestra no tiene cariotipo.')
    if _unresolved_count(karyotype) > 0:
        raise CaseBlockedError('Resuelva todos los cromosomas naranja antes de continuar.')
    with transaction.atomic():
        sample.status = SampleStatus.ANALYST_VALIDATED
        sample.save(update_fields=['status', 'updated_at'])
        emit_audit_event(sample, actor, AuditEventType.ANALYST_VALIDATED)
    return sample
