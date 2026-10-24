"""Clasificador placeholder — ADR-0007, DD-ML-001.

⚠️ STUB HONESTO (se usa si NO hay modelo entrenado disponible): asigna la clase
por rango de tamaño global (heurística débil) con confianza baja fija → todo cae
naranja → clasificación manual (FSD-UC-007). El adaptador entrenado real es
`EfficientNetClassifier` (efficientnet.py).
"""
from __future__ import annotations

import numpy as np

from .ports import ClassifierPort
from .segmentation import Detection

KARYOTYPE_CLASSES = [str(n) for n in range(1, 23)] + ['X', 'Y']
PLACEHOLDER_CONFIDENCE = 0.55


def assign_placeholder_classes(areas: list[int]) -> list[str]:
    """Ordena por área desc y asigna las 24 clases del cariograma en orden
    (1,1,2,2,...,22,22,X,Y). Débil pero determinística."""
    order = sorted(range(len(areas)), key=lambda i: areas[i], reverse=True)
    seq: list[str] = []
    for n in range(1, 23):
        seq += [str(n), str(n)]
    seq += ['X', 'Y']
    result = ['1'] * len(areas)
    for rank, idx in enumerate(order):
        result[idx] = seq[rank] if rank < len(seq) else 'Y'
    return result


class PlaceholderClassifier(ClassifierPort):
    @property
    def name(self) -> str:
        return 'placeholder-size-rank-v0'

    def classify_all(self, gray: np.ndarray, detections: list[Detection]) -> list[tuple[str, float]]:
        areas = [d.area for d in detections]
        classes = assign_placeholder_classes(areas)
        return [(c, PLACEHOLDER_CONFIDENCE) for c in classes]
