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

        model = models.efficientnet_b3(weights=None)
        in_feats = model.classifier[1].in_features
        model.classifier[1] = torch.nn.Linear(in_feats, len(self.classes))
        state = torch.load(models_dir / 'classifier.pth', map_location='cpu')
        model.load_state_dict(state)
        model.eval()
        self._model = model

        norm = meta['normalization']
        self._tf = transforms.Compose([
            transforms.Grayscale(num_output_channels=3),
            transforms.Resize((img_size, img_size)),
            transforms.ToTensor(),
            transforms.Normalize(norm['mean'], norm['std']),
        ])

    @property
    def name(self) -> str:
        return 'efficientnet-b3-metaclass-v1'

    @property
    def is_trained(self) -> bool:
        return True

    def classify_all(self, gray: np.ndarray, detections: list[Detection]) -> list[tuple[str, float]]:
        if not detections:
            return []
        torch = self._torch
        tensors = []
        for d in detections:
            x, y, w, h = d.bbox
            crop = gray[y:y + h, x:x + w]
            tensors.append(self._tf(self._Image.fromarray(crop)))
        batch = torch.stack(tensors)
        with torch.no_grad():
            probs = torch.softmax(self._model(batch), dim=1)
            conf, idx = probs.max(dim=1)
        return [(self.classes[int(i)], round(float(c), 3)) for i, c in zip(idx.tolist(), conf.tolist())]
