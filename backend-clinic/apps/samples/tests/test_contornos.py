"""La silueta de cada cromosoma (DD-KARYO-007 D1, T1).

backend-ml calcula el contorno; backend-clinic lo guarda, lo sirve y lo
invalida cuando deja de corresponder. Se fija:

- la ingesta guarda el contorno que trae la segmentación;
- `completar_contornos` pide a backend-ml SOLO lo que falta, no toca casos
  validados (RN-04) y no cambia nada si backend-ml no responde (RN-07);
- recortar, separar y unir dejan el contorno a None: la silueta guardada era
  la del objeto de antes;
- la vista tiene el alcance de las demás ediciones (403 NOT_OWNER);
- el cliente rechaza una respuesta que no casa caja a caja.

backend-ml se sustituye por un doble: aquí se prueba la lógica clínica.
"""
from decimal import Decimal

import httpx
import pytest

from apps.samples.models import (
    AuditEvent, Chromosome, Karyotype, Sample, SampleImage, SampleImageSource,
)
from apps.samples.pipeline_client import MLDegradedError, PipelineClient
from apps.samples.services import (
    CaseLockedError, SinMetafaseError, completar_contornos, ingest_segmentation,
    join_chromosomes, recrop_chromosome, split_chromosome,
)

pytestmark = pytest.mark.django_db

CONTORNO = [[10, 20], [40, 20], [40, 110], [10, 110]]


@pytest.fixture
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    return tmp_path


def _caso(dueno, chn, media=None, status='READY', imagen=True):
    s = Sample.objects.create(chn_code=chn, patient_ref='ANON', analyst=dueno, status=status)
    k = Karyotype.objects.create(sample=s, model_version='test-v0')
    if imagen and media is not None:
        (media / chn).mkdir(parents=True, exist_ok=True)
        (media / chn / '0.img').write_bytes(b'BM' + b'\x00' * 100)
        SampleImage.objects.create(sample=s, image_path=f'{chn}/0.img', order=0,
                                   source=SampleImageSource.UPLOAD)
    return s, k


def _crom(k, bbox=None, contour=None, cls='1', order=0, activo=True):
    return Chromosome.objects.create(
        karyotype=k, predicted_class=cls, position_index=0, order=order,
        confidence_score=Decimal('0.500'), is_active=activo,
        bbox=bbox if bbox is not None else {'x': 10, 'y': 20, 'w': 30, 'h': 90},
        contour=contour,
    )


@pytest.fixture
def ml(monkeypatch):
    """Doble de /api/v1/contours/: un contorno por caja, y registra lo pedido."""
    pedidos = []

    def falso(image_bytes, bboxes, filename='m.bmp'):
        pedidos.append(list(bboxes))
        return [CONTORNO for _ in bboxes]

    monkeypatch.setattr('apps.samples.services.pipeline_client.contours', falso)
    return pedidos


# ============================================================================
# Ingesta
# ============================================================================
class TestIngesta:
    def test_guarda_el_contorno_de_la_segmentacion(self, analyst_user):
        s = Sample.objects.create(chn_code='CHN-2026-10-23-0001', patient_ref='ANON', analyst=analyst_user)
        k = ingest_segmentation(s, {'model_version': 'v', 'chromosomes': [
            {'order': 0, 'predicted_class': '1', 'confidence_score': 0.9,
             'bbox': {'x': 10, 'y': 20, 'w': 30, 'h': 90}, 'contour': CONTORNO},
            {'order': 1, 'predicted_class': '2', 'confidence_score': 0.9,
             'bbox': {'x': 50, 'y': 20, 'w': 30, 'h': 90}},  # backend-ml antiguo: sin contorno
        ]})
        c0, c1 = k.chromosomes.order_by('order')
        assert c0.contour == CONTORNO
        assert c1.contour is None


