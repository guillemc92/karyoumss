"""Segmentación de cromosomas (visión por computadora real) — ADR-0007, DD-ML-001.

Baseline clásico (OpenCV) que corre de VERDAD sobre imágenes de metafase:
grises → Otsu invertido (cromosomas oscuros sobre fondo claro) → morfología →
**watershed** para separar cromosomas que se tocan/solapan → componentes.

Es el adaptador `OpenCVSegmenter` del puerto `SegmenterPort` (hexagonal): cuando
haya un modelo U-Net entrenado, se implementa `UNetSegmenter` con la misma
interfaz y se reemplaza sin tocar el pipeline.
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


def _binary_mask(gray: np.ndarray) -> np.ndarray:
    blur = cv2.medianBlur(gray, 3)
    _, bw = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    bw = cv2.morphologyEx(bw, cv2.MORPH_OPEN, kernel, iterations=1)
    return bw


def segment(gray: np.ndarray) -> list[Detection]:
    """Segmenta los cromosomas de una imagen en escala de grises.

    Usa watershed sobre la transformada de distancia para partir cromosomas que
    se tocan. Devuelve las detecciones filtradas por área.
    """
    if gray.ndim == 3:
        gray = cv2.cvtColor(gray, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    max_area = MAX_AREA_FRAC * h * w

    bw = _binary_mask(gray)

    # Watershed: separar objetos que se tocan.
    dist = cv2.distanceTransform(bw, cv2.DIST_L2, 5)
    _, sure_fg = cv2.threshold(dist, DIST_FG_FRAC * dist.max(), 255, 0)
    sure_fg = sure_fg.astype(np.uint8)
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
