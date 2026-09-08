"""Clasificador EfficientNet-B3 entrenado — ADR-0007, DD-ML-001 (Fase C3).

Adaptador REAL de `ClassifierPort`: carga el modelo entrenado sobre el dataset
MetaClass (`models/classifier.pth`) y clasifica cada cromosoma detectado. Import
de torch perezoso: si torch o el modelo no están, el pipeline cae al
`PlaceholderClassifier` (backend-ml sigue corriendo, RN-07).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np

from .asignacion import PENALIZACION, repartir
from .ports import ClassifierPort
from .preprocess import letterbox, reference_height
from .segmentation import Detection

MODELS_DIR = Path(__file__).resolve().parent.parent / 'models'

#: Interruptor del reparto global (ADR-0033). Apagado por defecto: el ADR está
#: en `proposed`, no en `accepted`, y encenderlo por defecto sería desplegar una
#: decisión sin firmar. Existe para poder comparar los dos caminos sobre los
#: mismos casos, igual que `CLINIC_LLM_ENABLED` en el backend clínico.
ASIGNACION_ENV = 'ML_ASIGNACION_ENABLED'


def _asignacion_activada() -> bool:
    return os.environ.get(ASIGNACION_ENV, '').strip().lower() in ('1', 'true', 'yes', 'on')


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
        self._asignacion = _asignacion_activada()

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
        # ADR-0033 D5: el reparto cambia la clase que se persiste, así que
        # también tiene que aparecer aquí.
        base = f'efficientnet-b3-metaclass-{self._version}'
        return f'{base}+asignacion-p{PENALIZACION}' if self._asignacion else base

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
            probs = torch.softmax(self._model(batch), dim=1).cpu().numpy()

        if self._asignacion:
            # ADR-0033: el modelo propone la distribución, el código reparte
            # respetando la estructura del cariotipo (2 copias por autosoma,
            # con cupo blando para no prohibir las trisomías).
            elegidas = repartir(probs, PENALIZACION)
        else:
            elegidas = probs.argmax(axis=1)

        # ADR-0033 D4: la confianza sigue siendo la del MODELO para la clase
        # finalmente elegida, no el coste de la asignación. Mezclarlas daría un
        # número sin significado clínico y rompería la comparabilidad con todas
        # las mediciones anteriores.
        return [(self.classes[int(i)], round(float(probs[fila, i]), 3))
                for fila, i in enumerate(elegidas)]
