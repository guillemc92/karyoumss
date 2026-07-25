"""Pipeline de inferencia: metafase → cromosomas (ADR-0007, DD-ML-001).

Orquesta segmentación (real, OpenCV) + clasificación. `get_classifier()` usa el
modelo EfficientNet-B3 entrenado si está disponible (torch + models/*.pth); si
no, cae al placeholder (RN-07: backend-ml sigue corriendo).
"""
from __future__ import annotations

import numpy as np

from .classifier import PlaceholderClassifier
from .ports import ClassifierPort, SegmenterPort
from .schemas import BBox, ChromosomeOut, SegmentResult
from .segmentation import Detection


class OpenCVSegmenter(SegmenterPort):
    def segment(self, gray: np.ndarray) -> list[Detection]:
        from .segmentation import segment
        return segment(gray)


_classifier_singleton: ClassifierPort | None = None


def get_classifier() -> ClassifierPort:
    """Devuelve el clasificador entrenado si se puede cargar; si no, placeholder."""
    global _classifier_singleton
    if _classifier_singleton is None:
        try:
            from .efficientnet import EfficientNetClassifier
            _classifier_singleton = EfficientNetClassifier()
        except Exception:  # torch ausente o modelo no cargable → placeholder
            _classifier_singleton = PlaceholderClassifier()
    return _classifier_singleton


def run_pipeline(
    gray: np.ndarray,
    segmenter: SegmenterPort | None = None,
    classifier: ClassifierPort | None = None,
) -> SegmentResult:
    segmenter = segmenter or OpenCVSegmenter()
    classifier = classifier or get_classifier()

    h, w = gray.shape[:2]
    detections = segmenter.segment(gray)
    preds = classifier.classify_all(gray, detections)

    chromosomes: list[ChromosomeOut] = []
    confs: list[float] = []
    for order, (d, (cls, conf)) in enumerate(zip(detections, preds)):
        x, y, bw, bh = d.bbox
        confs.append(conf)
        chromosomes.append(ChromosomeOut(
            order=order,
            predicted_class=cls,
            confidence_score=conf,
            bbox=BBox(x=x, y=y, w=bw, h=bh),
            area=d.area,
        ))

    seg_name = 'opencv-watershed-v0'
    clf_name = classifier.name
    return SegmentResult(
        model_version=f'{seg_name}+{clf_name}',
        segmenter=type(segmenter).__name__,
        classifier=clf_name,
        image_width=w,
        image_height=h,
        chromosome_count=len(chromosomes),
        confidence_avg=round(sum(confs) / len(confs), 3) if confs else 0.0,
        chromosomes=chromosomes,
    )


def crop_of(gray: np.ndarray, bbox: tuple[int, int, int, int]) -> np.ndarray:
    x, y, w, h = bbox
    return gray[y:y + h, x:x + w]
