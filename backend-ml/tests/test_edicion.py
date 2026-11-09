"""DD-KARYO-007 D3 y D4 — Separar por línea y unir por máscara.

## El defecto que esto corrige

`split` partía la caja POR LA MITAD vertical, fuera cual fuera la frontera
entre los dos cromosomas. La prueba central lo reproduce: dos cromosomas que se
tocan a lo largo de una DIAGONAL. Cortar por la mitad da dos trozos que mezclan
píxeles de los dos; cortar por la línea trazada sobre la diagonal devuelve
cada cromosoma con su área.

Imágenes sintéticas (fondo blanco, objetos oscuros): lo que se prueba es la
geometría del corte, no la segmentación.
"""
import json

import cv2
import numpy as np
from fastapi.testclient import TestClient

from app.edicion import GROSOR_CORTE, MIN_AREA_TROZO, CorteInvalidoError, cortar, mascara_de_objeto, unir
from app.main import app

client = TestClient(app)

import pytest  # noqa: E402


def _area(poligono) -> float:
    return float(cv2.contourArea(np.array(poligono, dtype=np.int32)))


def _png(img) -> bytes:
    ok, buf = cv2.imencode('.png', img)
    assert ok
    return buf.tobytes()


# Dos triángulos que comparten la diagonal (40,40)-(120,160): juntos forman el
# rectángulo 40..120 × 40..160, pero cada uno es «un cromosoma».
TRI_A = [[40, 40], [120, 40], [120, 160]]   # arriba a la derecha de la diagonal
TRI_B = [[40, 40], [120, 160], [40, 160]]   # abajo a la izquierda
RECT = [[40, 40], [120, 40], [120, 160], [40, 160]]
CAJA = (40, 40, 81, 121)
DIAGONAL = [[30, 25], [130, 175]]           # prolonga la frontera más allá del borde


def _imagen(*poligonos):
    img = np.full((220, 200), 255, dtype=np.uint8)
    for p in poligonos:
        cv2.fillPoly(img, [np.array(p, dtype=np.int32)], 40)
    return img


