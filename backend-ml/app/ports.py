"""Puertos hexagonales del motor de IA (ADR-0007 — diseño para extracción/swap).

La segmentación y la clasificación se definen como interfaces. Los adaptadores
concretos (OpenCV + EfficientNet-B3 entrenado, o placeholder) las implementan;
se reemplazan sin tocar el pipeline ni la API (ADR-0007 §Consecuencias:
extracción mecánica, no rewrite).
"""
from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from .segmentation import Detection


class SegmenterPort(ABC):
    """Detecta los cromosomas en una imagen de metafase (grises)."""

    @abstractmethod
    def segment(self, gray: np.ndarray) -> list[Detection]:  # pragma: no cover
        ...


class ClassifierPort(ABC):
    """Clasifica las detecciones de un caso en clases 1..22/X/Y + confianza.

    Recibe la imagen completa + las detecciones (no un crop suelto) porque el
    placeholder necesita el contexto global de tamaños; el modelo entrenado
    recorta cada detección internamente.
    """

    @abstractmethod
    def classify_all(self, gray: np.ndarray, detections: list[Detection]) -> list[tuple[str, float]]:  # pragma: no cover
        ...

    @property
    @abstractmethod
    def name(self) -> str:  # pragma: no cover
        ...

    @property
    def is_trained(self) -> bool:
        return False
