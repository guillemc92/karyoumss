"""Contrato de /xai/ y /classify/ (DD-AUD-001 F1, issue #2).

Hasta `release/8.0.0` ninguna prueba los llamaba (main.py al 40 % de
cobertura). Al pasarlos a `def` y meterlos en el límite de inferencias se
tocan, así que se fija aquí lo que devuelven, con un clasificador falso para
no cargar el modelo real (~16 s) en cada prueba.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import app.gradcam as gradcam
import app.main as main
import app.pipeline as pipeline

client = TestClient(main.app)
CAJA = {'x': 100, 'y': 100, 'w': 30, 'h': 40}


class ClasificadorFalso:
    name = 'falso'

    def __init__(self, entrenado=True, resultados=(('7', 0.91),)):
        self.is_trained = entrenado
        self._resultados = list(resultados)

    def classify_all(self, gray, detecciones):
        return self._resultados


@pytest.fixture
def clasificador(monkeypatch):
    def usar(**kwargs):
        clf = ClasificadorFalso(**kwargs)
        monkeypatch.setattr(pipeline, '_classifier_singleton', clf)
        return clf
    return usar


def _post(ruta, png, **caja):
    return client.post(ruta, files={'file': ('m.png', png, 'image/png')},
                       data={**CAJA, **caja})


@pytest.mark.parametrize('ruta', ['/api/v1/xai/', '/api/v1/classify/'])
def test_imagen_ilegible_400(ruta):
    r = client.post(ruta, files={'file': ('m.png', b'no es imagen', 'image/png')}, data=CAJA)
    assert r.status_code == 400


@pytest.mark.parametrize('ruta', ['/api/v1/xai/', '/api/v1/classify/'])
def test_bbox_fuera_de_la_imagen_400(ruta, synthetic_png_bytes):
    r = _post(ruta, synthetic_png_bytes, x=10_000)
    assert r.status_code == 400
    assert 'fuera de la imagen' in r.json()['detail']


class TestClassify:
    def test_devuelve_la_clase_del_recorte(self, clasificador, synthetic_png_bytes):
        clasificador()
        r = _post('/api/v1/classify/', synthetic_png_bytes)
        assert r.status_code == 200
        cuerpo = r.json()
        assert (cuerpo['predicted_class'], cuerpo['confidence_score']) == ('7', 0.91)
        assert cuerpo['modelo'] == 'falso' and cuerpo['entrenado'] is True
        assert cuerpo['ref_h'] > 0

    def test_sin_resultado_del_clasificador_503(self, clasificador, synthetic_png_bytes):
        clasificador(resultados=())
        r = _post('/api/v1/classify/', synthetic_png_bytes)
        assert r.status_code == 503


class TestXai:
    def test_sin_modelo_entrenado_503(self, clasificador, synthetic_png_bytes):
        # No se devuelve un mapa vacío que parezca una explicación.
        clasificador(entrenado=False)
        r = _post('/api/v1/xai/', synthetic_png_bytes)
        assert r.status_code == 503
        assert 'no está entrenado' in r.json()['detail']

    def test_devuelve_mapa_y_resumen(self, clasificador, synthetic_png_bytes, monkeypatch):
        clasificador()
        monkeypatch.setattr(gradcam, 'heatmap_png', lambda clf, crop, ref_h: 'PNG64')
        monkeypatch.setattr(gradcam, 'resumen_activacion',
                            lambda clf, crop, ref_h: {'pico': 'centromero'})
        r = _post('/api/v1/xai/', synthetic_png_bytes)
        assert r.status_code == 200
        cuerpo = r.json()
        assert cuerpo['heatmap_base64'] == 'PNG64'
        assert cuerpo['activacion'] == {'pico': 'centromero'}
        assert cuerpo['metodo'] == 'grad-cam'

    def test_gradcam_no_disponible_503(self, clasificador, synthetic_png_bytes, monkeypatch):
        clasificador()

        def falla(clf, crop, ref_h):
            raise gradcam.GradCamNoDisponible('sin capa convolucional')
        monkeypatch.setattr(gradcam, 'heatmap_png', falla)
        r = _post('/api/v1/xai/', synthetic_png_bytes)
        assert r.status_code == 503
        assert 'sin capa convolucional' in r.json()['detail']