class TestCortar:
    def test_la_linea_diagonal_separa_cada_cromosoma_con_su_area(self):
        img = _imagen(RECT)
        trozos = cortar(img, CAJA, RECT, DIAGONAL)
        assert len(trozos) == 2
        mitad = _area(RECT) / 2
        for t in trozos:
            # Cada trozo es un triángulo: sus píxeles son la mitad del objeto, menos
            # la franja que se lleva el trazo (GROSOR_CORTE px a lo largo de ~144 px).
            # Se cuentan píxeles (`area`), no el área del polígono, que por cómo
            # traza findContours queda medio perímetro por debajo.
            assert abs(t.area - mitad) < GROSOR_CORTE * 150
        # Y NO son las mitades izquierda y derecha de la caja: un triángulo ocupa
        # toda la altura de la caja en su lado ancho, una mitad vertical no.
        centros_x = sorted(np.mean([p[0] for p in t.contour]) for t in trozos)
        assert centros_x[0] < 75 < centros_x[1]
        izq = next(t for t in trozos if np.mean([p[0] for p in t.contour]) < 80)
        assert izq.bbox[3] > 100     # el triángulo de abajo-izquierda llega de arriba abajo

    def test_el_corte_por_la_mitad_no_respeta_la_frontera(self):
        """Control: lo que hacía `split` antes mezcla los dos triángulos."""
        x, y, w, h = CAJA
        mitad = [[x + w // 2, y - 5], [x + w // 2, y + h + 5]]
        trozos = cortar(_imagen(RECT), CAJA, RECT, mitad)
        # Cada mitad vertical lleva píxeles de los DOS triángulos.
        for t in trozos:
            xs = [p[0] for p in t.contour]
            ys = [p[1] for p in t.contour]
            assert max(ys) - min(ys) > 100 and max(xs) - min(xs) < 45

    def test_de_mayor_a_menor(self):
        # Una línea cerca del borde izquierdo: un trozo grande y uno pequeño.
        trozos = cortar(_imagen(RECT), CAJA, RECT, [[55, 30], [55, 170]])
        assert trozos[0].area > trozos[1].area

    def test_una_linea_que_cruza_dos_veces_da_tres_trozos(self):
        zigzag = [[70, 30], [70, 170], [95, 170], [95, 30]]
        assert len(cortar(_imagen(RECT), CAJA, RECT, zigzag)) == 3

    def test_una_linea_que_no_atraviesa_no_corta(self):
        with pytest.raises(CorteInvalidoError):
            cortar(_imagen(RECT), CAJA, RECT, [[80, 30], [80, 100]])   # se queda a medias

    def test_una_linea_fuera_del_objeto_no_corta(self):
        with pytest.raises(CorteInvalidoError):
            cortar(_imagen(RECT), CAJA, RECT, [[150, 0], [150, 200]])

    def test_un_punto_no_es_una_linea(self):
        with pytest.raises(CorteInvalidoError):
            cortar(_imagen(RECT), CAJA, RECT, [[80, 80]])

    def test_la_viruta_del_trazo_no_cuenta_como_trozo(self):
        # Una línea que roza la esquina deja una viruta de unos 28 px (medido):
        # debajo de MIN_AREA_TROZO, así que no es un trozo y el corte no vale.
        with pytest.raises(CorteInvalidoError):
            cortar(_imagen(RECT), CAJA, RECT, [[38, 52], [52, 38]])

    def test_sin_silueta_usa_otsu_en_la_caja(self):
        trozos = cortar(_imagen(RECT), CAJA, None, DIAGONAL)
        assert len(trozos) == 2

    def test_objeto_sin_pixeles(self):
        blanco = np.full((220, 200), 255, dtype=np.uint8)
        with pytest.raises(CorteInvalidoError):
            cortar(blanco, CAJA, None, DIAGONAL)

    def test_objeto_fuera_de_la_imagen(self):
        with pytest.raises(CorteInvalidoError):
            mascara_de_objeto(_imagen(RECT), (500, 500, 10, 10), None)

    def test_imagen_en_color(self):
        color = cv2.cvtColor(_imagen(RECT), cv2.COLOR_GRAY2BGR)
        assert len(cortar(color, CAJA, None, DIAGONAL)) == 2


class TestUnir:
    def test_dos_siluetas_que_se_tocan_dan_una(self):
        contorno, caja = unir([TRI_A, TRI_B])
        assert abs(_area(contorno) - _area(RECT)) < 0.05 * _area(RECT)
        assert caja == (40, 40, 80, 120)

    def test_dos_siluetas_separadas_dan_su_envolvente(self):
        lejos = [[150, 40], [170, 40], [170, 80], [150, 80]]
        contorno, caja = unir([TRI_B, lejos])
        # La envolvente cubre las dos manchas y el hueco entre ellas.
        assert _area(contorno) > _area(TRI_B) + _area(lejos)
        assert caja[0] == 40 and caja[0] + caja[2] == 170

    def test_hacen_falta_dos(self):
        with pytest.raises(CorteInvalidoError):
            unir([TRI_A])
        with pytest.raises(CorteInvalidoError):
            unir([TRI_A, [[1, 1], [2, 2]]])


class TestEndpoints:
    def _split(self, **datos):
        cuerpo = {'bbox': json.dumps(dict(zip('xywh', CAJA))), 'linea': json.dumps(DIAGONAL),
                  'contour': json.dumps(RECT)}
        cuerpo.update(datos)
        return client.post('/api/v1/split/', files={'file': ('m.png', _png(_imagen(RECT)), 'image/png')},
                           data={k: v for k, v in cuerpo.items() if v is not None})

    def test_split_devuelve_los_trozos(self):
        r = self._split()
        assert r.status_code == 200
        trozos = r.json()['trozos']
        assert len(trozos) == 2
        assert set(trozos[0]['bbox']) == {'x', 'y', 'w', 'h'}
        assert trozos[0]['area'] >= trozos[1]['area']

    def test_split_sin_contorno(self):
        assert self._split(contour=None).status_code == 200

    def test_split_linea_que_no_corta_422(self):
        r = self._split(linea=json.dumps([[150, 0], [150, 200]]))
        assert r.status_code == 422
        assert 'no separa' in r.json()['detail']

    @pytest.mark.parametrize('campo, valor', [
        ('bbox', '{malo'), ('bbox', json.dumps({'x': 1})), ('linea', json.dumps('x')),
        ('linea', json.dumps([[1, 2, 3]])), ('contour', json.dumps([['a', 1]])),
    ])
    def test_split_400(self, campo, valor):
        assert self._split(**{campo: valor}).status_code == 400

    def test_split_archivo_vacio_o_ilegible(self):
        cuerpo = {'bbox': json.dumps(dict(zip('xywh', CAJA))), 'linea': json.dumps(DIAGONAL)}
        assert client.post('/api/v1/split/', files={'file': ('m.png', b'', 'image/png')},
                           data=cuerpo).status_code == 400
        assert client.post('/api/v1/split/', files={'file': ('m.png', b'no-imagen', 'image/png')},
                           data=cuerpo).status_code == 422

    def test_join(self):
        r = client.post('/api/v1/join/', data={'contornos': json.dumps([TRI_A, TRI_B])})
        assert r.status_code == 200
        assert r.json()['bbox'] == {'x': 40, 'y': 40, 'w': 80, 'h': 120}

    def test_join_422_y_400(self):
        assert client.post('/api/v1/join/', data={'contornos': json.dumps([TRI_A])}).status_code == 422
        assert client.post('/api/v1/join/', data={'contornos': json.dumps({'a': 1})}).status_code == 400
        assert client.post('/api/v1/join/', data={'contornos': '{'}).status_code == 400
