import httpx
import pytest

from apps.samples.pipeline_client import MLDegradedError, PipelineClient


def _client(**overrides):
    defaults = dict(base_url='http://localhost:9999', timeout=0.2, threshold=3, cooldown=60)
    defaults.update(overrides)
    return PipelineClient(**defaults)


class TestPipelineClient:
    def test_trigger_processing_success(self, monkeypatch):
        client = _client()

        class FakeResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return {'sample_id': 'x', 'task_id': 'abc', 'status': 'queued'}

        class FakeHttpxClient:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def post(self, *a, **kw):
                return FakeResponse()

        monkeypatch.setattr(httpx, 'Client', lambda **kw: FakeHttpxClient())
        result = client.trigger_processing('sample-1')
        assert result['task_id'] == 'abc'

    def test_trigger_processing_timeout_raises_degraded(self, monkeypatch):
        client = _client()

        class FakeHttpxClient:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def post(self, *a, **kw):
                raise httpx.TimeoutException('timeout')

        monkeypatch.setattr(httpx, 'Client', lambda **kw: FakeHttpxClient())
        with pytest.raises(MLDegradedError):
            client.trigger_processing('sample-1')

    def test_circuit_opens_after_threshold_failures(self, monkeypatch):
        client = _client(threshold=2)

        class FakeHttpxClient:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def post(self, *a, **kw):
                raise httpx.TimeoutException('timeout')

        monkeypatch.setattr(httpx, 'Client', lambda **kw: FakeHttpxClient())
        for _ in range(2):
            with pytest.raises(MLDegradedError):
                client.trigger_processing('sample-1')

        # 3er intento: circuito abierto, ni siquiera llama a httpx
        with pytest.raises(MLDegradedError, match='circuit_open'):
            client.trigger_processing('sample-1')

    def test_get_status_success(self, monkeypatch):
        client = _client()

        class FakeResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return {'sample_id': 'x', 'status': 'READY'}

        class FakeHttpxClient:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def get(self, *a, **kw):
                return FakeResponse()

        monkeypatch.setattr(httpx, 'Client', lambda **kw: FakeHttpxClient())
        result = client.get_status('sample-1')
        assert result['status'] == 'READY'

    def test_get_status_error_raises_degraded(self, monkeypatch):
        client = _client()

        class FakeHttpxClient:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def get(self, *a, **kw):
                raise httpx.ConnectError('refused')

        monkeypatch.setattr(httpx, 'Client', lambda **kw: FakeHttpxClient())
        with pytest.raises(MLDegradedError):
            client.get_status('sample-1')
