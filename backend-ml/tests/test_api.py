"""Tests de la API FastAPI (ADR-0007, DD-ML-001)."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get('/health/')
    assert r.status_code == 200
    body = r.json()
    assert body['status'] == 'ok'
    assert body['trained_model'] is False  # baseline, sin modelo entrenado


def test_segment_endpoint(synthetic_png_bytes):
    r = client.post('/api/v1/segment/', files={'file': ('meta.png', synthetic_png_bytes, 'image/png')})
    assert r.status_code == 200
    body = r.json()
    assert body['chromosome_count'] >= 10
    assert len(body['chromosomes']) == body['chromosome_count']
    assert body['confidence_avg'] < 0.85
    c0 = body['chromosomes'][0]
    assert set(c0.keys()) >= {'order', 'predicted_class', 'confidence_score', 'bbox', 'area'}


def test_segment_rechaza_vacio():
    r = client.post('/api/v1/segment/', files={'file': ('x.png', b'', 'image/png')})
    assert r.status_code == 400


def test_segment_rechaza_no_imagen():
    r = client.post('/api/v1/segment/', files={'file': ('x.png', b'basura', 'image/png')})
    assert r.status_code == 422
