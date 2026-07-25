"""Tests de SampleProcessView y SampleStatusView.

Actualizados a DD-ML-002: el procesamiento es SÍNCRONO (registro/process llaman
a backend-ml `/api/v1/segment/` e ingestan el cariotipo). `process` → 200 READY;
`status` es local (no consulta a la IA). `segment_image` se mockea.
"""
from decimal import Decimal
from pathlib import Path

import pytest
from django.conf import settings
from django.urls import reverse

from apps.samples.models import Chromosome, Karyotype, Sample, SampleImage, SampleStatus
from apps.samples.pipeline_client import pipeline_client

pytestmark = pytest.mark.django_db


def _process_url(sample):
    return reverse('samples:sample-process', kwargs={'pk': sample.pk})


def _status_url(sample):
    return reverse('samples:sample-status', kwargs={'pk': sample.pk})


SEG_RESULT = {
    'model_version': 'opencv-watershed-v0+placeholder-clf-v0',
    'chromosomes': [
        {'order': i, 'predicted_class': str((i % 22) + 1), 'confidence_score': 0.55,
         'bbox': {'x': i, 'y': i, 'w': 10, 'h': 20}, 'area': 100}
        for i in range(46)
    ],
}


def _add_image(sample):
    """Persiste una imagen (bytes cualquiera; segment_image se mockea) para que
    reprocess_sample tenga qué leer."""
    rel = f'{sample.chn_code}/img0.img'
    path = Path(settings.MEDIA_ROOT) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'\xff\xd8-fake-image-bytes')
    SampleImage.objects.create(sample=sample, image_path=rel, order=0, source='upload')


@pytest.fixture
def own_sample(analyst_user):
    return Sample.objects.create(
        chn_code='CHN-2026-07-16-0001', patient_ref='ANON-OWN', analyst=analyst_user,
        status=SampleStatus.PENDING_AI,
    )


@pytest.fixture
def other_sample(django_user_model):
    other = django_user_model.objects.create_user(username='other_analyst3', password='x')
    return Sample.objects.create(
        chn_code='CHN-2026-07-16-0002', patient_ref='ANON-OTHER', analyst=other,
        status=SampleStatus.PENDING_AI,
    )


@pytest.fixture(autouse=True)
def _reset_circuit_breaker():
    pipeline_client._failures = 0
    pipeline_client._circuit_open_until = 0.0
    yield
    pipeline_client._failures = 0
    pipeline_client._circuit_open_until = 0.0


def _mock_segment(monkeypatch, result=SEG_RESULT):
    monkeypatch.setattr(pipeline_client, 'segment_image', lambda b, filename='m.bmp': result)


class TestProcess:
    def test_analista_procesa_propia(self, analyst_client, own_sample, monkeypatch):
        _add_image(own_sample)
        _mock_segment(monkeypatch)
        resp = analyst_client.post(_process_url(own_sample), {}, format='json')
        assert resp.status_code == 200
        assert resp.data['status'] == 'READY'
        assert resp.data['chromosome_count'] == 46
        own_sample.refresh_from_db()
        assert own_sample.status == SampleStatus.READY

    def test_analista_no_procesa_ajena_403(self, analyst_client, other_sample):
        resp = analyst_client.post(_process_url(other_sample), {}, format='json')
        assert resp.status_code == 403
        assert resp.data['code'] == 'NOT_OWNER'

    def test_supervisor_procesa_cualquiera(self, supervisor_client, other_sample, monkeypatch):
        _add_image(other_sample)
        _mock_segment(monkeypatch)
        resp = supervisor_client.post(_process_url(other_sample), {}, format='json')
        assert resp.status_code == 200

    def test_ya_processing_409(self, analyst_client, own_sample):
        own_sample.status = SampleStatus.PROCESSING
        own_sample.save(update_fields=['status'])
        resp = analyst_client.post(_process_url(own_sample), {}, format='json')
        assert resp.status_code == 409
        assert resp.data['code'] == 'ALREADY_PROCESSING'

    def test_ml_degraded_503_sin_imagen(self, analyst_client, own_sample):
        # Sin imagen almacenada → reprocess_sample levanta MLDegradedError → 503.
        resp = analyst_client.post(_process_url(own_sample), {}, format='json')
        assert resp.status_code == 503
        assert resp.data['code'] == 'ML_DEGRADED'
        own_sample.refresh_from_db()
        assert own_sample.status == SampleStatus.PENDING_AI  # no se degrada el estado

    def test_no_existe_404(self, analyst_client):
        import uuid
        url = reverse('samples:sample-process', kwargs={'pk': uuid.uuid4()})
        resp = analyst_client.post(url, {}, format='json')
        assert resp.status_code == 404

    def test_anonimo_401(self, api_client, own_sample):
        resp = api_client.post(_process_url(own_sample), {}, format='json')
        assert resp.status_code == 401

    def test_reprocesa_desde_ready(self, analyst_client, own_sample, monkeypatch):
        own_sample.status = SampleStatus.READY
        own_sample.save(update_fields=['status'])
        _add_image(own_sample)
        _mock_segment(monkeypatch)
        resp = analyst_client.post(_process_url(own_sample), {}, format='json')
        assert resp.status_code == 200
        assert resp.data['chromosome_count'] == 46


class TestStatus:
    def test_analista_ve_status_propia(self, analyst_client, own_sample):
        resp = analyst_client.get(_status_url(own_sample))
        assert resp.status_code == 200
        assert resp.data['status'] == SampleStatus.PENDING_AI
        assert resp.data['chromosome_count'] == 0
        assert resp.data['progress'] == 0

    def test_analista_no_ve_status_ajena_403(self, analyst_client, other_sample):
        resp = analyst_client.get(_status_url(other_sample))
        assert resp.status_code == 403
        assert resp.data['code'] == 'NOT_OWNER'

    def test_status_ready_incluye_conteo(self, analyst_client, own_sample):
        own_sample.status = SampleStatus.READY
        own_sample.save(update_fields=['status'])
        k = Karyotype.objects.create(sample=own_sample)
        for i in range(46):
            Chromosome.objects.create(karyotype=k, predicted_class='1', confidence_score=Decimal('0.9'), order=i)
        resp = analyst_client.get(_status_url(own_sample))
        assert resp.data['status'] == 'READY'
        assert resp.data['chromosome_count'] == 46
        assert resp.data['progress'] == 1

    def test_no_existe_404(self, analyst_client):
        import uuid
        url = reverse('samples:sample-status', kwargs={'pk': uuid.uuid4()})
        resp = analyst_client.get(url)
        assert resp.status_code == 404

    def test_anonimo_401(self, api_client, own_sample):
        resp = api_client.get(_status_url(own_sample))
        assert resp.status_code == 401
