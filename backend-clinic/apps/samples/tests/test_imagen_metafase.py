"""Guardrail: una imagen que no puede ser una metafase no entra al pipeline.

## De dónde sale esto

Ensayando la demo se subieron por error tres recortes de cromosomas sueltos en
vez de fotografías de metafase. El sistema los aceptó, el pipeline segmento uno
de ellos, y produjo un cariotipo de UN cromosoma sin avisar de nada. Basura
entra, cariotipo sale.

Las medidas reales de aquel caso, que son las que se usan como fixture:
60x119, 183x248 y 405x305 px. Una metafase del archivo del laboratorio mide
como minimo 1024x768 (medido sobre las 460 del dataset).
"""
import base64
import struct

import pytest
from django.contrib.auth import get_user_model

from apps.samples.imagen import (
    ALTO_MINIMO,
    ANCHO_MINIMO,
    dimensiones,
    es_metafase_plausible,
)
from apps.samples.models import Sample
from apps.samples.services import ImagenNoEsMetafaseError, SampleRegistrationService


# --- constructores de imagen minimos, sin dependencias ----------------------

def bmp(ancho: int, alto: int) -> bytes:
    """Cabecera BMP valida; los pixeles no importan, solo se leen las medidas."""
    cabecera_dib = struct.pack('<Iii HH IIiiII', 40, ancho, alto, 1, 24, 0, 0, 0, 0, 0, 0)
    return b'BM' + struct.pack('<IHHI', 54, 0, 0, 54) + cabecera_dib


def png(ancho: int, alto: int) -> bytes:
    return (b'\x89PNG\r\n\x1a\n' + struct.pack('>I', 13) + b'IHDR'
            + struct.pack('>II', ancho, alto) + b'\x08\x02\x00\x00\x00')


def jpeg(ancho: int, alto: int) -> bytes:
    sof = b'\xff\xc0' + struct.pack('>HB HH B', 17, 8, alto, ancho, 3) + b'\x00' * 9
    return b'\xff\xd8' + b'\xff\xe0' + struct.pack('>H', 16) + b'\x00' * 14 + sof


# --- lectura de dimensiones -------------------------------------------------

@pytest.mark.parametrize('constructor', [bmp, png, jpeg])
def test_lee_las_dimensiones_de_cada_formato(constructor):
    assert dimensiones(constructor(1024, 768)) == (1024, 768)


def test_bmp_de_arriba_abajo_tiene_alto_negativo_y_se_normaliza():
    crudo = bytearray(bmp(1024, 768))
    crudo[22:26] = struct.pack('<i', -768)
    assert dimensiones(bytes(crudo)) == (1024, 768)


def test_formato_desconocido_devuelve_none():
    assert dimensiones(b'esto no es una imagen') is None


def test_lo_que_no_se_puede_medir_se_deja_pasar():
    """None significa «no lo se», y ante la duda no se bloquea al usuario."""
    assert es_metafase_plausible(b'formato raro pero quiza valido') is True


# --- el umbral --------------------------------------------------------------

@pytest.mark.parametrize('ancho,alto', [(60, 119), (183, 248), (405, 305)])
def test_los_recortes_del_caso_real_se_rechazan(ancho, alto):
    assert es_metafase_plausible(bmp(ancho, alto)) is False


@pytest.mark.parametrize('ancho,alto', [(1024, 768), (1024, 1177), (1280, 1290)])
def test_las_metafases_reales_del_dataset_pasan(ancho, alto):
    assert es_metafase_plausible(bmp(ancho, alto)) is True


def test_el_limite_exacto_se_acepta():
    assert es_metafase_plausible(bmp(ANCHO_MINIMO, ALTO_MINIMO)) is True


def test_un_pixel_por_debajo_se_rechaza():
    assert es_metafase_plausible(bmp(ANCHO_MINIMO - 1, ALTO_MINIMO)) is False
    assert es_metafase_plausible(bmp(ANCHO_MINIMO, ALTO_MINIMO - 1)) is False


# --- integracion con el registro -------------------------------------------

def como_carga(datos: bytes) -> dict:
    return {'filename': 'x.bmp', 'data_base64': base64.b64encode(datos).decode(),
            'source': 'upload'}


def payload(imagenes: list, chn: str, borrador: bool = False) -> dict:
    return {
        'patient': {'full_name': 'PRUEBA', 'document_id': '0'},
        'sample': {'chn_code': chn, 'sample_type': 'sangre'},
        'clinical_history': {}, 'analysis_requests': [],
        'images': imagenes, 'is_draft': borrador,
    }