# ============================================================================
# completar_contornos
# ============================================================================
class TestCompletarContornos:
    def test_pide_solo_lo_que_falta(self, analyst_user, media, ml):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0002', media)
        falta = _crom(k, order=0)
        _crom(k, contour=CONTORNO, order=1)                          # ya lo tiene
        _crom(k, bbox={}, order=2)                                    # sin caja: no se puede
        _crom(k, order=3, activo=False)                               # absorbido por un JOIN
        assert completar_contornos(s) == 1
        assert ml == [[falta.bbox]]
        falta.refresh_from_db()
        assert falta.contour == CONTORNO

    def test_nada_que_completar_no_llama_a_backend_ml(self, analyst_user, media, ml):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0003', media)
        _crom(k, contour=CONTORNO)
        assert completar_contornos(s) == 0
        assert ml == []

    def test_no_emite_evento_de_auditoria(self, analyst_user, media, ml):
        """Es dato derivado de la imagen, no una corrección del analista."""
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0004', media)
        _crom(k)
        completar_contornos(s)
        assert AuditEvent.objects.filter(sample=s).count() == 0

    def test_un_contorno_nulo_no_se_guarda(self, analyst_user, media, monkeypatch):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0005', media)
        c = _crom(k)
        monkeypatch.setattr('apps.samples.services.pipeline_client.contours',
                            lambda img, bboxes, filename='': [None])
        assert completar_contornos(s) == 0
        c.refresh_from_db()
        assert c.contour is None

    @pytest.mark.parametrize('estado', ['ANALYST_VALIDATED', 'VALIDATED'])
    def test_no_toca_un_caso_validado(self, analyst_user, media, ml, estado):
        s, k = _caso(analyst_user, f'CHN-2026-10-23-01{len(estado):02d}', media, status=estado)
        _crom(k)
        with pytest.raises(CaseLockedError):
            completar_contornos(s)
        assert ml == []

    def test_sin_metafase_lo_dice(self, analyst_user, media, ml):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0006', media, imagen=False)
        _crom(k)
        with pytest.raises(SinMetafaseError):
            completar_contornos(s)

    def test_sin_backend_ml_no_cambia_nada(self, analyst_user, media, monkeypatch):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0007', media)
        c = _crom(k)

        def caido(*a, **kw):
            raise MLDegradedError('caído')

        monkeypatch.setattr('apps.samples.services.pipeline_client.contours', caido)
        with pytest.raises(MLDegradedError):
            completar_contornos(s)
        c.refresh_from_db()
        assert c.contour is None

    def test_sin_cariotipo_devuelve_cero(self, analyst_user, ml):
        s = Sample.objects.create(chn_code='CHN-2026-10-23-0008', patient_ref='ANON',
                                  analyst=analyst_user, status='READY')
        assert completar_contornos(s) == 0


# ============================================================================
# Invalidación: la silueta era la del objeto de antes
# ============================================================================
class TestInvalidacion:
    def test_recortar_deja_el_contorno_a_none(self, analyst_user, media, monkeypatch):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0009', media)
        c = _crom(k, contour=CONTORNO)
        monkeypatch.setattr('apps.samples.services.pipeline_client.classify_crop',
                            lambda *a, **kw: {'predicted_class': '3', 'confidence_score': 0.6})
        recrop_chromosome(s, c, {'x': 12, 'y': 22, 'w': 20, 'h': 60}, analyst_user)
        c.refresh_from_db()
        assert c.contour is None

    def test_separar_deja_el_contorno_a_none(self, analyst_user, media):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0010', media)
        c = _crom(k, contour=CONTORNO)
        nuevo = split_chromosome(s, c, analyst_user)
        c.refresh_from_db()
        assert c.contour is None
        assert nuevo.contour is None

    def test_unir_deja_el_contorno_a_none(self, analyst_user, media):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0011', media)
        a = _crom(k, contour=CONTORNO, order=0)
        b = _crom(k, contour=CONTORNO, order=1, bbox={'x': 40, 'y': 20, 'w': 30, 'h': 90})
        join_chromosomes(s, a, b, analyst_user)
        a.refresh_from_db()
        assert a.contour is None


# ============================================================================
# Vista
# ============================================================================
def _url(sample):
    return f'/api/clinic/samples/{sample.id}/karyotype/contours/'


@pytest.fixture
def otro_analista(django_user_model):
    return django_user_model.objects.create_user(username='otra_analista_contornos', password='x')


