"""DD-OPS-001: tres metafases BMP reales caben en una petición de registro."""
from django.conf import settings

TAMANO_BMP_METACLASS = 3_145_782  # metafase_1.bmp, 1024 x 768 a 32 bits


def test_tres_metafases_bmp_en_base64_caben_en_el_limite():
    tres_en_base64 = 3 * TAMANO_BMP_METACLASS * 4 // 3
    assert settings.DATA_UPLOAD_MAX_MEMORY_SIZE > tres_en_base64
