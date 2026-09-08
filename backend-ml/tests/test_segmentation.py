"""Tests de la segmentación y el pipeline (ADR-0007, DD-ML-001)."""
import cv2
import numpy as np

from app.classifier import PlaceholderClassifier, assign_placeholder_classes
from app.pipeline import run_pipeline
from app.segmentation import load_gray, segment


class TestSegmentation:
    def test_detecta_los_cromosomas_sinteticos(self, synthetic_gray):
        dets = segment(synthetic_gray)
        # 12 elipses bien separadas → deberían detectarse ~12 (tolerancia).
        assert 10 <= len(dets) <= 14
        for d in dets:
            assert d.area >= 250
            x, y, w, h = d.bbox
            assert w > 0 and h > 0

    def test_imagen_en_blanco_no_detecta_nada(self):
        blank = np.full((200, 200), 255, dtype=np.uint8)
        assert segment(blank) == []


    def test_load_gray_decodifica_png(self, synthetic_png_bytes):
        gray = load_gray(synthetic_png_bytes)
        assert gray.ndim == 2 and gray.shape[0] > 0

    def test_load_gray_rechaza_basura(self):
        import pytest
        with pytest.raises(ValueError):
            load_gray(b'no soy una imagen')


class TestNucleoInterfasico:
    """Regresión del fallo de escala del umbral de distancia.

    Las preparaciones de metafase suelen traer un **núcleo interfásico**: un
    blob redondo y grueso junto a los cromosomas. Con el umbral de marcadores
    calculado sobre el máximo GLOBAL de la transformada de distancia, ese núcleo
    fijaba un listón que ningún cromosoma alcanzaba, dejándolos sin marcador —
    y watershed los fundía en un solo objeto. Se medía en 18 de 120 metafases
    reales: el sistema informaba 1 o 2 cromosomas donde había ~46.

    Es un fallo silencioso y clínicamente grave: no lanza error, devuelve un
    recuento plausible pero falso.
    """

    @staticmethod
    def _con_nucleo(nucleo: bool):
        """Barras finas (cromosomas) y, opcionalmente, un disco grueso."""
        img = np.full((400, 400), 235, dtype=np.uint8)
        for i in range(8):
            x = 30 + i * 42
            cv2.rectangle(img, (x, 60), (x + 14, 170), 40, -1)
        if nucleo:
            cv2.circle(img, (200, 300), 70, 30, -1)
        return img

    def test_el_nucleo_no_borra_los_cromosomas(self):
        detectados = len(segment(self._con_nucleo(nucleo=True)))
        # 8 barras + el núcleo. Lo que se prohíbe es el colapso a ~1.
        assert detectados >= 8, f'el núcleo se llevó los cromosomas: {detectados}'

    def test_el_nucleo_no_cambia_el_recuento_de_cromosomas(self):
        """La propiedad de fondo: agregar un objeto de otra escala no debe
        alterar cuántos cromosomas se ven."""
        sin_n = len(segment(self._con_nucleo(nucleo=False)))
        con_n = len(segment(self._con_nucleo(nucleo=True)))
        assert con_n - sin_n == 1, f'sin núcleo {sin_n}, con núcleo {con_n}'


class TestPlaceholderClassifier:
    def test_asigna_clases_por_rango_de_tamano(self):
        # El más grande → '1', el segundo más grande → '1' (par), etc.
        areas = [100, 5000, 4000, 90]
        classes = assign_placeholder_classes(areas)
        assert classes[1] == '1'  # área 5000 (mayor)
        assert classes[2] == '1'  # área 4000 (2º mayor) → completa el par 1
        assert len(classes) == 4


class TestPipeline:
    def test_pipeline_entrega_estructura_completa(self, synthetic_gray):
        # Clasificador explícito (placeholder) → determinístico sin depender de torch.
        res = run_pipeline(synthetic_gray, classifier=PlaceholderClassifier())
        assert res.chromosome_count == len(res.chromosomes)
        assert res.chromosome_count >= 10
        assert res.model_version.startswith('opencv-watershed')
        assert 'placeholder' in res.classifier
        assert res.confidence_avg == 0.55  # placeholder → confianza baja fija (naranja)
        for c in res.chromosomes:
            assert c.predicted_class in [str(n) for n in range(1, 23)] + ['X', 'Y']
            assert c.bbox.w > 0 and c.bbox.h > 0

    def test_pipeline_imagen_vacia(self):
        res = run_pipeline(np.full((100, 100), 255, dtype=np.uint8), classifier=PlaceholderClassifier())
        assert res.chromosome_count == 0
        assert res.confidence_avg == 0.0