class TestKaryotypeContoursView:
    def test_el_dueno_completa_y_el_cariotipo_los_sirve(self, analyst_client, analyst_user, media, ml):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0012', media)
        _crom(k)
        resp = analyst_client.post(_url(s))
        assert resp.status_code == 200
        assert resp.data == {'completados': 1}
        cariotipo = analyst_client.get(f'/api/clinic/samples/{s.id}/karyotype/')
        assert cariotipo.data['chromosomes'][0]['contour'] == CONTORNO

    def test_un_analista_no_completa_el_caso_de_otro(self, analyst_client, otro_analista, media, ml):
        s, k = _caso(otro_analista, 'CHN-2026-10-23-0013', media)
        _crom(k)
        resp = analyst_client.post(_url(s))
        assert resp.status_code == 403
        assert resp.data['code'] == 'NOT_OWNER'
        assert ml == []

    def test_sin_sesion_401(self, api_client, analyst_user, media):
        s, _ = _caso(analyst_user, 'CHN-2026-10-23-0014', media)
        assert api_client.post(_url(s)).status_code == 401

    def test_sin_cariotipo_404(self, analyst_client, analyst_user):
        s = Sample.objects.create(chn_code='CHN-2026-10-23-0015', patient_ref='ANON',
                                  analyst=analyst_user, status='READY')
        resp = analyst_client.post(_url(s))
        assert resp.status_code == 404
        assert resp.data['code'] == 'NO_KARYOTYPE'

    def test_sin_metafase_404(self, analyst_client, analyst_user, media, ml):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0016', media, imagen=False)
        _crom(k)
        resp = analyst_client.post(_url(s))
        assert resp.status_code == 404
        assert resp.data['code'] == 'NO_METAPHASE_IMAGE'

    def test_caso_validado_409(self, analyst_client, analyst_user, media, ml):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0017', media, status='ANALYST_VALIDATED')
        _crom(k)
        resp = analyst_client.post(_url(s))
        assert resp.status_code == 409
        assert resp.data['code'] == 'CASE_LOCKED'

    def test_sin_backend_ml_503(self, analyst_client, analyst_user, media, monkeypatch):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0018', media)
        _crom(k)

        def caido(*a, **kw):
            raise MLDegradedError('caído')

        monkeypatch.setattr('apps.samples.services.pipeline_client.contours', caido)
        resp = analyst_client.post(_url(s))
        assert resp.status_code == 503
        assert resp.data['code'] == 'ML_UNAVAILABLE'

    def test_el_contorno_no_se_escribe_por_el_serializador(self, analyst_user, media):
        from apps.samples.serializers import ChromosomeSerializer
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0019', media)
        c = _crom(k)
        ser = ChromosomeSerializer(c, data={'contour': CONTORNO}, partial=True)
        assert ser.is_valid()
        ser.save()
        c.refresh_from_db()
        assert c.contour is None


# ============================================================================
# Cliente HTTP
# ============================================================================
class _Resp:
    def __init__(self, cuerpo, status=200):
        self._cuerpo, self.status_code = cuerpo, status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError('error', request=None, response=None)

    def json(self):
        return self._cuerpo


class _Cliente:
    def __init__(self, resp):
        self.resp, self.enviado = resp, None

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def post(self, url, files=None, data=None):
        self.enviado = {'url': url, 'data': data}
        return self.resp


def _cliente_con(monkeypatch, resp):
    falso = _Cliente(resp)
    monkeypatch.setattr('apps.samples.pipeline_client.httpx.Client', lambda timeout=None: falso)
    return PipelineClient('http://ml', timeout=2, threshold=3, cooldown=30), falso


class TestPipelineClientContours:
    def test_envia_las_cajas_y_devuelve_los_contornos(self, monkeypatch):
        cliente, falso = _cliente_con(monkeypatch, _Resp({'contornos': [CONTORNO, None]}))
        r = cliente.contours(b'img', [{'x': 1, 'y': 2, 'w': 3, 'h': 4}, {'x': 5, 'y': 6, 'w': 7, 'h': 8}])
        assert r == [CONTORNO, None]
        assert falso.enviado['url'] == 'http://ml/api/v1/contours/'
        assert '"x": 1' in falso.enviado['data']['bboxes']

    def test_una_respuesta_que_no_casa_caja_a_caja_se_rechaza(self, monkeypatch):
        cliente, _ = _cliente_con(monkeypatch, _Resp({'contornos': [CONTORNO]}))
        with pytest.raises(MLDegradedError):
            cliente.contours(b'img', [{'x': 1, 'y': 2, 'w': 3, 'h': 4}, {'x': 5, 'y': 6, 'w': 7, 'h': 8}])

    def test_error_http_es_degradacion(self, monkeypatch):
        cliente, _ = _cliente_con(monkeypatch, _Resp({}, status=500))
        with pytest.raises(MLDegradedError):
            cliente.contours(b'img', [{'x': 1, 'y': 2, 'w': 3, 'h': 4}])

    def test_circuito_abierto_no_llama(self, monkeypatch):
        cliente, falso = _cliente_con(monkeypatch, _Resp({'contornos': []}))
        cliente._circuit_open_until = 10 ** 12
        with pytest.raises(MLDegradedError):
            cliente.contours(b'img', [])
        assert falso.enviado is None
