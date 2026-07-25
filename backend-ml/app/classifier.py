"""Clasificador de cromosomas — ADR-0007, DD-ML-001.

⚠️ PLACEHOLDER HONESTO: NO hay modelo entrenado todavía. Este adaptador asigna
la clase por **rango de tamaño** (heurística débil: los pares 1→22 decrecen en
tamaño) con **confianza baja fija** → en el visor todo cae naranja/rojo → el
analista clasifica a mano (modo manual real, FSD-UC-007). Cuando se entrene el
EfficientNet-B3 (sobre el dataset MetaClass), se reemplaza por
`EfficientNetClassifier` con la misma interfaz `ClassifierPort`.
"""
from __future__ import annotations

import numpy as np

from .ports import ClassifierPort

# Orden de clases del cariograma (24 clases).
KARYOTYPE_CLASSES = [str(n) for n in range(1, 23)] + ['X', 'Y']
# Confianza fija baja: el placeholder NO es fiable → todo requiere revisión.
PLACEHOLDER_CONFIDENCE = 0.55


class PlaceholderClassifier(ClassifierPort):
    """Asigna clase por rango de tamaño global, confianza baja fija.

    NO es un modelo: es un stub para que el pipeline entregue una estructura
    completa mientras no exista el clasificador entrenado.
    """

    def __init__(self) -> None:
        self._rank = 0  # se setea por el pipeline vía `set_rank`

    @property
    def name(self) -> str:
        return 'placeholder-size-rank-v0'

    def classify(self, crop: np.ndarray, area: int) -> tuple[str, float]:
        # La clase real la decide el pipeline por rango de tamaño (necesita ver
        # todas las detecciones); acá sólo se devuelve la confianza baja. El
        # pipeline sobreescribe la clase. Ver `pipeline.assign_placeholder_classes`.
        return ('1', PLACEHOLDER_CONFIDENCE)


def assign_placeholder_classes(areas: list[int]) -> list[str]:
    """Heurística de placeholder: ordena por área desc y asigna las 24 clases
    del cariograma en orden (1,1,2,2,...,22,22,X,Y). Débil pero determinística."""
    order = sorted(range(len(areas)), key=lambda i: areas[i], reverse=True)
    # secuencia de clases esperadas: cada autosoma x2, luego X, Y
    seq: list[str] = []
    for n in range(1, 23):
        seq += [str(n), str(n)]
    seq += ['X', 'Y']
    result = ['1'] * len(areas)
    for rank, idx in enumerate(order):
        result[idx] = seq[rank] if rank < len(seq) else 'Y'
    return result
