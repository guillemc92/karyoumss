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
