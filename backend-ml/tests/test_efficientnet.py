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


class TestCoherenciaDeLosArtefactos:
    """Los 3 archivos de `models/` son un conjunto: se despliegan juntos.

    El v2 cambió el orden de las clases (alfabético de ImageFolder → orden
    citogenético). Un `classifier.pth` servido con el `classes.json` de otra
    versión traduce cada predicción a la clase equivocada **sin fallar ni
    avisar** — el peor modo de fallo posible en un sistema clínico. Estos tests
    no necesitan torch: solo leen los metadatos.
    """

    def test_num_classes_coincide_con_la_lista(self):
        import json
        meta = json.loads((MODELS / 'model_meta.json').read_text())
        classes = json.loads((MODELS / 'classes.json').read_text())
        assert meta['num_classes'] == len(classes)

    def test_estan_las_24_clases_esperadas(self):
        import json
        classes = json.loads((MODELS / 'classes.json').read_text())
        assert set(classes) == {str(n) for n in range(1, 23)} | {'X', 'Y'}

    def test_el_orden_corresponde_al_preprocesamiento_declarado(self):
        """v2 (letterbox) usa orden citogenético; v1 (resize) el alfabético de
        ImageFolder. Si no concuerdan, los artefactos están mezclados."""
        import json
        meta = json.loads((MODELS / 'model_meta.json').read_text())
        classes = json.loads((MODELS / 'classes.json').read_text())
        citogenetico = [str(n) for n in range(1, 23)] + ['X', 'Y']

        if meta.get('preprocess') == 'letterbox':
            assert classes == citogenetico, (
                'modelo v2 con classes.json que no es el suyo — cada predicción '
                'se traduciría a la clase equivocada'
            )
        else:
            assert classes == sorted(citogenetico), (
                'modelo v1 (resize) con un classes.json que no es el alfabético'
            )
