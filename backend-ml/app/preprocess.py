"""Preprocesamiento de crops de cromosomas — ADR-0007, DD-ML-001 (Fase C4).

FUENTE ÚNICA DE VERDAD del preprocesamiento. Entrenamiento e inferencia deben
usar exactamente esta función: si divergen, el modelo ve en producción algo
distinto de lo que vio al entrenar y la precisión cae sin síntoma visible.

Por qué letterbox y no `Resize((224,224))`:
un citogenetista clasifica un cromosoma por su TAMAÑO RELATIVO al resto de la
metafase y por su RELACIÓN DE ASPECTO (posición del centrómero). Redimensionar
cada crop a un cuadrado destruye ambas señales — el cromosoma 1 (H/W 3.6) y el
21 (H/W 1.2) llegan a la red con la misma forma y el mismo tamaño.

Aquí se preserva:
  - la relación de aspecto (se rellena, no se deforma),
  - la escala relativa: cada crop se escala contra `ref_h`, la altura mediana de
    los cromosomas de SU MISMA imagen. Es invariante al zoom del microscopio
    pero conserva que el 1 es ~2x la mediana y el 21 ~0.4x.
"""
from __future__ import annotations

import numpy as np
from PIL import Image

CANVAS = 224
TARGET_FRAC = 0.45   # un cromosoma de altura mediana ocupa 45% del lienzo
FILL = 255           # fondo blanco (los crops MetaClass son oscuro sobre claro)


def letterbox(
    crop: np.ndarray,
    ref_h: float,
    canvas: int = CANVAS,
    target_frac: float = TARGET_FRAC,
    fill: int = FILL,
) -> Image.Image:
    """Escala `crop` conservando aspecto y escala relativa, centrado en el lienzo.

    `ref_h` es la altura mediana de los cromosomas de la misma imagen. Con
    ref_h <= 0 se cae a un ajuste por tamaño propio (sin señal de escala).
    """
    if crop.ndim == 3:
        crop = crop[..., 0]
    h, w = crop.shape[:2]
    if h < 1 or w < 1:
        return Image.new('L', (canvas, canvas), fill)

    if ref_h and ref_h > 0:
        scale = (target_frac * canvas) / float(ref_h)
    else:
        scale = canvas / float(max(h, w))

    # nunca desbordar el lienzo (crops anómalos: cromosomas pegados)
    scale = min(scale, canvas / float(max(h, w)))

    new_h = max(1, int(round(h * scale)))
    new_w = max(1, int(round(w * scale)))

    img = Image.fromarray(crop.astype(np.uint8), mode='L')
    img = img.resize((new_w, new_h), Image.BILINEAR)

    out = Image.new('L', (canvas, canvas), fill)
    out.paste(img, ((canvas - new_w) // 2, (canvas - new_h) // 2))
    return out


def reference_height(heights) -> float:
    """Altura mediana de los cromosomas de una imagen (la escala de referencia)."""
    vals = [float(h) for h in heights if h and h > 0]
    return float(np.median(vals)) if vals else 0.0
