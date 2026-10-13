"""La metafase del cariotipo y su entrega al visor (DD-KARYO-006, T1).

Dos partes:

- `metafase.py`: qué imagen es la del cariotipo, cuándo unos bytes son una
  imagen y que la ruta no salga de MEDIA_ROOT. Los marcadores falsos de abajo
  son copia de los que se encontraron en `media/` el 13/10: empiezan con una
  firma válida y aun así no son imágenes.
- `MetaphaseImageView`: el mismo alcance que el visor (403 a un analista
  ajeno), y 404 NO_METAPHASE_IMAGE como degradación, no como error.
"""
import struct

import pytest

from apps.samples.metafase import metafase_segmentada, ruta_segura, tipo_de_imagen
from apps.samples.models import Karyotype, Sample, SampleImage, SampleImageSource

pytestmark = pytest.mark.django_db


# ----------------------------------------------------------------------------
# Bytes de prueba
# ----------------------------------------------------------------------------
def bmp(ancho=4, alto=3, bits=24):
    """BMP mínimo pero completo: cabecera de 54 bytes y todos sus píxeles."""
    fila = ((ancho * bits + 31) // 32) * 4
    # abs(): un BMP de arriba abajo declara alto negativo y tiene los mismos
    # píxeles. Sin abs() este generador fabricaba un BMP vacío y el detector,
    # con razón, lo rechazaba: el fallo era del instrumento, no del código.
    pixeles = b'\x80' * (fila * abs(alto))
    cabecera = (b'BM' + struct.pack('<IHHI', 54 + len(pixeles), 0, 0, 54)
                + struct.pack('<IiiHHIIiiII', 40, ancho, alto, 1, bits, 0, len(pixeles), 0, 0, 0, 0))
    return cabecera + pixeles


PNG = (b'\x89PNG\r\n\x1a\n' + b'\x00\x00\x00\rIHDR' + b'\x00' * 17 + b'IEND')
JPEG = b'\xff\xd8\xff\xe0' + b'\x00' * 40 + b'\xff\xd9'

# Marcadores reales de media/ (13/10): firma válida, pero no son imágenes.
MARCADOR_BM_CEROS = b'BM' + b'\x00' * 52
MARCADOR_BMP_SIN_PIXELES = bmp()[:54]
MARCADOR_JPEG_SIN_FIN = b'\xff\xd8\xff\xe0' + b'00000000'
MARCADOR_TEXTO = b'hello world'


@pytest.fixture
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    return tmp_path


def _escribir(media, ruta, contenido):
    destino = media / ruta
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(contenido)
    return ruta


# ============================================================================
# tipo_de_imagen
# ============================================================================
class TestTipoDeImagen:
    @pytest.mark.parametrize('contenido, esperado', [
        (bmp(), 'image/bmp'),
        (bmp(ancho=60, alto=119, bits=8), 'image/bmp'),
        (bmp(alto=-3), 'image/bmp'),          # BMP de arriba abajo: alto negativo
        (PNG, 'image/png'),
        (JPEG, 'image/jpeg'),
    ])
    def test_reconoce_imagenes(self, media, contenido, esperado):
        assert tipo_de_imagen(media / _escribir(media, 'x.img', contenido)) == esperado

    @pytest.mark.parametrize('contenido', [
        MARCADOR_BM_CEROS, MARCADOR_BMP_SIN_PIXELES, MARCADOR_JPEG_SIN_FIN, MARCADOR_TEXTO,
        bmp()[:-1],                              # BMP truncado: le falta un byte de píxeles
        b'\x89PNG\r\n\x1a\n' + b'\x00' * 20,      # firma PNG sin IHDR
        b'',
    ])
    def test_rechaza_lo_que_solo_parece_una_imagen(self, media, contenido):
        assert tipo_de_imagen(media / _escribir(media, 'x.img', contenido)) is None

    def test_rechaza_bmp_sin_bits_por_pixel(self, media):
        malo = bytearray(bmp())
        malo[28:30] = b'\x00\x00'
        assert tipo_de_imagen(media / _escribir(media, 'x.img', bytes(malo))) is None


# ============================================================================
# ruta_segura
# ============================================================================
class TestRutaSegura:
    def test_dentro_de_media(self, media):
        _escribir(media, 'CHN-1/a.img', bmp())
        assert ruta_segura('CHN-1/a.img') == (media / 'CHN-1/a.img').resolve()

    def test_no_sale_de_media(self, media, tmp_path_factory):
        fuera = tmp_path_factory.mktemp('fuera') / 'secreto.img'
        fuera.write_bytes(bmp())
        assert ruta_segura('../' + fuera.parent.name + '/secreto.img') is None
        assert ruta_segura(str(fuera)) is None

    def test_fichero_ausente_o_ruta_vacia(self, media):
        assert ruta_segura('CHN-1/no-existe.img') is None
        assert ruta_segura('') is None

    def test_un_directorio_no_es_una_imagen(self, media):
        (media / 'CHN-1').mkdir()
        assert ruta_segura('CHN-1') is None


# ============================================================================
# metafase_segmentada
# ============================================================================
class TestMetafaseSegmentada:
    def test_elige_la_de_menor_orden(self, analyst_user):
        s = Sample.objects.create(chn_code='CHN-2026-10-13-0001', patient_ref='ANON', analyst=analyst_user)
        SampleImage.objects.create(sample=s, image_path='b.img', order=1, source=SampleImageSource.UPLOAD)
        primera = SampleImage.objects.create(sample=s, image_path='a.img', order=0, source=SampleImageSource.UPLOAD)
        assert metafase_segmentada(s) == primera

    def test_sin_imagenes(self, analyst_user):
        s = Sample.objects.create(chn_code='CHN-2026-10-13-0002', patient_ref='ANON', analyst=analyst_user)
        assert metafase_segmentada(s) is None


# ============================================================================
# MetaphaseImageView
# ============================================================================
def _url(sample):
    return f'/api/clinic/samples/{sample.id}/karyotype/metaphase/'


def _caso(dueno, chn, media=None, contenido=None, con_cariotipo=True):
    s = Sample.objects.create(chn_code=chn, patient_ref='ANON', analyst=dueno)
    if con_cariotipo:
        Karyotype.objects.create(sample=s)
    if contenido is not None:
        ruta = _escribir(media, f'{chn}/0.img', contenido)
        SampleImage.objects.create(sample=s, image_path=ruta, order=0, source=SampleImageSource.UPLOAD)
    return s


@pytest.fixture
def otro_analista(django_user_model):
    return django_user_model.objects.create_user(username='otra_analista_metafase', password='x')


class TestMetaphaseImageView:
    def test_el_dueno_recibe_la_imagen(self, analyst_client, analyst_user, media):
        s = _caso(analyst_user, 'CHN-2026-10-13-0010', media, bmp())
        resp = analyst_client.get(_url(s))
        assert resp.status_code == 200
        assert resp['Content-Type'] == 'image/bmp'
        assert b''.join(resp.streaming_content) == bmp()
        assert resp['Cache-Control'] == 'private, max-age=300'
        assert resp['X-Content-Type-Options'] == 'nosniff'

    def test_el_supervisor_ve_cualquier_caso(self, supervisor_client, otro_analista, media):
        s = _caso(otro_analista, 'CHN-2026-10-13-0011', media, PNG)
        resp = supervisor_client.get(_url(s))
        assert resp.status_code == 200
        assert resp['Content-Type'] == 'image/png'

    def test_un_analista_no_ve_la_metafase_de_otro(self, analyst_client, otro_analista, media):
        """AI-SEC-001: misma regla que el visor, no una segunda."""
        s = _caso(otro_analista, 'CHN-2026-10-13-0012', media, bmp())
        resp = analyst_client.get(_url(s))
        assert resp.status_code == 403
        assert resp.data['code'] == 'NOT_OWNER'

    def test_sin_sesion_401(self, api_client, analyst_user, media):
        s = _caso(analyst_user, 'CHN-2026-10-13-0013', media, bmp())
        assert api_client.get(_url(s)).status_code == 401

    def test_muestra_inexistente_404(self, analyst_client):
        resp = analyst_client.get('/api/clinic/samples/00000000-0000-0000-0000-000000000000/karyotype/metaphase/')
        assert resp.status_code == 404
        assert resp.data['code'] == 'NOT_FOUND'

    def test_sin_cariotipo_404(self, analyst_client, analyst_user, media):
        s = _caso(analyst_user, 'CHN-2026-10-13-0014', media, bmp(), con_cariotipo=False)
        resp = analyst_client.get(_url(s))
        assert resp.status_code == 404
        assert resp.data['code'] == 'NO_KARYOTYPE'

    @pytest.mark.parametrize('contenido', [MARCADOR_BM_CEROS, MARCADOR_JPEG_SIN_FIN, MARCADOR_TEXTO])
    def test_un_marcador_no_se_sirve_como_imagen(self, analyst_client, analyst_user, media, contenido):
        """Degradación (D5): el cliente pinta rectángulos en vez de una imagen rota."""
        s = _caso(analyst_user, 'CHN-2026-10-13-0015', media, contenido)
        resp = analyst_client.get(_url(s))
        assert resp.status_code == 404
        assert resp.data['code'] == 'NO_METAPHASE_IMAGE'

    def test_sin_imagen_registrada_404(self, analyst_client, analyst_user, media):
        s = _caso(analyst_user, 'CHN-2026-10-13-0016')
        assert analyst_client.get(_url(s)).data['code'] == 'NO_METAPHASE_IMAGE'

    def test_fichero_borrado_404(self, analyst_client, analyst_user, media):
        s = _caso(analyst_user, 'CHN-2026-10-13-0017', media, bmp())
        (media / 'CHN-2026-10-13-0017/0.img').unlink()
        assert analyst_client.get(_url(s)).data['code'] == 'NO_METAPHASE_IMAGE'

    def test_una_ruta_que_sale_de_media_no_se_abre(self, analyst_client, analyst_user, media, tmp_path_factory):
        fuera = tmp_path_factory.mktemp('fuera_vista') / 'x.img'
        fuera.write_bytes(bmp())
        s = _caso(analyst_user, 'CHN-2026-10-13-0018')
        SampleImage.objects.create(sample=s, image_path=f'../{fuera.parent.name}/x.img', order=0,
                                   source=SampleImageSource.UPLOAD)
        assert analyst_client.get(_url(s)).data['code'] == 'NO_METAPHASE_IMAGE'

    def test_sirve_la_imagen_segmentada_no_otra(self, analyst_client, analyst_user, media):
        """D4: la de orden 0, aunque haya más metafases en el caso."""
        s = _caso(analyst_user, 'CHN-2026-10-13-0019', media, bmp(ancho=4))
        otra = _escribir(media, 'CHN-2026-10-13-0019/1.img', bmp(ancho=8))
        SampleImage.objects.create(sample=s, image_path=otra, order=1, source=SampleImageSource.UPLOAD)
        resp = analyst_client.get(_url(s))
        assert b''.join(resp.streaming_content) == bmp(ancho=4)
