import base64
import binascii
from datetime import datetime, timezone
from decimal import Decimal as _Decimal
from pathlib import Path

from django.conf import settings
from django.db import transaction

from .models import (
    CONFIDENCE_THRESHOLD,
    Chromosome,
    Karyotype,
    PatientVault,
    Sample,
    SampleImage,
    SampleStatus,
)
from .iscn import IscnError, generate_iscn, validate_iscn
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
        if not is_draft:
            # Flujo real (DD-ML-002): segmentar la 1ª imagen con backend-ml e
            # ingestar el cariotipo. RN-07: si la IA cae, la muestra queda
            # persistida en PENDING_AI (sin cariotipo), no se rompe el flujo.
            raw = self._first_image_bytes(data.get('images', []))
            if raw is None:
                degraded = True
            else:
                try:
                    result = pipeline_client.segment_image(raw)
                    ingest_segmentation(sample, result)
                    sample.status = SampleStatus.READY
                    sample.save(update_fields=['status', 'updated_at'])
                except MLDegradedError:
                    degraded = True

        return {
            'id': str(sample.id),
            'chn_code': sample.chn_code,
            'sample_code': sample.sample_code,
            'status': sample.status,
            'task_id': None,
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
        """Persiste los bytes reales de cada imagen en MEDIA_ROOT (DD-ML-002 §2.1)
        para que backend-ml pueda segmentarlas (registro y reproceso)."""
        timestamp = int(datetime.now(timezone.utc).timestamp())
        created = 0
        for idx, img in enumerate(images):
            try:
                raw = self._decode_base64(img['data_base64'])
            except (binascii.Error, ValueError):
                continue
            rel_path = f'{chn_code}/{timestamp}_{idx}.img'
            abs_path = Path(settings.MEDIA_ROOT) / rel_path
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            abs_path.write_bytes(raw)
            SampleImage.objects.create(
                sample=sample, image_path=rel_path, order=idx, source=img['source'],
            )
            created += 1
        return created

    def _first_image_bytes(self, images: list) -> bytes | None:
        for img in images:
            try:
                return self._decode_base64(img['data_base64'])
            except (binascii.Error, ValueError):
                continue
        return None

    @staticmethod
    def _decode_base64(data_url: str) -> bytes:
        if ',' in data_url:
            data_url = data_url.split(',', 1)[1]
        return base64.b64decode(data_url, validate=False)


sample_registration_service = SampleRegistrationService()


# ============================================================================
# Ingesta de la segmentación de backend-ml (ADR-0007, DD-ML-002)
# ============================================================================

def ingest_segmentation(sample, result: dict) -> Karyotype:
    """Crea (o reemplaza) el Karyotype 1:1 + las filas Chromosome a partir del
    SegmentResult de backend-ml. RN-02: resolution_status derivado del umbral
    de confianza (naranja < 0.85 → PENDING). La semaforización sigue siendo
    derivada en lectura (no se persiste el color)."""
    with transaction.atomic():
        Karyotype.objects.filter(sample=sample).delete()  # 1:1 — reemplaza si reprocesa
        karyotype = Karyotype.objects.create(
            sample=sample,
            model_version=(result.get('model_version') or '')[:80],
        )
        per_class: dict[str, int] = {}
        for ch in result.get('chromosomes', []):
            cls = str(ch.get('predicted_class', ''))[:2]
            pos = per_class.get(cls, 0)
            per_class[cls] = pos + 1
            conf = ch.get('confidence_score')
            conf_dec = _Decimal(str(conf)) if conf is not None else None
            res_status = 'AUTO'
            if conf_dec is None:
                res_status = 'AUTO'  # rojo (null) — intervención manual, no naranja
            elif conf_dec < CONFIDENCE_THRESHOLD:
                res_status = 'PENDING'
            Chromosome.objects.create(
                karyotype=karyotype,
                predicted_class=cls,
                position_index=pos,
                confidence_score=conf_dec,
                bbox=ch.get('bbox', {}) or {},
                resolution_status=res_status,
                order=int(ch.get('order', 0)),
            )
    return karyotype


def reprocess_sample(sample) -> Karyotype:
    """Reprocesa la 1ª imagen almacenada de la muestra con backend-ml e ingesta
    el cariotipo (DD-ML-002). MLDegradedError si backend-ml no responde."""
    image = sample.images.order_by('order', 'captured_at').first()
    if image is None:
        raise MLDegradedError('sin imagen para procesar')
    abs_path = Path(settings.MEDIA_ROOT) / image.image_path
    if not abs_path.exists():
        raise MLDegradedError('imagen no encontrada en almacenamiento')
    result = pipeline_client.segment_image(abs_path.read_bytes(), filename=abs_path.name)
    return ingest_segmentation(sample, result)


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


def emit_audit_event(sample, actor, event_type, chromosome=None, payload=None, mode='auto') -> AuditEvent:
    """Emite un evento de auditoría encadenado (ADR-0022 D1). Debe llamarse
    DENTRO de una transacción atómica junto con la acción de dominio.

    `select_for_update` sobre el último evento del caso serializa dos
    acciones concurrentes sobre la misma sample (evita cadenas divergentes).
    `mode` marca las acciones hechas en modo degradado (FSD-UC-007 §7, BR-008).
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
        mode=mode,
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
    """Naranjas sin resolver + rojos (bloquean la emisión, RN-01/RN-02).

    Solo cuenta cromosomas activos (JOIN de P3 desactiva fragmentos absorbidos).
    """
    count = 0
    for c in karyotype.chromosomes.filter(is_active=True):
        sem = c.semaphore
        if sem == 'red':
            count += 1
        elif sem == 'orange' and c.resolution_status != 'RESOLVED':
            count += 1
    return count


def view_xai(sample, chromosome, actor, mode='auto') -> dict:
    """Registra XAI_VIEWED y marca el cromosoma como visto (gate BR-004).
    El heatmap Grad-CAM real lo genera el microservicio de inferencia
    (ADR-0007); acá se devuelve una referencia mock."""
    with transaction.atomic():
        if not chromosome.xai_viewed:
            chromosome.xai_viewed = True
            chromosome.save(update_fields=['xai_viewed'])
        emit_audit_event(
            sample, actor, AuditEventType.XAI_VIEWED, chromosome=chromosome,
            payload={'confidence_pre_xai': str(chromosome.confidence_score)}, mode=mode,
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


def resolve_chromosome(sample, chromosome, actor, mode='auto') -> Chromosome:
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
            payload={'predicted_class': chromosome.predicted_class}, mode=mode,
        )
    return chromosome


def mark_anomaly(sample, chromosome, actor, mode='auto') -> Chromosome:
    """Marca un cromosoma con anomalía estructural (M)."""
    with transaction.atomic():
        chromosome.is_anomaly = True
        chromosome.save(update_fields=['is_anomaly'])
        emit_audit_event(
            sample, actor, AuditEventType.MARK_ANOMALY, chromosome=chromosome,
            payload={'predicted_class': chromosome.predicted_class}, mode=mode,
        )
    return chromosome


def validate_case(sample, actor, mode='auto') -> Sample:
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
        emit_audit_event(sample, actor, AuditEventType.ANALYST_VALIDATED, mode=mode)
    return sample


# ============================================================================
# Cariotipo P3 (ADR-0021 P3, DD-KARYO-003) — corrección manual
# reclasificar (drag & drop) + separar / unir / resolver cruce
# ============================================================================

VALID_CHROMOSOME_CLASSES = frozenset(
    [str(n) for n in range(1, 23)] + ['X', 'Y']
)


class CaseLockedError(Exception):
    """Se intentó editar un caso que ya salió del analista (BR-003/FSD-UC-004)."""


class InvalidClassError(Exception):
    """Clase destino inválida para reclasificar (no es 1..22/X/Y)."""


class SameClassError(Exception):
    """La clase destino es igual a la actual (reclasificación sin efecto)."""


class JoinSelfError(Exception):
    """Se intentó unir un cromosoma consigo mismo."""


class CrossKaryotypeError(Exception):
    """Se intentó unir cromosomas de cariotipos distintos."""


def _assert_editable(sample) -> None:
    """Bloquea la edición si el caso ya fue validado por el analista o el
    supervisor (el caso salió del analista, BR-003)."""
    if sample.status in (SampleStatus.ANALYST_VALIDATED, SampleStatus.VALIDATED):
        raise CaseLockedError('El caso ya fue validado y no admite más correcciones.')


def reclassify_chromosome(sample, chromosome, target_class, actor, mode='auto') -> Chromosome:
    """Reclasifica un cromosoma a otro slot (override manual, BR-003).

    El analista es autoridad: la corrección marca el cromosoma como RESOLVED
    (deja de bloquear el caso aunque su confianza siga baja).
    """
    _assert_editable(sample)
    target = str(target_class)
    if target not in VALID_CHROMOSOME_CLASSES:
        raise InvalidClassError(f'Clase destino inválida: {target!r}')
    if target == chromosome.predicted_class:
        raise SameClassError('La clase destino es igual a la actual.')
    previous = chromosome.predicted_class
    with transaction.atomic():
        chromosome.predicted_class = target
        chromosome.resolution_status = 'RESOLVED'
        chromosome.save(update_fields=['predicted_class', 'resolution_status'])
        emit_audit_event(
            sample, actor, AuditEventType.CORRECT_CLASS, chromosome=chromosome,
            payload={'from': previous, 'to': target}, mode=mode,
        )
    return chromosome


def split_chromosome(sample, chromosome, actor, mode='auto') -> Chromosome:
    """Separa un cromosoma segmentado como uno solo (touching) en dos.

    El original conserva la mitad izquierda del bbox; el nuevo cromosoma toma
    la mitad derecha (misma clase, siguiente position_index). La reclasificación
    posterior de cada fragmento queda a criterio del analista.
    """
    _assert_editable(sample)
    bbox = dict(chromosome.bbox or {})
    x = bbox.get('x', 0)
    y = bbox.get('y', 0)
    w = bbox.get('w', 0)
    h = bbox.get('h', 0)
    half = w / 2 if w else 0
    with transaction.atomic():
        chromosome.bbox = {'x': x, 'y': y, 'w': half, 'h': h}
        chromosome.save(update_fields=['bbox'])
        siblings = chromosome.karyotype.chromosomes.filter(
            predicted_class=chromosome.predicted_class,
        )
        next_index = max((c.position_index for c in siblings), default=chromosome.position_index) + 1
        next_order = max((c.order for c in chromosome.karyotype.chromosomes.all()), default=chromosome.order) + 1
        created = Chromosome.objects.create(
            karyotype=chromosome.karyotype,
            predicted_class=chromosome.predicted_class,
            position_index=next_index,
            confidence_score=chromosome.confidence_score,
            bbox={'x': x + half, 'y': y, 'w': half, 'h': h},
            measures=dict(chromosome.measures or {}),
            resolution_status=chromosome.resolution_status,
            order=next_order,
        )
        emit_audit_event(
            sample, actor, AuditEventType.SPLIT, chromosome=chromosome,
            payload={'origin': str(chromosome.id), 'created': str(created.id)}, mode=mode,
        )
    return created


def join_chromosomes(sample, keep, absorbed, actor, mode='auto') -> Chromosome:
    """Une dos fragmentos en uno: `keep` toma la unión de ambos bbox y
    `absorbed` queda inactivo (soft-remove, preserva trazabilidad de audit)."""
    _assert_editable(sample)
    if keep.id == absorbed.id:
        raise JoinSelfError('No se puede unir un cromosoma consigo mismo.')
    if keep.karyotype_id != absorbed.karyotype_id:
        raise CrossKaryotypeError('Los cromosomas pertenecen a cariotipos distintos.')
    with transaction.atomic():
        keep.bbox = _bbox_union(keep.bbox, absorbed.bbox)
        keep.save(update_fields=['bbox'])
        absorbed.is_active = False
        absorbed.save(update_fields=['is_active'])
        emit_audit_event(
            sample, actor, AuditEventType.JOIN, chromosome=keep,
            payload={'kept': str(keep.id), 'absorbed': str(absorbed.id)}, mode=mode,
        )
    return keep


def resolve_cross(sample, chromosome, actor, mode='auto') -> Chromosome:
    """Individualiza un cromosoma cruzado/solapado: lo marca como resuelto."""
    _assert_editable(sample)
    with transaction.atomic():
        chromosome.resolution_status = 'RESOLVED'
        chromosome.save(update_fields=['resolution_status'])
        emit_audit_event(
            sample, actor, AuditEventType.RESOLVE_CROSS, chromosome=chromosome,
            payload={'predicted_class': chromosome.predicted_class}, mode=mode,
        )
    return chromosome


# ============================================================================
# Flujo del Supervisor S1 (ADR-0023 D2, DD-SUP-001) — auditoría del 5%
# ============================================================================

import math    # noqa: E402
import random  # noqa: E402
from decimal import Decimal  # noqa: E402

from django.utils import timezone as _tz  # noqa: E402

from .models import AuditDecision, AuditReview  # noqa: E402

AUDIT_CONFIDENCE_MIN = Decimal('0.86')  # RN-08: solo verdes de alta confianza (>86%)
AUDIT_FRACTION = 0.05


class NotAuditableError(Exception):
    """El caso no está en un estado auditable (debe ser ANALYST_VALIDATED)."""


class InvalidDecisionError(Exception):
    """Decisión de auditoría inválida (no es CONFIRMED/REJECTED)."""


def _audit_pool(karyotype):
    """Cromosomas activos con confianza > 0.86, ordenados de forma estable."""
    return sorted(
        [
            c for c in karyotype.chromosomes.filter(is_active=True)
            if c.confidence_score is not None and c.confidence_score > AUDIT_CONFIDENCE_MIN
        ],
        key=lambda c: str(c.id),
    )


def select_audit_sample(sample) -> list:
    """Selecciona (idempotente) el 5% aleatorio determinista de cromosomas de
    alta confianza para auditoría (RN-08, ADR-0023 D2) y materializa un
    `AuditReview` PENDING por cada uno. Reproducible: semilla = sample_id.

    Devuelve los AuditReview del caso (ordenados)."""
    karyotype = getattr(sample, 'karyotype', None)
    if karyotype is None:
        return []
    pool = _audit_pool(karyotype)
    if pool:
        n = max(1, math.ceil(AUDIT_FRACTION * len(pool)))
        rng = random.Random(str(sample.id))
        chosen = rng.sample(pool, n) if n <= len(pool) else pool
        with transaction.atomic():
            for chromo in chosen:
                AuditReview.objects.get_or_create(sample=sample, chromosome=chromo)
    return list(sample.audit_reviews.select_related('chromosome').all())


def decide_audit(sample, review, reviewer, decision, comment='') -> AuditReview:
    """Registra la decisión del Supervisor sobre un cromosoma auditado
    (Confirmar/Rechazar) y emite AUDIT_DECISION (ADR-0022)."""
    if sample.status != SampleStatus.ANALYST_VALIDATED:
        raise NotAuditableError('El caso debe estar validado por el analista para auditar.')
    if decision not in (AuditDecision.CONFIRMED, AuditDecision.REJECTED):
        raise InvalidDecisionError('La decisión debe ser CONFIRMED o REJECTED.')
    with transaction.atomic():
        review.decision = decision
        review.comment = comment or ''
        review.reviewer = reviewer
        review.decided_at = _tz.now()
        review.save(update_fields=['decision', 'comment', 'reviewer', 'decided_at'])
        emit_audit_event(
            sample, reviewer, AuditEventType.AUDIT_DECISION, chromosome=review.chromosome,
            payload={'decision': decision, 'comment': review.comment},
        )
    return review


def audit_summary(sample) -> dict:
    """Resumen del avance de auditoría del 5% para el caso."""
    reviews = list(sample.audit_reviews.all())
    return {
        'total': len(reviews),
        'pending': sum(1 for r in reviews if r.decision == AuditDecision.PENDING),
        'confirmed': sum(1 for r in reviews if r.decision == AuditDecision.CONFIRMED),
        'rejected': sum(1 for r in reviews if r.decision == AuditDecision.REJECTED),
    }


# ============================================================================
# Flujo del Supervisor S2 (ADR-0023 D3, DD-SUP-002) — firma MFA delegada
# ============================================================================

from datetime import timedelta  # noqa: E402

from .admin_client import admin_client  # noqa: E402
from .models import SignLockout  # noqa: E402

MFA_MAX_FAILS = 3
MFA_LOCKOUT_MINUTES = 15


class NotSignableError(Exception):
    """El caso no está en estado firmable (debe ser ANALYST_VALIDATED)."""


class SegregationError(Exception):
    """RN-06: el supervisor que firma no puede ser el analista del caso."""


class AuditIncompleteError(Exception):
    """Quedan cromosomas del 5% sin auditar antes de firmar (FSD-UC-005 A1)."""


class MfaLockedError(Exception):
    """Firma bloqueada por 3 fallos de MFA (FSD-UC-005 A2)."""


class MfaInvalidError(Exception):
    """Código MFA inválido."""


class MfaNotEnrolledError(Exception):
    """El supervisor no tiene 2FA habilitado en backend-admin."""


def _supervisor_email(user) -> str:
    return getattr(user, 'email', '') or getattr(user, 'username', '')


def sign_report(sample, supervisor, mfa_code) -> Sample:
    """Firma el reporte con MFA (FSD-UC-005). Valida en orden: estado firmable,
    segregación (RN-06), auditoría 5% completa, lockout, y por último el TOTP
    (delegado a backend-admin, ADR-0023 D3). Éxito → estado SIGNED + SIGN_REPORT.
    """
    if sample.status != SampleStatus.ANALYST_VALIDATED:
        raise NotSignableError('El caso debe estar validado por el analista para firmarse.')
    if supervisor.id == sample.analyst_id:
        raise SegregationError('El supervisor que firma no puede ser el analista del caso (RN-06).')
    if audit_summary(sample)['pending'] > 0:
        raise AuditIncompleteError('Debe revisar toda la auditoría del 5% antes de firmar.')

    now = _tz.now()
    lockout, _ = SignLockout.objects.get_or_create(user=supervisor)
    if lockout.locked_until and lockout.locked_until > now:
        raise MfaLockedError('Firma bloqueada por intentos fallidos de MFA. Reintente más tarde.')

    result = admin_client.verify_mfa(_supervisor_email(supervisor), mfa_code)  # MfaServiceError → 503
    if not result.get('enrolled'):
        raise MfaNotEnrolledError('El supervisor no tiene 2FA configurado.')
    if not result.get('valid'):
        lockout.failed_attempts += 1
        if lockout.failed_attempts >= MFA_MAX_FAILS:
            lockout.locked_until = now + timedelta(minutes=MFA_LOCKOUT_MINUTES)
            lockout.failed_attempts = 0
        lockout.save(update_fields=['failed_attempts', 'locked_until'])
        raise MfaInvalidError('Código MFA inválido.')

    with transaction.atomic():
        sample.status = SampleStatus.SIGNED
        sample.signed_by = supervisor
        sample.signed_at = now
        sample.save(update_fields=['status', 'signed_by', 'signed_at', 'updated_at'])
        emit_audit_event(sample, supervisor, AuditEventType.SIGN_REPORT, payload={'method': 'TOTP'})
        lockout.failed_attempts = 0
        lockout.locked_until = None
        lockout.save(update_fields=['failed_attempts', 'locked_until'])
    return sample


def _bbox_union(a: dict, b: dict) -> dict:
    """Rectángulo mínimo que contiene a ambos bbox {x,y,w,h}."""
    a = a or {}
    b = b or {}
    ax, ay, aw, ah = a.get('x', 0), a.get('y', 0), a.get('w', 0), a.get('h', 0)
    bx, by, bw, bh = b.get('x', 0), b.get('y', 0), b.get('w', 0), b.get('h', 0)
    x0 = min(ax, bx)
    y0 = min(ay, by)
    x1 = max(ax + aw, bx + bw)
    y1 = max(ay + ah, by + bh)
    return {'x': x0, 'y': y0, 'w': x1 - x0, 'h': y1 - y0}


# ============================================================================
# Narrativa asistida por LLM (ADR-0024) — IA generativa vía SDK
# ============================================================================


def generate_narrative(sample, actor, iscn: str, mode='auto') -> dict:
    """Genera y persiste el BORRADOR narrativo del informe (ADR-0024 D3).

    El LLM **no calcula el dato clínico**: recibe el `iscn` ya producido por la
    función determinística (ADR-0023 D4) y solo redacta el párrafo que lo
    acompaña. Por eso `iscn` es un parámetro y no algo que este servicio infiera.

    RN-07 — degradación limpia: si el LLM no responde, alucina o está apagado,
    se devuelve `{'generated': False, 'reason': ...}` y **no se lanza**. La
    narrativa nunca puede bloquear la emisión del informe.

    Devuelve {'generated': bool, 'text': str, 'reason': str|None}.
    """
    from .llm_client import LlmServiceError, llm_client

    if not iscn:
        return {'generated': False, 'text': '', 'reason': 'sin_iscn'}

    # `predicted_class` ya refleja las reclasificaciones del analista (P3 la
    # corrige en sitio), así que es la clase final. Solo cuenta los activos:
    # separar/unir desactiva cromosomas sin borrarlos.
    counts = {}
    karyotype = Karyotype.objects.filter(sample=sample).first()
    if karyotype:
        for chromo in Chromosome.objects.filter(karyotype=karyotype, is_active=True):
            if chromo.predicted_class:
                counts[chromo.predicted_class] = counts.get(chromo.predicted_class, 0) + 1

    try:
        result = llm_client.generate_narrative(
            iscn=iscn,
            sample_type=sample.sample_type or 'no especificado',
            chn_code=sample.chn_code,
            counts=counts,
        )
    except LlmServiceError as exc:
        # No se persiste nada ni se emite evento: no hubo narrativa que auditar.
        return {'generated': False, 'text': '', 'structured': None, 'reason': str(exc)}

    now = datetime.now(timezone.utc)
    with transaction.atomic():
        sample.narrative_draft = result['text']
        sample.narrative_model = result['model']
        sample.narrative_generated_at = now
        sample.save(update_fields=[
            'narrative_draft', 'narrative_model', 'narrative_generated_at', 'updated_at',
        ])
        emit_audit_event(
            sample, actor, AuditEventType.NARRATIVE_GENERATED,
            payload={
                'model': result['model'],
                'iscn_input': iscn,          # con qué dato se redactó
                'tokens': result['tokens'],
                'latency_ms': result['latency_ms'],
                'intentos': result.get('intentos', 1),   # cuántos hizo falta
                'es_normal': (result.get('structured') or {}).get('es_normal'),
                'anomalias_citadas': (result.get('structured') or {}).get('anomalias_citadas', []),
                # ADR-0028 D2: qué entradas del corpus fundamentaron el texto y
                # cuántas siguen sin firma clínica. Sin esto, un error en una
                # entrada sería irrastreable: no se sabría qué informes rehacer.
                'corpus_entradas': result.get('corpus_entradas', []),
                'corpus_sin_revisar': result.get('corpus_sin_revisar', 0),
                'is_draft': True,            # requiere revisión humana (D3)
            },
            mode=mode,
        )
    return {
        'generated': True,
        'text': result['text'],
        'structured': result.get('structured'),
        'reason': None,
    }


# ============================================================================
# Motor ISCN — fase S3 (ADR-0023 D4, ADR-0025)
# ============================================================================


class NotReportableError(Exception):
    """El caso no está en SIGNED: el ISCN se reporta DESPUÉS de la firma."""


class IscnAlreadyGeneratedError(Exception):
    """Ya tiene ISCN y no se justificó un override (RN-04: read-only)."""


def _conteo_por_clase(sample) -> dict[str, int]:
    """Conteo final por clase de los cromosomas ACTIVOS del caso.

    `predicted_class` ya refleja las reclasificaciones del analista (P3 corrige
    en sitio) y `is_active=False` marca los que separar/unir descartó — así que
    esto es el cariotipo tal como quedó tras la validación humana.
    """
    counts: dict[str, int] = {}
    karyotype = Karyotype.objects.filter(sample=sample).first()
    if karyotype:
        for chromo in Chromosome.objects.filter(karyotype=karyotype, is_active=True):
            if chromo.predicted_class:
                counts[chromo.predicted_class] = counts.get(chromo.predicted_class, 0) + 1
    return counts


def generate_case_iscn(sample, actor, override: str = '', justification: str = '',
                       mode='auto'):
    """Genera la nomenclatura ISCN del caso y lo pasa a REPORTED (ADR-0023 D4).

    Sin `override`: la calcula la función pura `generate_iscn()` sobre el conteo
    validado. Con `override`: el Supervisor impone su string, que se valida
    contra la gramática ISCN y **exige justificación** — es la autoridad médica,
    pero la decisión queda auditada.

    RN-04: `iscn_nomenclature` es read-only tras generarse. Regenerar sin
    justificar un override → IscnAlreadyGeneratedError.
    """
    if sample.status != SampleStatus.SIGNED:
        raise NotReportableError(
            f'el caso debe estar firmado (SIGNED) para reportarse; está en {sample.status}')

    if sample.iscn_nomenclature and not override:
        raise IscnAlreadyGeneratedError(
            'el caso ya tiene ISCN; para cambiarlo se requiere override justificado')

    original = generate_iscn(_conteo_por_clase(sample))   # puede lanzar IscnError

    if override:
        if not justification.strip():
            raise IscnError('el override requiere una justificación')
        final = validate_iscn(override)                   # puede lanzar IscnError
    else:
        final = original

    now = datetime.now(timezone.utc)
    with transaction.atomic():
        sample.iscn_nomenclature = final
        sample.iscn_generated_at = now
        sample.iscn_is_override = bool(override)
        sample.status = SampleStatus.REPORTED
        sample.save(update_fields=[
            'iscn_nomenclature', 'iscn_generated_at', 'iscn_is_override',
            'status', 'updated_at',
        ])
        if override:
            emit_audit_event(
                sample, actor, AuditEventType.ISCN_OVERRIDE,
                payload={
                    'original_iscn': original,
                    'final_iscn': final,
                    'justification': justification.strip(),
                },
                mode=mode,
            )
    return sample
