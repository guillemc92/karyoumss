"""Test del clasificador entrenado (Fase C3). Se saltea si torch o el modelo no
están (CI-safe)."""
from pathlib import Path

import pytest

MODELS = Path(__file__).resolve().parents[1] / 'models'


def _available() -> bool:
    try:
        import torch  # noqa: F401
        import torchvision  # noqa: F401
    except Exception:
        return False
    return (MODELS / 'classifier.pth').exists()


@pytest.mark.skipif(not _available(), reason='torch o modelo entrenado no disponible')
class TestEfficientNet:
    def test_carga_y_clasifica(self, synthetic_gray):
        from app.efficientnet import EfficientNetClassifier
        from app.segmentation import segment

        clf = EfficientNetClassifier()
        assert clf.is_trained is True
        assert len(clf.classes) == 24

        dets = segment(synthetic_gray)
        preds = clf.classify_all(synthetic_gray, dets)
        assert len(preds) == len(dets)
        valid = [str(n) for n in range(1, 23)] + ['X', 'Y']
        for cls, conf in preds:
            assert cls in valid
            assert 0.0 <= conf <= 1.0

    def test_pipeline_usa_el_modelo_entrenado(self, synthetic_gray):
        from app.pipeline import get_classifier, run_pipeline
        clf = get_classifier()
        assert clf.is_trained is True  # el factory carga el EfficientNet real
        res = run_pipeline(synthetic_gray)
        assert 'efficientnet' in res.classifier