@pytest.fixture
def analista(db):
    return get_user_model().objects.create(username='analista_guardrail')


@pytest.mark.django_db
def test_registrar_con_un_recorte_falla_y_no_crea_la_muestra(analista):
    """Lo importante no es solo el error: es que no quede basura a medias."""
    servicio = SampleRegistrationService()
    with pytest.raises(ImagenNoEsMetafaseError) as exc:
        servicio.register(payload([como_carga(bmp(60, 119))], 'CHN-2026-01-01-0001'), analista)

    assert '60x119' in str(exc.value)
    assert not Sample.objects.filter(chn_code='CHN-2026-01-01-0001').exists()


@pytest.mark.django_db
def test_detecta_el_recorte_aunque_no_sea_el_primero(analista):
    """La 1a imagen es la que se segmenta, pero las demas se reprocesan luego."""
    servicio = SampleRegistrationService()
    imagenes = [como_carga(bmp(1024, 768)), como_carga(bmp(60, 119))]
    with pytest.raises(ImagenNoEsMetafaseError) as exc:
        servicio.register(payload(imagenes, 'CHN-2026-01-01-0002'), analista)
    assert 'imagen 2' in str(exc.value)


@pytest.mark.django_db
def test_un_borrador_no_se_valida_porque_no_se_analiza(analista):
    servicio = SampleRegistrationService()
    resultado = servicio.register(
        payload([como_carga(bmp(60, 119))], 'CHN-2026-01-01-0003', borrador=True), analista)
    assert resultado['status'] == 'DRAFT'


@pytest.mark.django_db
def test_el_mensaje_orienta_en_vez_de_solo_negar(analista):
    servicio = SampleRegistrationService()
    with pytest.raises(ImagenNoEsMetafaseError) as exc:
        servicio.register(payload([como_carga(bmp(405, 305))], 'CHN-2026-01-01-0004'), analista)
    mensaje = str(exc.value)
    assert f'{ANCHO_MINIMO}x{ALTO_MINIMO}' in mensaje
    assert 'cromosoma' in mensaje


# --- ficheros malformados: «no lo sé» no es «lo rechazo» --------------------
#
# El lector es de fabricacion propia y trabaja sobre bytes que llegan de fuera.
# Estas son sus tres salidas de emergencia. Todas terminan en `None`, que
# `es_metafase_plausible` traduce a «deja pasar»: bloquear una imagen porque la
# cabecera no se supo leer seria rechazar formatos legitimos que no contemplamos.

def test_una_cabecera_truncada_no_revienta_el_registro():
    """Un BMP cortado a la mitad hace que `struct.unpack` lance. Sin el except,
    subir un fichero incompleto daria un 500 en vez de un mensaje."""
    truncado = b'BM' + b'\x00' * 10           # dice ser BMP y no llega a 26 bytes
    assert dimensiones(truncado) is None
    assert es_metafase_plausible(truncado) is True


def test_un_formato_desconocido_se_deja_pasar():
    """TIFF, por ejemplo: el laboratorio tiene equipos que exportan formatos que
    este lector no cubre. «No lo sé» tiene que dejar trabajar."""
    assert dimensiones(b'II*\x00' + b'\x00' * 40) is None
    assert es_metafase_plausible(b'II*\x00' + b'\x00' * 40) is True


def test_un_jpeg_con_relleno_entre_segmentos_se_recorre_igual():
    """Entre marcadores puede haber bytes de relleno que no son 0xFF. El lector
    avanza de uno en uno hasta el siguiente marcador en vez de rendirse."""
    cuerpo = (b'\xff\xd8'
              + b'\x00\x00\x00'                       # relleno: no empieza por FF
              + b'\xff\xc0\x00\x11\x08' + struct.pack('>HH', 768, 1024)
              + b'\x00' * 12)
    assert dimensiones(cuerpo) == (1024, 768)


def test_un_jpeg_con_una_longitud_imposible_se_abandona():
    """Una longitud de segmento menor que 2 haria que el indice no avanzara: el
    bucle se quedaria dando vueltas sobre el mismo byte para siempre."""
    cuerpo = b'\xff\xd8' + b'\xff\xe0\x00\x01' + b'\x00' * 20
    assert dimensiones(cuerpo) is None
    assert es_metafase_plausible(cuerpo) is True
