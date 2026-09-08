"""Segmentación de cromosomas (visión por computadora real) — ADR-0007, DD-ML-001.

Baseline clásico (OpenCV) que corre de VERDAD sobre imágenes de metafase:
grises → Otsu invertido (cromosomas oscuros sobre fondo claro) → morfología →
**watershed** para separar cromosomas que se tocan/solapan → componentes.

Es el adaptador `OpenCVSegmenter` del puerto `SegmenterPort` (hexagonal): cuando
haya un modelo U-Net entrenado, se implementa `UNetSegmenter` con la misma
interfaz y se reemplaza sin tocar el pipeline.

## Techo medido del baseline clásico

Contra el cariograma del experto en 453 casos pareados: MAE 3.8 cromosomas,
96% dentro de ±10, sin fallos catastróficos. El error que queda es **sub-
segmentación**: cúmulos de cromosomas que se tocan y se cuentan como uno
(áreas de 2.0x y 4.3x la mediana en una misma metafase).

Se intentó repartirlos con una segunda pasada de watershed sobre las
detecciones sobredimensionadas, y **se descartó por medición**: empeoró el MAE
de 3.5 a 12.8 (y a 4.9 restringiendo el corte). La causa es biológica — el
centrómero es un estrangulamiento, así que un umbral de distancia agresivo
parte cada cromosoma en sus dos brazos en lugar de separar los pegados. Los
brazos de un cromosoma grande miden lo mismo que un cromosoma pequeño, así que
ningún filtro de tamaño distingue un caso del otro.

Separar cromosomas que se solapan requiere aprender la forma, no medir la
distancia: es justamente el trabajo del `UNetSegmenter` previsto en ADR-0007.
No reintentar por la vía clásica.
"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class Detection:
    """Un cromosoma (o cluster que se toca) detectado en la metafase."""
    bbox: tuple[int, int, int, int]  # x, y, w, h
    area: int
    centroid: tuple[float, float]


# Umbrales del baseline (px sobre imágenes ~1024x768). Ajustables por config.
MIN_AREA = 250       # descarta specks + texto de los números anotados
MAX_AREA_FRAC = 0.15  # descarta megablobs (bordes/artefactos)
DIST_FG_FRAC = 0.35   # fracción del máximo de la dist-transform para el foreground seguro


def _sure_foreground(bw: np.ndarray, dist: np.ndarray) -> np.ndarray:
    """Marcadores de watershed con umbral **por componente**, no global.

    Un umbral global (`DIST_FG_FRAC * dist.max()`) asume que todos los objetos
    tienen un grosor parecido, y en una metafase eso es falso: un núcleo
    interfásico es un blob redondo con distancia ~110 px, mientras que un
    cromosoma ronda los ~18 px. Con el máximo global el umbral sube a ~39 px,
    **ningún cromosoma lo alcanza** y todos se quedan sin marcador: watershed
    los absorbe en un único objeto. Medido sobre 120 casos pareados contra el
    cariograma del experto, ese fallo se daba en 18 de ellos (15%).

    Midiendo cada componente contra su propio grosor, un cúmulo de cromosomas
    que se tocan se sigue partiendo (comparten escala) y el núcleo deja de
    arrastrar al resto. MAE 10.4 → 3.5 cromosomas; fallos catastróficos 18 → 0.
    """
    n, labels, stats, _ = cv2.connectedComponentsWithStats(bw, 8)
    fg = np.zeros(bw.shape, np.uint8)
    for label in range(1, n):  # 0 = fondo
        x, y, w, h, area = stats[label]
        if area < MIN_AREA:
            continue
        # Recortar al bbox: recorrer la imagen entera por componente es O(n·px).
        sub_mask = labels[y:y + h, x:x + w] == label
        sub_dist = dist[y:y + h, x:x + w]
        local_max = sub_dist[sub_mask].max()
        if local_max <= 0:
            continue
        fg[y:y + h, x:x + w][sub_mask & (sub_dist >= DIST_FG_FRAC * local_max)] = 255
    return fg


def _binary_mask(gray: np.ndarray) -> np.ndarray:
    blur = cv2.medianBlur(gray, 3)
    _, bw = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    bw = cv2.morphologyEx(bw, cv2.MORPH_OPEN, kernel, iterations=1)
    return bw


def segment(gray: np.ndarray) -> list[Detection]:
    """Segmenta los cromosomas de una imagen en escala de grises.

    Usa watershed sobre la transformada de distancia para partir cromosomas que
    se tocan, con los marcadores calculados **por componente** (ver
    `_sure_foreground`). Devuelve las detecciones filtradas por área.
    """
    if gray.ndim == 3:
        gray = cv2.cvtColor(gray, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    max_area = MAX_AREA_FRAC * h * w

    bw = _binary_mask(gray)

    # Watershed: separar objetos que se tocan.
    dist = cv2.distanceTransform(bw, cv2.DIST_L2, 5)
    sure_fg = _sure_foreground(bw, dist)
    sure_bg = cv2.dilate(bw, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)), iterations=2)
    unknown = cv2.subtract(sure_bg, sure_fg)

    n_markers, markers = cv2.connectedComponents(sure_fg)
    markers = markers + 1
    markers[unknown == 255] = 0
    color = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    markers = cv2.watershed(color, markers)

    detections: list[Detection] = []
    for label in range(2, n_markers + 1):  # 1 = fondo, <2 = borde
        ys, xs = np.where(markers == label)
        if xs.size == 0:
            continue
        area = int(xs.size)
        if area < MIN_AREA or area > max_area:
            continue
        x0, x1 = int(xs.min()), int(xs.max())
        y0, y1 = int(ys.min()), int(ys.max())
        bw_box, bh_box = x1 - x0 + 1, y1 - y0 + 1
        if bw_box < 6 or bh_box < 6:
            continue
        detections.append(Detection(
            bbox=(x0, y0, bw_box, bh_box),
            area=area,
            centroid=(float(xs.mean()), float(ys.mean())),
        ))
    return detections


def load_gray(image_bytes: bytes) -> np.ndarray:
    """Decodifica bytes de imagen (BMP/PNG/JPG/TIFF) a escala de grises."""
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError('No se pudo decodificar la imagen')
    return img
