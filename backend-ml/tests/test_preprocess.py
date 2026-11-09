"""Tests del preprocesamiento de crops (Fase C4, ADR-0007).

Protegen las dos propiedades que el `Resize((224,224))` del v1 destruía y que son
la señal discriminante del citogenetista: relación de aspecto y escala relativa.
Si alguien vuelve a meter un resize deformante, estos tests fallan.

No requieren torch ni el dataset real (CI-safe).
"""
import numpy as np
import pytest

from app.preprocess import CANVAS, FILL, letterbox, reference_height


def _crop(w: int, h: int, value: int = 40) -> np.ndarray:
    """Crop sintético: un bloque oscuro de w x h (un 'cromosoma')."""
    return np.full((h, w), value, dtype=np.uint8)


def _ink_bbox(img):
    """Caja del contenido no-fondo dentro del lienzo."""
    a = np.asarray(img)
    ys, xs = np.where(a < FILL - 10)
    assert xs.size, 'el lienzo quedó vacío'
    return xs.min(), ys.min(), xs.max() - xs.min() + 1, ys.max() - ys.min() + 1


class TestLetterbox:
    def test_salida_es_el_lienzo_cuadrado(self):
        out = letterbox(_crop(37, 133), ref_h=70.0)
        assert out.size == (CANVAS, CANVAS)
        assert out.mode == 'L'

    def test_preserva_la_relacion_de_aspecto(self):
        """Un cromosoma 1 (H/W 3.6) NO puede salir con la forma de un 21 (H/W 1.2)."""
        for w, h in [(37, 133), (26, 29), (32, 89)]:
            _, _, bw, bh = _ink_bbox(letterbox(_crop(w, h), ref_h=70.0))
            assert bh / bw == pytest.approx(h / w, rel=0.08), f'aspecto perdido en {w}x{h}'

    def test_preserva_la_escala_relativa(self):
        """El 1 (133px) debe ocupar mucha más área que el 21 (29px) con la misma
        referencia. Con Resize ambos ocupaban exactamente lo mismo."""
        ref = 70.0
        _, _, w1, h1 = _ink_bbox(letterbox(_crop(37, 133), ref))
        _, _, w21, h21 = _ink_bbox(letterbox(_crop(26, 29), ref))
        assert h1 > h21 * 3, 'el cromosoma grande no quedó proporcionalmente mayor'
        assert (w1 * h1) > (w21 * h21) * 3

    def test_invariante_al_zoom_del_microscopio(self):
        """Duplicar la escala de TODA la imagen (crop y referencia) debe dar
        prácticamente el mismo lienzo: es escala relativa, no absoluta."""
        a = _ink_bbox(letterbox(_crop(30, 90), ref_h=60.0))
        b = _ink_bbox(letterbox(_crop(60, 180), ref_h=120.0))
        assert b[3] == pytest.approx(a[3], rel=0.05)
        assert b[2] == pytest.approx(a[2], rel=0.05)

    def test_queda_centrado(self):
        x, y, bw, bh = _ink_bbox(letterbox(_crop(30, 90), ref_h=70.0))
        assert abs((x + bw / 2) - CANVAS / 2) <= 1.5
        assert abs((y + bh / 2) - CANVAS / 2) <= 1.5

    def test_el_relleno_es_fondo_blanco(self):
        """El padding debe mimetizarse con el fondo de la lámina, no crear un
        borde negro que la red aprenda como si fuera señal."""
        a = np.asarray(letterbox(_crop(20, 100), ref_h=70.0))
        assert a[0, 0] == FILL and a[-1, -1] == FILL

    def test_nunca_desborda_el_lienzo(self):
        """Un cromosoma enorme (o un cluster mal segmentado) no puede recortarse."""
        for w, h in [(400, 900), (900, 400), (300, 300)]:
            _, _, bw, bh = _ink_bbox(letterbox(_crop(w, h), ref_h=5.0))
            assert bw <= CANVAS and bh <= CANVAS

    @pytest.mark.parametrize('ref', [0.0, -1.0, None])
    def test_sin_referencia_no_revienta(self, ref):
        out = letterbox(_crop(30, 90), ref_h=ref or 0.0)
        assert out.size == (CANVAS, CANVAS)

    def test_crop_degenerado_no_revienta(self):
        assert letterbox(np.zeros((0, 0), dtype=np.uint8), 70.0).size == (CANVAS, CANVAS)

    def test_acepta_crop_de_3_canales(self):
        rgb = np.full((90, 30, 3), 40, dtype=np.uint8)
        assert letterbox(rgb, 70.0).size == (CANVAS, CANVAS)


class TestReferenceHeight:
    def test_es_la_mediana(self):
        assert reference_height([10, 20, 30, 40, 50]) == 30.0

    def test_ignora_valores_invalidos(self):
        assert reference_height([0, -5, 20, 40, None]) == 30.0

    def test_lista_vacia_da_cero(self):
        assert reference_height([]) == 0.0
        assert reference_height([0, -1]) == 0.0
