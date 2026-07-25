"""Tests de la API FastAPI (ADR-0007, DD-ML-001)."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get('/health/')
    assert r.status_code == 200
    body = r.json()
    assert body['status'] == 'ok'
    assert isinstance(body['trained_model'], bool)  # True con modelo entrenado, False con placeholder


def test_segment_endpoint(synthetic_png_bytes):
    # Agnóstico al clasificador (placeholder o EfficientNet entrenado).
    r = client.post('/api/v1/segment/', files={'file': ('meta.png', synthetic_png_bytes, 'image/png')})
    assert r.status_code == 200
    body = r.json()
    assert body['chromosome_count'] >= 10
    assert len(body['chromosomes']) == body['chromosome_count']
    assert 0.0 <= body['confidence_avg'] <= 1.0
    valid = [str(n) for n in range(1, 23)] + ['X', 'Y']
    c0 = body['chromosomes'][0]
    assert set(c0.keys()) >= {'order', 'predicted_class', 'confidence_score', 'bbox', 'area'}
    assert c0['predicted_class'] in valid


def test_segment_rechaza_vacio():
    r = client.post('/api/v1/segment/', files={'file': ('x.png', b'', 'image/png')})
    assert r.status_code == 400


def test_segment_rechaza_no_imagen():
    r = client.post('/api/v1/segment/', files={'file': ('x.png', b'basura', 'image/png')})
    assert r.status_code == 422
