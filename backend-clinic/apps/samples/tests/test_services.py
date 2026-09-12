import pytest

from apps.samples.models import PatientVault, Sample, SampleImage, SampleStatus
from apps.samples.services import ChnDuplicateError, sample_registration_service

VALID_IMAGE = 'data:image/jpeg;base64,aGVsbG8gd29ybGQ='


def _payload(**overrides):
    base = {
        'patient': {'full_name': 'ANON-TEST', 'birth_date': '1998-03-15', 'document_id': '', 'phone': ''},
        'sample': {'chn_code': 'CHN-2026-07-12-0001', 'sample_type': 'sangre', 'gender': 'M'},
        'clinical_history': {'indication': 'Estudio prenatal', 'family_history': ''},
        'analysis_requests': ['karyotype_high_res'],
        'images': [{'data_base64': VALID_IMAGE, 'source': 'camera'}] * 3,
        'is_draft': False,
    }
    base.update(overrides)
    return base


@pytest.mark.django_db
class TestSampleRegistrationService:
    def test_register_complete_creates_sample_and_vault(self, analyst_user):
        result = sample_registration_service.register(_payload(), analyst_user)
        assert result['status'] == SampleStatus.PENDING_AI
        assert result['image_count'] == 3
        sample = Sample.objects.get(id=result['id'])
        assert sample.chn_code == 'CHN-2026-07-12-0001'
        assert sample.sample_code.startswith('BM-')
        assert PatientVault.objects.filter(chn_code='CHN-2026-07-12-0001').exists()
        assert SampleImage.objects.filter(sample=sample).count() == 3

    def test_register_draft_only_requires_chn(self, analyst_user):
        payload = _payload(is_draft=True, patient={'full_name': '', 'birth_date': '', 'document_id': '', 'phone': ''}, images=[])
        result = sample_registration_service.register(payload, analyst_user)
        assert result['status'] == SampleStatus.DRAFT
        assert result['image_count'] == 0

    def test_register_draft_without_patient_skips_vault(self, analyst_user):
        payload = _payload(is_draft=True, patient={'full_name': '', 'birth_date': '', 'document_id': '', 'phone': ''}, images=[])
        sample_registration_service.register(payload, analyst_user)
        assert not PatientVault.objects.filter(chn_code='CHN-2026-07-12-0001').exists()

    def test_register_duplicate_chn_raises(self, analyst_user):
        sample_registration_service.register(_payload(), analyst_user)
        with pytest.raises(ChnDuplicateError):
            sample_registration_service.register(_payload(sample={'chn_code': 'CHN-2026-07-12-0001', 'sample_type': 'sangre', 'gender': 'M'}), analyst_user)

    def test_register_generates_sequential_sample_codes(self, analyst_user):
        r1 = sample_registration_service.register(_payload(), analyst_user)
        r2 = sample_registration_service.register(
            _payload(sample={'chn_code': 'CHN-2026-07-12-0002', 'sample_type': 'sangre', 'gender': 'F'}), analyst_user
        )
        assert r1['sample_code'] != r2['sample_code']

    def test_register_atomic_rollback_on_failure(self, analyst_user, monkeypatch):
        """Si falla la creación de imágenes tras crear Sample, la transacción revierte todo."""
        from apps.samples import services as services_module

        original = services_module.SampleRegistrationService._create_images

        def boom(self, *args, **kwargs):
            raise RuntimeError('simulated failure')

        monkeypatch.setattr(services_module.SampleRegistrationService, '_create_images', boom)
        with pytest.raises(RuntimeError):
            sample_registration_service.register(_payload(), analyst_user)
        assert not Sample.objects.filter(chn_code='CHN-2026-07-12-0001').exists()
        monkeypatch.setattr(services_module.SampleRegistrationService, '_create_images', original)

    def test_register_skips_malformed_image(self, analyst_user):
        payload = _payload(images=[
            {'data_base64': VALID_IMAGE, 'source': 'camera'},
            {'data_base64': 'not-valid-base64!!!', 'source': 'upload'},
            {'data_base64': VALID_IMAGE, 'source': 'upload'},
            {'data_base64': VALID_IMAGE, 'source': 'upload'},
        ])
        result = sample_registration_service.register(payload, analyst_user)
        assert result['image_count'] == 3


@pytest.mark.django_db
class TestCuantasMetafasesSeAnalizan:
    """ADR-0036: se guardan N metafases y se analiza UNA. Que se vea.

    Medido sobre 60 metafases reales de 10 muestras
    (`backend-ml/training/eval_multimetafase.py`): el 90 % no llega ni a
    producir una nomenclatura, asi que el consenso entre metafases no se puede
    construir todavia. Pero mientras no se construya, el sistema no puede dar a
    entender que mira las tres.

    Estos tests no arreglan la limitacion: la fijan. Si alguien quitara
    `analyzed_count`, o lo igualara a `image_count` sin analizar de verdad, se
    ponen rojos.
    """

    def test_se_guardan_tres_y_se_analiza_una(self, analyst_user, monkeypatch):
        from apps.samples import services

        monkeypatch.setattr(services.pipeline_client, 'segment_image',
                            lambda raw, **kw: {'chromosomes': []})

        resultado = sample_registration_service.register(_payload(), analyst_user)

        assert resultado['image_count'] == 3, 'las tres se guardan'
        assert resultado['analyzed_count'] == 1, 'pero solo se analiza una'
        assert resultado['analyzed_count'] < resultado['image_count']

    def test_si_la_ia_cae_no_se_analiza_ninguna(self, analyst_user, monkeypatch):
        """RN-07: la muestra se persiste igual, pero el contador dice la verdad.

        Un `analyzed_count` de 1 con el pipeline caido seria peor que no tener
        el campo: afirmaria un analisis que no ocurrio.
        """
        from apps.samples import services
        from apps.samples.pipeline_client import MLDegradedError

        def caido(*a, **kw):
            raise MLDegradedError('circuit_open')

        monkeypatch.setattr(services.pipeline_client, 'segment_image', caido)

        resultado = sample_registration_service.register(_payload(), analyst_user)

        assert resultado['degraded'] is True
        assert resultado['analyzed_count'] == 0
        assert resultado['image_count'] == 3, 'las imagenes no se pierden (RN-07)'

    def test_un_borrador_no_analiza_nada(self, analyst_user):
        payload = _payload(is_draft=True,
                           patient={'full_name': '', 'birth_date': '',
                                    'document_id': '', 'phone': ''},
                           images=[])
        resultado = sample_registration_service.register(payload, analyst_user)
        assert resultado['analyzed_count'] == 0
