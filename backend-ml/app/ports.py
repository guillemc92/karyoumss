"""Puertos hexagonales del motor de IA (ADR-0007 — diseño para extracción/swap).

La segmentación y la clasificación se definen como interfaces. Hoy las
implementan adaptadores clásicos (OpenCV + heurística); cuando exista el modelo
entrenado (U-Net + EfficientNet-B3) se implementan `UNetSegmenter` /
`EfficientNetClassifier` con la MISMA interfaz y se reemplazan sin tocar el
pipeline ni la API (ADR-0007 §Consecuencias: extracción mecánica, no rewrite).
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
    """Clasifica el recorte de un cromosoma en una clase 1..22/X/Y + confianza."""

    @abstractmethod
    def classify(self, crop: np.ndarray, area: int) -> tuple[str, float]:  # pragma: no cover
        ...

    @property
    @abstractmethod
    def name(self) -> str:  # pragma: no cover
        ...
