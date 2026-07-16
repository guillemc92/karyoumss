"""Tests de SampleProcessView y SampleStatusView (SPEC-008 UC-S-006/UC-S-007).

POST /samples/{id}/process/ y GET /samples/{id}/status/ estaban fuera de
alcance según SPEC-008 §6.1 (redactado antes de que frontend-clinic los
consumiera), pero el frontend ya depende de ambos endpoints
(samplesClient.ts, useSampleMutations, useStatusPolling). Decisión
2026-07-16: implementarlos; §6.1 se corrige en la misma sesión.
"""
import httpx
import pytest
from django.urls import reverse

from apps.samples.models import Sample, SampleStatus
from apps.samples.pipeline_client import pipeline_client

pytestmark = pytest.mark.django_db


def _process_url(sample):
    return reverse('samples:sample-process', kwargs={'pk': sample.pk})


def _status_url(sample):
    return reverse('samples:sample-status', kwargs={'pk': sample.pk})


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
    """El circuit breaker vive en la instancia módulo-level pipeline_client;
    resetear entre tests para que un test no contamine al siguiente."""
    pipeline_client._failures = 0
    pipeline_client._circuit_open_until = 0.0
    yield
    pipeline_client._failures = 0
    pipeline_client._circuit_open_until = 0.0


class FakeHttpxClient:
    def __init__(self, response=None, raise_exc=None):
        self._response = response
        self._raise_exc = raise_exc

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def post(self, *a, **kw):
        if self._raise_exc:
            raise self._raise_exc
        return self._response

    def get(self, *a, **kw):
        if self._raise_exc:
            raise self._raise_exc
        return self._response


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class TestProcess:
    def test_analista_procesa_propia(self, analyst_client, own_sample, monkeypatch):
        fake = FakeHttpxClient(response=FakeResponse({'sample_id': str(own_sample.id), 'task_id': 'task-1', 'status': 'queued'}))
        monkeypatch.setattr(httpx, 'Client', lambda **kw: fake)

        resp = analyst_client.post(_process_url(own_sample), {'force_reprocess': False}, format='json')

        assert resp.status_code == 202
        assert resp.data['task_id'] == 'task-1'
        assert resp.data['status'] == 'queued'
        own_sample.refresh_from_db()
        assert own_sample.status == SampleStatus.PROCESSING

    def test_analista_no_procesa_ajena_403(self, analyst_client, other_sample):
        resp = analyst_client.post(_process_url(other_sample), {}, format='json')
        assert resp.status_code == 403
        assert resp.data['code'] == 'NOT_OWNER'

    def test_supervisor_procesa_cualquiera(self, supervisor_client, other_sample, monkeypatch):
        fake = FakeHttpxClient(response=FakeResponse({'sample_id': str(other_sample.id), 'task_id': 'task-2', 'status': 'queued'}))
        monkeypatch.setattr(httpx, 'Client', lambda **kw: fake)

        resp = supervisor_client.post(_process_url(other_sample), {}, format='json')
        assert resp.status_code == 202

    def test_ya_processing_409(self, analyst_client, own_sample):
        own_sample.status = SampleStatus.PROCESSING
        own_sample.save(update_fields=['status'])

        resp = analyst_client.post(_process_url(own_sample), {}, format='json')
        assert resp.status_code == 409
        assert resp.data['code'] == 'ALREADY_PROCESSING'

    def test_ml_degraded_503(self, analyst_client, own_sample, monkeypatch):
        fake = FakeHttpxClient(raise_exc=httpx.TimeoutException('timeout'))
        monkeypatch.setattr(httpx, 'Client', lambda **kw: fake)

        resp = analyst_client.post(_process_url(own_sample), {}, format='json')

        assert resp.status_code == 503
        assert resp.data['code'] == 'ML_DEGRADED'
        own_sample.refresh_from_db()
        assert own_sample.status == SampleStatus.PENDING_AI  # no se degrada el estado si el pipeline falló

    def test_no_existe_404(self, analyst_client):
        import uuid
        url = reverse('samples:sample-process', kwargs={'pk': uuid.uuid4()})
        resp = analyst_client.post(url, {}, format='json')
        assert resp.status_code == 404

    def test_anonimo_401(self, api_client, own_sample):
        resp = api_client.post(_process_url(own_sample), {}, format='json')
        assert resp.status_code == 401

    def test_force_reprocess_true_permite_desde_ready(self, analyst_client, own_sample, monkeypatch):
        own_sample.status = SampleStatus.READY
        own_sample.save(update_fields=['status'])
        fake = FakeHttpxClient(response=FakeResponse({'sample_id': str(own_sample.id), 'task_id': 'task-3', 'status': 'queued'}))
        monkeypatch.setattr(httpx, 'Client', lambda **kw: fake)

        resp = analyst_client.post(_process_url(own_sample), {'force_reprocess': True}, format='json')
        assert resp.status_code == 202


class TestStatus:
    def test_analista_ve_status_propia(self, analyst_client, own_sample, monkeypatch):
        fake = FakeHttpxClient(response=FakeResponse({'status': 'PROCESSING', 'progress': 0.5}))
        monkeypatch.setattr(httpx, 'Client', lambda **kw: fake)

        resp = analyst_client.get(_status_url(own_sample))

        assert resp.status_code == 200
        assert resp.data['status'] == 'PROCESSING'
        assert resp.data['progress'] == 0.5

    def test_analista_no_ve_status_ajena_403(self, analyst_client, other_sample):
        resp = analyst_client.get(_status_url(other_sample))
        assert resp.status_code == 403
        assert resp.data['code'] == 'NOT_OWNER'

    def test_status_ready_incluye_metricas(self, analyst_client, own_sample, monkeypatch):
        fake = FakeHttpxClient(response=FakeResponse({
            'status': 'READY', 'progress': 1, 'chromosome_count': 46, 'confidence_avg': 0.92,
        }))
        monkeypatch.setattr(httpx, 'Client', lambda **kw: fake)

        resp = analyst_client.get(_status_url(own_sample))

        assert resp.data['chromosome_count'] == 46
        assert resp.data['confidence_avg'] == 0.92

    def test_ml_degraded_503(self, analyst_client, own_sample, monkeypatch):
        fake = FakeHttpxClient(raise_exc=httpx.ConnectError('refused'))
        monkeypatch.setattr(httpx, 'Client', lambda **kw: fake)

        resp = analyst_client.get(_status_url(own_sample))

        assert resp.status_code == 503
        assert resp.data['code'] == 'ML_DEGRADED'

    def test_no_existe_404(self, analyst_client):
        import uuid
        url = reverse('samples:sample-status', kwargs={'pk': uuid.uuid4()})
        resp = analyst_client.get(url)
        assert resp.status_code == 404

    def test_anonimo_401(self, api_client, own_sample):
        resp = api_client.get(_status_url(own_sample))
        assert resp.status_code == 401
