"""Tests del wiring backend-clinic ↔ backend-ml (ADR-0007, DD-ML-002).

`pipeline_client.segment_image` se mockea (no se necesita backend-ml corriendo):
se prueba la ingesta del SegmentResult a Karyotype/Chromosome, el flujo de
registro real y la degradación (RN-07).
"""
import base64
from decimal import Decimal

import pytest

from apps.samples import pipeline_client as pc_mod
from apps.samples.models import Chromosome, Karyotype, Sample
from apps.samples.pipeline_client import MLDegradedError
from apps.samples.services import (
    ingest_segmentation,
    reprocess_sample,
    sample_registration_service,
)

pytestmark = pytest.mark.django_db

B64_IMG = base64.b64encode(b'\xff\xd8\xff\xe0' + b'0' * 200).decode()

SEG_RESULT = {
    'model_version': 'opencv-watershed-v0+placeholder-clf-v0',
    'chromosomes': [
        {'order': 0, 'predicted_class': '1', 'confidence_score': 0.96, 'bbox': {'x': 1, 'y': 2, 'w': 3, 'h': 4}, 'area': 100},
        {'order': 1, 'predicted_class': '1', 'confidence_score': 0.55, 'bbox': {'x': 5, 'y': 6, 'w': 7, 'h': 8}, 'area': 90},
        {'order': 2, 'predicted_class': 'X', 'confidence_score': 0.55, 'bbox': {'x': 9, 'y': 9, 'w': 9, 'h': 9}, 'area': 80},
    ],
}


def _reg_data(chn, draft=False):
    return {
        'sample': {'chn_code': chn, 'gender': 'F'},
        'patient': {'full_name': 'ANON'},
        'clinical_history': {},
        'analysis_requests': [],
        'images': [{'data_base64': B64_IMG, 'source': 'upload'}],
        'is_draft': draft,
    }


class TestIngest:
    def test_creates_karyotype_and_chromosomes(self, analyst_user):
        s = Sample.objects.create(chn_code='CHN-2026-07-24-M001', analyst=analyst_user, status='PENDING_AI')
        k = ingest_segmentation(s, SEG_RESULT)
        assert Karyotype.objects.filter(sample=s).count() == 1
        assert k.chromosomes.count() == 3
        assert k.model_version.startswith('opencv-watershed')

    def test_resolution_status_derived_from_confidence(self, analyst_user):
        s = Sample.objects.create(chn_code='CHN-2026-07-24-M002', analyst=analyst_user, status='PENDING_AI')
        k = ingest_segmentation(s, SEG_RESULT)
        green = k.chromosomes.get(confidence_score=Decimal('0.96'))
        orange = k.chromosomes.filter(confidence_score=Decimal('0.55'))
        assert green.resolution_status == 'AUTO'
        assert all(c.resolution_status == 'PENDING' for c in orange)

    def test_position_index_per_class(self, analyst_user):
        s = Sample.objects.create(chn_code='CHN-2026-07-24-M003', analyst=analyst_user, status='PENDING_AI')
        k = ingest_segmentation(s, SEG_RESULT)
        pares_1 = sorted(c.position_index for c in k.chromosomes.filter(predicted_class='1'))
        assert pares_1 == [0, 1]

    def test_ingest_replaces_existing(self, analyst_user):
        s = Sample.objects.create(chn_code='CHN-2026-07-24-M004', analyst=analyst_user, status='READY')
        ingest_segmentation(s, SEG_RESULT)
        ingest_segmentation(s, {'model_version': 'x', 'chromosomes': SEG_RESULT['chromosomes'][:1]})
        assert Karyotype.objects.filter(sample=s).count() == 1
        assert Chromosome.objects.filter(karyotype__sample=s).count() == 1


class TestRegistrationFlow:
    def test_register_segments_and_ingests(self, analyst_user, monkeypatch):
        monkeypatch.setattr(pc_mod.pipeline_client, 'segment_image', lambda b, filename='m.bmp': SEG_RESULT)
        result = sample_registration_service.register(_reg_data('CHN-2026-07-24-M010'), analyst_user)
        assert result['status'] == 'READY'
        assert result['degraded'] is False
        s = Sample.objects.get(id=result['id'])
        assert getattr(s, 'karyotype', None) is not None
        assert s.karyotype.chromosomes.count() == 3

    def test_register_degraded_persists_without_karyotype(self, analyst_user, monkeypatch):
        def _boom(b, filename='m.bmp'):
            raise MLDegradedError('down')
        monkeypatch.setattr(pc_mod.pipeline_client, 'segment_image', _boom)
        result = sample_registration_service.register(_reg_data('CHN-2026-07-24-M011'), analyst_user)
        assert result['degraded'] is True
        s = Sample.objects.get(id=result['id'])
        assert s.status == 'PENDING_AI'
        assert getattr(s, 'karyotype', None) is None

    def test_draft_does_not_process(self, analyst_user, monkeypatch):
        called = {'n': 0}
        monkeypatch.setattr(pc_mod.pipeline_client, 'segment_image', lambda *a, **k: called.__setitem__('n', called['n'] + 1) or SEG_RESULT)
        result = sample_registration_service.register(_reg_data('CHN-2026-07-24-M012', draft=True), analyst_user)
        assert result['status'] == 'DRAFT'
        assert called['n'] == 0


class TestReprocess:
    def test_reprocess_reads_stored_image(self, analyst_user, monkeypatch):
        monkeypatch.setattr(pc_mod.pipeline_client, 'segment_image', lambda b, filename='m.bmp': SEG_RESULT)
        result = sample_registration_service.register(_reg_data('CHN-2026-07-24-M020'), analyst_user)
        s = Sample.objects.get(id=result['id'])
        # cambiar el mock y reprocesar debe leer la imagen guardada y re-ingestar
        monkeypatch.setattr(pc_mod.pipeline_client, 'segment_image', lambda b, filename='m.bmp': {'model_version': 'v2', 'chromosomes': SEG_RESULT['chromosomes'][:2]})
        k = reprocess_sample(s)
        assert k.chromosomes.count() == 2
        assert k.model_version == 'v2'

    def test_reprocess_without_image_degraded(self, analyst_user):
        s = Sample.objects.create(chn_code='CHN-2026-07-24-M021', analyst=analyst_user, status='READY')
        with pytest.raises(MLDegradedError):
            reprocess_sample(s)


class TestProcessEndpoint:
    def test_process_reprocesses_to_ready(self, analyst_client, analyst_user, monkeypatch):
        monkeypatch.setattr(pc_mod.pipeline_client, 'segment_image', lambda b, filename='m.bmp': SEG_RESULT)
        reg = sample_registration_service.register(_reg_data('CHN-2026-07-24-M030'), analyst_user)
        resp = analyst_client.post(f'/api/clinic/samples/{reg["id"]}/process/')
        assert resp.status_code == 200
        assert resp.data['status'] == 'READY'
        assert resp.data['chromosome_count'] == 3
