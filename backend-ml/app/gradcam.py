"""Grad-CAM real sobre el clasificador EfficientNet-B3 (ADR-0007, XAI).

Sustituye al mapa simulado. La diferencia importa más de lo que parece: el
sistema **obliga** al analista a consultar la explicabilidad antes de resolver
un cromosoma naranja (BR-004). Enseñarle un cuadrado de color en vez de una
explicación real convierte ese control en atrezo — crea la apariencia de que el
sistema justifica su decisión cuando no lo hace, que es lo contrario de lo que
persigue todo el diseño.

## Cómo funciona, en tres pasos

1. Se engancha un *hook* a la última capa convolucional (`model.features[-1]`),
   que es donde las activaciones todavía conservan estructura espacial pero ya
   representan conceptos y no bordes.
2. Se hace la pasada hacia delante y se retropropaga **la clase predicha**. El
   gradiente dice cuánto habría cambiado esa puntuación si cada activación
   hubiera sido distinta: eso es «cuánto importó».
3. Se pesa cada mapa de activación por su gradiente promedio, se suman, y se
   aplica ReLU — solo interesa lo que empuja **a favor** de la clase, no en
   contra.

## Por qué reutiliza el preprocesado del clasificador

El mapa tiene que corresponder a **lo que el modelo vio**. Si aquí se recortara
o escalara distinto que en `classify_all`, el calor señalaría píxeles que no son
los que produjeron esa clasificación: una explicación falsa, que es peor que
ninguna. Por eso recibe el crop ya preparado y el mismo `ref_h` de la metafase.
"""
from __future__ import annotations

import base64
import io

import numpy as np

from .preprocess import letterbox


class GradCamNoDisponible(Exception):
    """El modelo no permite calcular Grad-CAM (sin torch, o sin capa objetivo)."""


def _capa_objetivo(model):
    """La última capa convolucional de EfficientNet-B3.

    `features[-1]` es el bloque final antes del pooling: 1536 canales sobre una
    rejilla de ~10x10 para entradas de 300px. Bajar más da mapas más finos pero
    de bordes; subir más pierde toda la localización.
    """
    features = getattr(model, 'features', None)
    if features is None or len(features) == 0:
        raise GradCamNoDisponible('el modelo no expone `features`')
    return features[-1]


def _mapa_calor(clasificador, crop_gray: np.ndarray, ref_h: float) -> np.ndarray:
    """Devuelve el mapa de activación normalizado a [0,1], del tamaño del crop."""
    torch = clasificador._torch
    model = clasificador._model
    capa = _capa_objetivo(model)

    # Mismo preprocesado que classify_all: el mapa debe corresponder a lo visto.
    if clasificador._preprocess == 'letterbox':
        img = letterbox(crop_gray, ref_h, canvas=clasificador._img_size)
    else:
        img = clasificador._Image.fromarray(crop_gray)
    tensor = clasificador._tf(img).unsqueeze(0)

    activaciones: list = []
    gradientes: list = []

    def guarda_activacion(_m, _entrada, salida):
        activaciones.append(salida)

    def guarda_gradiente(_m, _grad_entrada, grad_salida):
        gradientes.append(grad_salida[0])

    h1 = capa.register_forward_hook(guarda_activacion)
    # full_backward_hook es el sustituto no deprecado de backward_hook.
    h2 = capa.register_full_backward_hook(guarda_gradiente)

    try:
        # Grad-CAM necesita gradientes: no se puede usar torch.no_grad() aquí,
        # a diferencia del resto de la inferencia.
        salida = model(tensor)
        clase = int(salida.argmax(dim=1).item())
        model.zero_grad(set_to_none=True)
        salida[0, clase].backward()
    finally:
        h1.remove()
        h2.remove()

    if not activaciones or not gradientes:
        raise GradCamNoDisponible('los hooks no capturaron nada')

    act = activaciones[0].detach()[0]        # (C, H, W)
    grad = gradientes[0].detach()[0]         # (C, H, W)

    pesos = grad.mean(dim=(1, 2))            # importancia media por canal
    mapa = torch.relu((pesos[:, None, None] * act).sum(dim=0))

    mapa = mapa.cpu().numpy().astype(np.float32)
    if mapa.max() > mapa.min():
        mapa = (mapa - mapa.min()) / (mapa.max() - mapa.min())
    else:
        mapa = np.zeros_like(mapa)           # activación plana: nada que destacar

    import cv2
    return cv2.resize(mapa, (crop_gray.shape[1], crop_gray.shape[0]),
                      interpolation=cv2.INTER_CUBIC)


def heatmap_png(clasificador, crop_gray: np.ndarray, ref_h: float = 0.0,
                alpha: float = 0.45) -> str:
    """Grad-CAM del crop, superpuesto sobre el cromosoma, en PNG base64.

    Se superpone en vez de devolver el mapa suelto porque un mapa de calor sin
    el cromosoma debajo no le dice nada al analista: necesita ver *qué banda*
    del cromosoma pesó en la decisión.
    """
    import cv2

    mapa = _mapa_calor(clasificador, crop_gray, ref_h)

    color = cv2.applyColorMap((mapa * 255).astype(np.uint8), cv2.COLORMAP_JET)
    base = cv2.cvtColor(crop_gray, cv2.COLOR_GRAY2BGR)
    mezcla = cv2.addWeighted(base, 1.0 - alpha, color, alpha, 0)

    ok, buf = cv2.imencode('.png', mezcla)
    if not ok:
        raise GradCamNoDisponible('no se pudo codificar el PNG')
    return base64.b64encode(buf.tobytes()).decode('ascii')


def resumen_activacion(clasificador, crop_gray: np.ndarray,
                       ref_h: float = 0.0) -> dict:
    """Dónde se concentra la atención, en términos que un informe pueda citar.

    El PNG es para mirar; esto es para auditar: queda en el evento XAI_VIEWED y
    permite revisar después por qué el modelo dijo lo que dijo sin volver a
    generar la imagen.
    """
    mapa = _mapa_calor(clasificador, crop_gray, ref_h)
    alto = mapa.shape[0]
    tercios = {
        'superior': float(mapa[:alto // 3].mean()),
        'medio': float(mapa[alto // 3: 2 * alto // 3].mean()),
        'inferior': float(mapa[2 * alto // 3:].mean()),
    }
    foco = max(tercios, key=tercios.get)
    return {
        'foco': foco,
        'reparto': {k: round(v, 3) for k, v in tercios.items()},
        # Fracción del cromosoma que concentra activación alta: si es muy
        # grande, el modelo no está mirando nada en concreto.
        'concentracion': round(float((mapa > 0.5).mean()), 3),
    }
