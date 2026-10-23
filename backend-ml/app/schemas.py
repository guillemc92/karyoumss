"""Contratos de I/O del servicio de inferencia (ADR-0007, DD-ML-001).

El shape de `ChromosomeOut` mapea al modelo `Chromosome` de backend-clinic
(predicted_class, confidence_score, bbox, order) para que la ingesta sea directa.
"""
from __future__ import annotations

from pydantic import BaseModel


class BBox(BaseModel):
    x: int
    y: int
    w: int
    h: int


class ChromosomeOut(BaseModel):
    order: int
    predicted_class: str            # '1'..'22'/'X'/'Y'
    confidence_score: float         # 0..1 (placeholder: bajo → naranja)
    bbox: BBox
    area: int
    # DD-KARYO-007 D1: silueta en píxeles de la metafase; None → el cliente pinta la caja.
    contour: list[list[int]] | None = None


class ContornosOut(BaseModel):
    """Una silueta por caja pedida, en el mismo orden; None donde no se pudo."""
    contornos: list[list[list[int]] | None]


class TrozoOut(BaseModel):
    """Un trozo tras separar (DD-KARYO-007 D3), en píxeles de la metafase."""
    contour: list[list[int]]
    bbox: dict[str, int]
    area: int


class SplitOut(BaseModel):
    """Los trozos de mayor a menor área: el primero se queda con el objeto original."""
    trozos: list[TrozoOut]


class JoinOut(BaseModel):
    """Silueta y caja de la unión (DD-KARYO-007 D4)."""
    contour: list[list[int]]
    bbox: dict[str, int]


class SegmentResult(BaseModel):
    model_version: str
    segmenter: str
    classifier: str
    image_width: int
    image_height: int
    chromosome_count: int
    confidence_avg: float
    chromosomes: list[ChromosomeOut]


class HealthOut(BaseModel):
    status: str
    service: str
    model_version: str
    trained_model: bool             # False: baseline OpenCV + placeholder
