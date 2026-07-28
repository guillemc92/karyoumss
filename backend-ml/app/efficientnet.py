"""Clasificador EfficientNet-B3 entrenado — ADR-0007, DD-ML-001 (Fase C3).

Adaptador REAL de `ClassifierPort`: carga el modelo entrenado sobre el dataset
MetaClass (`models/classifier.pth`) y clasifica cada cromosoma detectado. Import
de torch perezoso: si torch o el modelo no están, el pipeline cae al
`PlaceholderClassifier` (backend-ml sigue corriendo, RN-07).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .ports import ClassifierPort
from .preprocess import letterbox, reference_height
from .segmentation import Detection

MODELS_DIR = Path(__file__).resolve().parent.parent / 'models'


class EfficientNetClassifier(ClassifierPort):
    def __init__(self, models_dir: Path = MODELS_DIR):
        import torch                       # import perezoso (torch es opcional)
        from torchvision import models, transforms
        from PIL import Image

        self._torch = torch
        self._Image = Image

        meta = json.loads((models_dir / 'model_meta.json').read_text())
        self.classes: list[str] = json.loads((models_dir / 'classes.json').read_text())
        img_size = int(meta.get('img_size', 224))
        self.val_macro_f1 = meta.get('val_macro_f1')
        # v1 se entrenó con Resize() deformante; v2+ con letterbox de escala
        # relativa. El modelo declara cuál espera — mezclarlos degrada la
        # precisión en silencio.
        self._preprocess = meta.get('preprocess', 'resize')
        self._img_size = img_size
        self._version = meta.get('version', 'v1')

        model = models.efficientnet_b3(weights=None)
        in_feats = model.classifier[1].in_features
        model.classifier[1] = torch.nn.Linear(in_feats, len(self.classes))
        state = torch.load(models_dir / 'classifier.pth', map_location='cpu')
        model.load_state_dict(state)
        model.eval()
        self._model = model

        norm = meta['normalization']
        if self._preprocess == 'letterbox':
            # el letterbox ya deja el crop en img_size x img_size
            self._tf = transforms.Compose([
                transforms.Grayscale(num_output_channels=3),
                transforms.ToTensor(),
                transforms.Normalize(norm['mean'], norm['std']),
            ])
        else:
            self._tf = transforms.Compose([
                transforms.Grayscale(num_output_channels=3),
                transforms.Resize((img_size, img_size)),
                transforms.ToTensor(),
                transforms.Normalize(norm['mean'], norm['std']),
            ])

    @property
    def name(self) -> str:
        # Se persiste en Karyotype.model_version de cada caso: tiene que decir
        # qué modelo produjo ese resultado, o la trazabilidad clínica miente.
        return f'efficientnet-b3-metaclass-{self._version}'

    @property
    def is_trained(self) -> bool:
        return True

    def classify_all(self, gray: np.ndarray, detections: list[Detection]) -> list[tuple[str, float]]:
        if not detections:
            return []
        torch = self._torch
        use_letterbox = self._preprocess == 'letterbox'
        # escala de referencia de ESTA metafase (mediana de alturas detectadas)
        ref_h = reference_height([d.bbox[3] for d in detections]) if use_letterbox else 0.0
        tensors = []
        for d in detections:
            x, y, w, h = d.bbox
            crop = gray[y:y + h, x:x + w]
            if use_letterbox:
                img = letterbox(crop, ref_h, canvas=self._img_size)
            else:
                img = self._Image.fromarray(crop)
            tensors.append(self._tf(img))
        batch = torch.stack(tensors)
        with torch.no_grad():
            probs = torch.softmax(self._model(batch), dim=1)
            conf, idx = probs.max(dim=1)
        return [(self.classes[int(i)], round(float(c), 3)) for i, c in zip(idx.tolist(), conf.tolist())]
