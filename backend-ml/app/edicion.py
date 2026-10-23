"""Separar y unir objetos sobre la metafase (DD-KARYO-007 D3 y D4).

El corte se hace en ráster, no cortando polígonos (DD-KARYO-007 §10.1):

1. se pinta la máscara del objeto —su silueta, o Otsu en su caja si no tiene;
2. se borra la línea que trazó el analista con `GROSOR_CORTE` px;
3. cada componente conexo que queda es un trozo; los de menos de
   `MIN_AREA_TROZO` px son ruido del trazo y se descartan.

Es más robusto que intersecar un polígono con una polilínea: da igual que la
línea sea recta o quebrada, que corte dos veces o que no llegue al borde por
un píxel (la máscara no se separa y se dice).

Unir es lo inverso: se pintan las dos máscaras y se toma el contorno de la
unión. Si no se tocan, la silueta es la envolvente convexa de las dos, para
que un cromosoma partido en dos manchas siga siendo UN objeto que se pueda
pulsar (DD-KARYO-007 §11).
"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from .segmentation import _binary_mask, contorno_de_mascara

#: Grosor, en px de la metafase, del corte que deja la línea. Con 1 px la
#: conectividad-8 salta la línea en diagonal y el objeto no se separa.
GROSOR_CORTE = 3

#: Área mínima de un trozo. Por debajo es la viruta que deja el trazo al pasar
#: rozando el borde, no un cromosoma (el más pequeño, el 21, ronda los 250 px).
MIN_AREA_TROZO = 40

#: Margen alrededor de la caja al pintar la máscara: que el trazo cerca del
#: borde no se salga del lienzo de trabajo.
_MARGEN = 2


class CorteInvalidoError(ValueError):
    """La línea no separa el objeto en dos o más trozos."""


@dataclass
class Trozo:
    contour: list[list[int]]
    bbox: tuple[int, int, int, int]
    area: int


def _region(bbox: tuple[int, int, int, int], contorno: list[list[int]] | None,
            forma: tuple[int, int]) -> tuple[int, int, int, int]:
    """Rectángulo de trabajo: la caja y la silueta, con margen, dentro de la imagen."""
    xs = [bbox[0], bbox[0] + bbox[2]]
    ys = [bbox[1], bbox[1] + bbox[3]]
    if contorno:
        xs += [p[0] for p in contorno]
        ys += [p[1] for p in contorno]
    alto, ancho = forma
    x0 = max(0, min(xs) - _MARGEN)
    y0 = max(0, min(ys) - _MARGEN)
    x1 = min(ancho, max(xs) + _MARGEN + 1)
    y1 = min(alto, max(ys) + _MARGEN + 1)
    return x0, y0, x1, y1


def mascara_de_objeto(gray: np.ndarray, bbox: tuple[int, int, int, int],
                      contorno: list[list[int]] | None) -> tuple[np.ndarray, int, int]:
    """Máscara binaria del objeto en su región de trabajo, y el origen de esa región.

    Con silueta, la silueta rellena. Sin ella, Otsu dentro de la caja: es lo que
    `contorno_en_caja` habría trazado.
    """
    if gray.ndim == 3:
        gray = cv2.cvtColor(gray, cv2.COLOR_BGR2GRAY)
    x0, y0, x1, y1 = _region(bbox, contorno, gray.shape)
    if x1 <= x0 or y1 <= y0:
        raise CorteInvalidoError('el objeto cae fuera de la metafase')
    mascara = np.zeros((y1 - y0, x1 - x0), dtype=np.uint8)
    if contorno and len(contorno) >= 3:
        puntos = np.array([[px - x0, py - y0] for px, py in contorno], dtype=np.int32)
        cv2.fillPoly(mascara, [puntos], 255)
    else:
        # Otsu sobre la región CON su margen: una caja ajustada a un objeto que
        # la llena entera es un recorte plano, sin fondo con el que comparar.
        recorte = gray[y0:y1, x0:x1]
        if int(recorte.max()) != int(recorte.min()):
            mascara = _binary_mask(recorte)
    return mascara, x0, y0


def cortar(gray: np.ndarray, bbox: tuple[int, int, int, int],
           contorno: list[list[int]] | None, linea: list[list[float]]) -> list[Trozo]:
    """Trozos del objeto tras borrar la línea, de mayor a menor área.

    `linea` es una polilínea `[[x, y], …]` en píxeles de la metafase.
    Lanza `CorteInvalidoError` si no salen al menos dos trozos.
    """
    if len(linea) < 2:
        raise CorteInvalidoError('la línea necesita al menos dos puntos')
    mascara, x0, y0 = mascara_de_objeto(gray, bbox, contorno)
    if cv2.countNonZero(mascara) == 0:
        raise CorteInvalidoError('el objeto no tiene píxeles que cortar')
    trazo = np.array([[round(px) - x0, round(py) - y0] for px, py in linea], dtype=np.int32)
    cv2.polylines(mascara, [trazo], isClosed=False, color=0, thickness=GROSOR_CORTE)

    n, etiquetas, stats, _ = cv2.connectedComponentsWithStats(mascara, connectivity=8)
    trozos: list[Trozo] = []
    for i in range(1, n):
        area = int(stats[i, cv2.CC_STAT_AREA])
        if area < MIN_AREA_TROZO:
            continue
        contorno_trozo = contorno_de_mascara(etiquetas == i, x0, y0)
        if contorno_trozo is None:
            continue
        caja = (int(stats[i, cv2.CC_STAT_LEFT]) + x0, int(stats[i, cv2.CC_STAT_TOP]) + y0,
                int(stats[i, cv2.CC_STAT_WIDTH]), int(stats[i, cv2.CC_STAT_HEIGHT]))
        trozos.append(Trozo(contour=contorno_trozo, bbox=caja, area=area))
    if len(trozos) < 2:
        raise CorteInvalidoError('la línea no separa el objeto: trácela de borde a borde')
    trozos.sort(key=lambda t: t.area, reverse=True)
    return trozos


def unir(contornos: list[list[list[int]]]) -> tuple[list[list[int]], tuple[int, int, int, int]]:
    """Silueta y caja de la unión de varias siluetas.

    Si las siluetas se tocan (o quedan a 1 px), el contorno de la unión. Si no,
    la envolvente convexa de todas: un solo objeto que se puede pulsar.
    """
    validos = [c for c in contornos if c and len(c) >= 3]
    if len(validos) < 2:
        raise CorteInvalidoError('hacen falta al menos dos siluetas para unir')
    puntos = np.array([p for c in validos for p in c], dtype=np.int32)
    x0, y0 = puntos.min(axis=0) - _MARGEN
    x1, y1 = puntos.max(axis=0) + _MARGEN + 1
    mascara = np.zeros((y1 - y0, x1 - x0), dtype=np.uint8)
    for c in validos:
        cv2.fillPoly(mascara, [np.array(c, dtype=np.int32) - [x0, y0]], 255)
    # Un cierre de 3 px suelda dos siluetas que se rozan pero no comparten píxel.
    cerrada = cv2.morphologyEx(mascara, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    n, _ = cv2.connectedComponents(cerrada, connectivity=8)
    if n - 1 == 1:
        contorno = contorno_de_mascara(cerrada, int(x0), int(y0))
    else:
        casco = cv2.convexHull(puntos).reshape(-1, 2)
        contorno = [[int(px), int(py)] for px, py in casco]
    xs = [p[0] for p in contorno]
    ys = [p[1] for p in contorno]
    return contorno, (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
