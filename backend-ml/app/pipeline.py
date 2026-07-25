"""Pipeline de inferencia: metafase → cromosomas (ADR-0007, DD-ML-001).

Orquesta segmentación (real, OpenCV) + clasificación (placeholder) sobre la
imagen. `model_version` sigue la nomenclatura canónica del proyecto
(u-net + efficientnet-b3) pero marca que es baseline hasta enchufar el modelo.
"""
from __future__ import annotations

import cv2
import numpy as np

from .classifier import PLACEHOLDER_CONFIDENCE, PlaceholderClassifier, assign_placeholder_classes
from .ports import ClassifierPort, SegmenterPort
from .schemas import BBox, ChromosomeOut, SegmentResult
from .segmentation import Detection

# Baseline: segmentación real, clasificación placeholder (sin modelo entrenado).
MODEL_VERSION = 'opencv-watershed-v0+placeholder-clf-v0'


class OpenCVSegmenter(SegmenterPort):
    def segment(self, gray: np.ndarray) -> list[Detection]:
        from .segmentation import segment
        return segment(gray)


def run_pipeline(
    gray: np.ndarray,
    segmenter: SegmenterPort | None = None,
    classifier: ClassifierPort | None = None,
) -> SegmentResult:
    segmenter = segmenter or OpenCVSegmenter()
    classifier = classifier or PlaceholderClassifier()

    h, w = gray.shape[:2]
    detections = segmenter.segment(gray)

    # Clasificación placeholder por rango de tamaño (necesita todas las áreas).
    areas = [d.area for d in detections]
    classes = assign_placeholder_classes(areas) if areas else []

    chromosomes: list[ChromosomeOut] = []
    confs: list[float] = []
    for order, (d, cls) in enumerate(zip(detections, classes)):
        x, y, bw, bh = d.bbox
        conf = PLACEHOLDER_CONFIDENCE
        confs.append(conf)
        chromosomes.append(ChromosomeOut(
            order=order,
            predicted_class=cls,
            confidence_score=conf,
            bbox=BBox(x=x, y=y, w=bw, h=bh),
            area=d.area,
        ))

    return SegmentResult(
        model_version=MODEL_VERSION,
        segmenter=type(segmenter).__name__,
        classifier=classifier.name,
        image_width=w,
        image_height=h,
        chromosome_count=len(chromosomes),
        confidence_avg=round(sum(confs) / len(confs), 3) if confs else 0.0,
        chromosomes=chromosomes,
    )


def crop_of(gray: np.ndarray, bbox: tuple[int, int, int, int]) -> np.ndarray:
    x, y, w, h = bbox
    return gray[y:y + h, x:x + w]
