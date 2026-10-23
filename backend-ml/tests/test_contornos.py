"""DD-KARYO-007 D1 — Cada objeto lleva su silueta, no solo su caja.

Dos fuentes de contorno:
- la segmentación nueva: la región que watershed asignó a la detección;
- los casos antiguos, que solo tienen `bbox`: Otsu dentro de la caja
  (`contorno_en_caja` y `POST /api/v1/contours/`).

La prueba de que es una SILUETA y no la caja disfrazada: una elipse ocupa
pi/4 (~78 %) de su caja, así que el área del polígono tiene que quedar bastante
por debajo del área de la caja y cerca del área real del objeto.
"""
import json

import cv2
import numpy as np
from fastapi.testclient import TestClient

from app.classifier import PlaceholderClassifier
from app.main import MAX_CAJAS_CONTORNO, app
from app.pipeline import run_pipeline
from app.segmentation import contorno_de_mascara, contorno_en_caja, segment

client = TestClient(app)


def _area(poligono) -> float:
    return float(cv2.contourArea(np.array(poligono, dtype=np.int32)))


def _png(img) -> bytes:
    ok, buf = cv2.imencode('.png', img)
    assert ok
    return buf.tobytes()


def _una_elipse():
    """Fondo blanco y UNA elipse oscura inclinada 45°, con su caja exacta."""
    img = np.full((200, 200), 255, dtype=np.uint8)
    cv2.ellipse(img, (100, 100), (10, 40), 45, 0, 360, 40, -1)
    ys, xs = np.nonzero(img < 128)
    caja = (int(xs.min()), int(ys.min()), int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1))
    return img, caja, int(xs.size)


class TestContornoEnLaSegmentacion:
    def test_cada_deteccion_trae_su_silueta(self, synthetic_gray):
        dets = segment(synthetic_gray)
        assert len(dets) >= 10
        for d in dets:
            assert d.contour is not None and len(d.contour) >= 3

    def test_la_silueta_cae_dentro_de_su_caja(self, synthetic_gray):
        for d in segment(synthetic_gray):
            x, y, w, h = d.bbox
            for px, py in d.contour:
                assert x <= px <= x + w and y <= py <= y + h

    def test_es_la_silueta_y_no_la_caja(self, synthetic_gray):
        for d in segment(synthetic_gray):
            _, _, w, h = d.bbox
            area = _area(d.contour)
            assert area < 0.9 * w * h, 'el contorno ocupa toda la caja: es la caja, no la silueta'
            assert 0.75 * d.area <= area <= 1.25 * d.area, (area, d.area)

    def test_el_pipeline_entrega_el_contorno(self, synthetic_gray):
        res = run_pipeline(synthetic_gray, classifier=PlaceholderClassifier())
        assert all(c.contour for c in res.chromosomes)


class TestContornoEnCaja:
    def test_traza_la_elipse_dentro_de_su_caja(self):
        img, caja, pixeles = _una_elipse()
        contorno = contorno_en_caja(img, caja)
        assert contorno is not None
        assert 0.8 * pixeles <= _area(contorno) <= 1.2 * pixeles

    def test_acepta_imagen_en_color(self):
        img, caja, _ = _una_elipse()
        assert contorno_en_caja(cv2.cvtColor(img, cv2.COLOR_GRAY2BGR), caja) is not None

    def test_caja_fuera_de_la_imagen_da_none(self):
        img, _, _ = _una_elipse()
        assert contorno_en_caja(img, (190, 190, 40, 40)) is None
        assert contorno_en_caja(img, (-5, 10, 20, 20)) is None
        assert contorno_en_caja(img, (10, 10, 0, 20)) is None

    def test_zona_sin_tinta_da_none(self):
        img, _, _ = _una_elipse()
        assert contorno_en_caja(img, (0, 0, 30, 30)) is None  # esquina blanca y plana

    def test_casi_sin_tinta_da_none(self):
        img = np.full((100, 100), 255, dtype=np.uint8)
        img[50, 50] = 0  # una mota: no es un cromosoma
        img[10, 10] = 200
        assert contorno_en_caja(img, (0, 0, 100, 100)) is None


class TestContornoDeMascara:
    def test_mascara_vacia_da_none(self):
        assert contorno_de_mascara(np.zeros((20, 20), bool)) is None

    def test_un_solo_pixel_no_es_un_poligono(self):
        m = np.zeros((20, 20), np.uint8)
        m[10, 10] = 1
        assert contorno_de_mascara(m) is None

    def test_se_queda_con_la_mancha_mayor_y_desplaza(self):
        m = np.zeros((60, 60), np.uint8)
        cv2.rectangle(m, (5, 5), (8, 8), 1, -1)       # mota
        cv2.rectangle(m, (20, 20), (50, 40), 1, -1)   # el objeto
        contorno = contorno_de_mascara(m, 100, 200)
        xs = [p[0] for p in contorno]
        ys = [p[1] for p in contorno]
        assert min(xs) == 120 and max(xs) == 150
        assert min(ys) == 220 and max(ys) == 240


class TestEndpointContornos:
    def test_un_contorno_por_caja_y_en_orden(self):
        img, caja, _ = _una_elipse()
        cajas = [dict(zip('xywh', caja)), {'x': 0, 'y': 0, 'w': 30, 'h': 30}]
        r = client.post('/api/v1/contours/', files={'file': ('m.png', _png(img), 'image/png')},
                        data={'bboxes': json.dumps(cajas)})
        assert r.status_code == 200
        contornos = r.json()['contornos']
        assert len(contornos) == 2
        assert contornos[0] is not None and len(contornos[0]) >= 3
        assert contornos[1] is None  # sin tinta

    def test_una_caja_mal_formada_no_tumba_las_demas(self):
        img, caja, _ = _una_elipse()
        cajas = [{'x': 'a'}, dict(zip('xywh', caja))]
        r = client.post('/api/v1/contours/', files={'file': ('m.png', _png(img), 'image/png')},
                        data={'bboxes': json.dumps(cajas)})
        assert r.status_code == 200
        assert r.json()['contornos'][0] is None
        assert r.json()['contornos'][1] is not None

    def test_bboxes_que_no_es_json_da_400(self):
        img, _, _ = _una_elipse()
        r = client.post('/api/v1/contours/', files={'file': ('m.png', _png(img), 'image/png')},
                        data={'bboxes': 'no-json'})
        assert r.status_code == 400

    def test_bboxes_que_no_es_lista_de_cajas_da_400(self):
        img, _, _ = _una_elipse()
        r = client.post('/api/v1/contours/', files={'file': ('m.png', _png(img), 'image/png')},
                        data={'bboxes': json.dumps({'x': 1})})
        assert r.status_code == 400

    def test_demasiadas_cajas_da_400(self):
        img, _, _ = _una_elipse()
        cajas = [{'x': 0, 'y': 0, 'w': 5, 'h': 5}] * (MAX_CAJAS_CONTORNO + 1)
        r = client.post('/api/v1/contours/', files={'file': ('m.png', _png(img), 'image/png')},
                        data={'bboxes': json.dumps(cajas)})
        assert r.status_code == 400

    def test_archivo_vacio_da_400(self):
        r = client.post('/api/v1/contours/', files={'file': ('m.png', b'', 'image/png')},
                        data={'bboxes': '[]'})
        assert r.status_code == 400

    def test_lo_que_no_es_imagen_da_422(self):
        r = client.post('/api/v1/contours/', files={'file': ('m.png', b'no soy una imagen', 'image/png')},
                        data={'bboxes': '[]'})
        assert r.status_code == 422
