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


class EstadoInferenciasOut(BaseModel):
    """Estado del límite de inferencias (FR1.1–FR1.5)."""
    maximo: int                     # ML_MAX_INFERENCIAS
    en_curso: int                   # inferencias con plaza ahora mismo
    libres: int                     # maximo - en_curso
    espera_max_s: float             # ML_ESPERA_MAX_S, antes del 503
    en_espera: int                  # peticiones esperando turno
