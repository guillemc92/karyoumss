"""Separar por línea y unir por máscara (DD-KARYO-007 D3 y D4, T5).

Se fija:

- separar exige una línea (sin ella, 400: ya no hay corte por la mitad);
- el original se queda con el trozo MAYOR y cada trozo restante es un cromosoma
  nuevo, con la silueta y la caja que devolvió el corte;
- cada trozo se reclasifica; si la IA no responde a eso, conserva la clase de
  origen en naranja y pendiente (RN-07);
- el evento SPLIT guarda la línea y el estado previo (lo que necesita deshacer);
- sin backend-ml no se separa (503) y una línea que no corta es 422; en los
  dos casos no cambia nada;
- unir pide la silueta de la unión; sin IA une las cajas igual.

backend-ml se sustituye por un doble: aquí se prueba la lógica clínica. El corte
en ráster de verdad se prueba en backend-ml/tests/test_edicion.py.
"""
import json
from decimal import Decimal

import httpx
import pytest

from apps.samples.models import (
    AuditEvent, AuditEventType, Chromosome, Karyotype, Sample, SampleImage, SampleImageSource,
)
from apps.samples.pipeline_client import CorteInvalidoError, MLDegradedError, PipelineClient
from apps.samples.services import (
    CaseLockedError, ObjetoInactivoError, SinMetafaseError, join_chromosomes, split_chromosome,
)

pytestmark = pytest.mark.django_db

ORIGINAL = [[10, 20], [40, 20], [40, 110], [10, 110]]
TROZO_MAYOR = {'contour': [[10, 20], [40, 20], [40, 70], [10, 70]], 'bbox': {'x': 10, 'y': 20, 'w': 30, 'h': 50}, 'area': 1500}
TROZO_MENOR = {'contour': [[10, 74], [40, 74], [40, 110], [10, 110]], 'bbox': {'x': 10, 'y': 74, 'w': 30, 'h': 36}, 'area': 1080}
LINEA = [[0, 72], [50, 72]]


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


def _crom(k, cls='1', order=0, activo=True, contour=ORIGINAL):
    return Chromosome.objects.create(
        karyotype=k, predicted_class=cls, position_index=0, order=order,
        confidence_score=Decimal('0.950'), is_active=activo, xai_viewed=True,
        resolution_status='RESOLVED',
        bbox={'x': 10, 'y': 20, 'w': 30, 'h': 90}, contour=contour,
    )


def _caida(*a, **kw):
    raise MLDegradedError('circuit_open')


@pytest.fixture
def ml(monkeypatch):
    """Doble de backend-ml: corta en dos trozos y clasifica cada uno."""
    llamadas = {'split': [], 'classify': [], 'join': []}

    def cortar(image_bytes, bbox, contour, linea, filename=''):
        llamadas['split'].append({'bbox': bbox, 'contour': contour, 'linea': linea})
        return [TROZO_MAYOR, TROZO_MENOR]

    clases = iter([('3', 0.91), ('18', 0.42)])

    def clasificar(image_bytes, bbox, filename=''):
        llamadas['classify'].append(bbox)
        clase, conf = next(clases)
        return {'predicted_class': clase, 'confidence_score': conf}

    def unir(contornos):
        llamadas['join'].append(contornos)
        return {'contour': ORIGINAL, 'bbox': {'x': 10, 'y': 20, 'w': 30, 'h': 90}}

    monkeypatch.setattr('apps.samples.services.pipeline_client.split', cortar)
    monkeypatch.setattr('apps.samples.services.pipeline_client.classify_crop', clasificar)
    monkeypatch.setattr('apps.samples.services.pipeline_client.join', unir)
    return llamadas


# ============================================================================
# Separar
# ============================================================================
class TestSeparar:
    def test_el_original_se_queda_con_el_trozo_mayor(self, analyst_user, media, ml):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0201', media)
        c = _crom(k)
        origen, nuevo = split_chromosome(s, c, LINEA, analyst_user)
        c.refresh_from_db()
        assert origen.id == c.id
        assert c.bbox == TROZO_MAYOR['bbox'] and c.contour == TROZO_MAYOR['contour']
        assert nuevo.bbox == TROZO_MENOR['bbox'] and nuevo.contour == TROZO_MENOR['contour']
        assert k.chromosomes.filter(is_active=True).count() == 2
        # Lo que se le pasó a backend-ml: la silueta del objeto y la línea.
        assert ml['split'] == [{'bbox': {'x': 10, 'y': 20, 'w': 30, 'h': 90}, 'contour': ORIGINAL,
                                'linea': [[0.0, 72.0], [50.0, 72.0]]}]

    def test_cada_trozo_se_reclasifica(self, analyst_user, media, ml):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0202', media)
        c = _crom(k)
        origen, nuevo = split_chromosome(s, c, LINEA, analyst_user)
        assert ml['classify'] == [TROZO_MAYOR['bbox'], TROZO_MENOR['bbox']]
        assert (origen.predicted_class, origen.semaphore, origen.resolution_status) == ('3', 'green', 'AUTO')
        assert (nuevo.predicted_class, nuevo.semaphore, nuevo.resolution_status) == ('18', 'orange', 'PENDING')
        # La decisión de antes miraba otro objeto: se vuelve a revisar.
        assert origen.xai_viewed is False

    def test_el_evento_guarda_la_linea_y_el_estado_previo(self, analyst_user, media, ml):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0203', media)
        c = _crom(k)
        _, nuevo = split_chromosome(s, c, LINEA, analyst_user)
        ev = AuditEvent.objects.get(sample=s, event_type=AuditEventType.SPLIT)
        assert ev.payload['linea'] == [[0.0, 72.0], [50.0, 72.0]]
        assert ev.payload['created'] == [str(nuevo.id)]
        assert ev.payload['previo'] == {
            'bbox': {'x': 10, 'y': 20, 'w': 30, 'h': 90}, 'contour': ORIGINAL,
            'predicted_class': '1', 'confidence_score': '0.950',
            'resolution_status': 'RESOLVED', 'xai_viewed': True,
        }
        assert [t['clase'] for t in ev.payload['trozos']] == ['3', '18']
        assert ev.payload['reclasificado'] is True

    def test_sin_ia_para_clasificar_los_trozos_quedan_en_naranja(self, analyst_user, media, ml, monkeypatch):
        monkeypatch.setattr('apps.samples.services.pipeline_client.classify_crop', _caida)
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0204', media)
        origen, nuevo = split_chromosome(s, _crom(k, cls='7'), LINEA, analyst_user)
        for t in (origen, nuevo):
            assert t.predicted_class == '7'          # la de origen
            assert t.semaphore == 'orange'
            assert t.resolution_status == 'PENDING'  # RN-01: hay que revisarlos
        assert AuditEvent.objects.get(sample=s, event_type='SPLIT').payload['reclasificado'] is False

    def test_una_clase_invalida_del_modelo_cuenta_como_sin_clasificar(self, analyst_user, media, ml, monkeypatch):
        monkeypatch.setattr('apps.samples.services.pipeline_client.classify_crop',
                            lambda *a, **kw: {'predicted_class': '99', 'confidence_score': 0.99})
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0205', media)
        origen, _ = split_chromosome(s, _crom(k, cls='7'), LINEA, analyst_user)
        assert origen.predicted_class == '7' and origen.semaphore == 'orange'

    def test_tres_trozos_crean_dos_cromosomas(self, analyst_user, media, ml, monkeypatch):
        tercero = {'contour': [[50, 20], [60, 20], [60, 40]], 'bbox': {'x': 50, 'y': 20, 'w': 10, 'h': 20}, 'area': 90}
        monkeypatch.setattr('apps.samples.services.pipeline_client.split',
                            lambda *a, **kw: [TROZO_MAYOR, TROZO_MENOR, tercero])
        monkeypatch.setattr('apps.samples.services.pipeline_client.classify_crop',
                            lambda *a, **kw: {'predicted_class': '21', 'confidence_score': 0.9})
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0206', media)
        resultado = split_chromosome(s, _crom(k), LINEA, analyst_user)
        assert len(resultado) == 3
        assert sorted(c.position_index for c in resultado) == [0, 1, 2]   # tres «21» seguidos
        assert len({c.order for c in resultado[1:]}) == 2

    @pytest.mark.parametrize('linea', [None, [], [[1, 2]], 'x', [[1, 2], [3]], [[1, 2], ['a', 3]], [[True, 1], [2, 3]]])
    def test_linea_invalida(self, analyst_user, media, ml, linea):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0207', media)
        with pytest.raises(ValueError):
            split_chromosome(s, _crom(k), linea, analyst_user)
        assert ml['split'] == []

    def test_sin_backend_ml_no_cambia_nada(self, analyst_user, media, monkeypatch):
        monkeypatch.setattr('apps.samples.services.pipeline_client.split', _caida)
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0208', media)
        c = _crom(k)
        with pytest.raises(MLDegradedError):
            split_chromosome(s, c, LINEA, analyst_user)
        c.refresh_from_db()
        assert c.contour == ORIGINAL and k.chromosomes.count() == 1
        assert AuditEvent.objects.filter(sample=s).count() == 0

    def test_una_linea_que_no_corta_no_cambia_nada(self, analyst_user, media, monkeypatch):
        def no_corta(*a, **kw):
            raise CorteInvalidoError('la línea no separa el objeto')
        monkeypatch.setattr('apps.samples.services.pipeline_client.split', no_corta)
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0209', media)
        with pytest.raises(CorteInvalidoError):
            split_chromosome(s, _crom(k), LINEA, analyst_user)
        assert k.chromosomes.count() == 1
        assert AuditEvent.objects.filter(sample=s).count() == 0

    def test_sin_metafase(self, analyst_user, media, ml):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0210', media, imagen=False)
        with pytest.raises(SinMetafaseError):
            split_chromosome(s, _crom(k), LINEA, analyst_user)

    def test_objeto_descartado(self, analyst_user, media, ml):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0211', media)
        with pytest.raises(ObjetoInactivoError):
            split_chromosome(s, _crom(k, activo=False), LINEA, analyst_user)

    def test_caso_validado(self, analyst_user, media, ml):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0212', media, status='ANALYST_VALIDATED')
        with pytest.raises(CaseLockedError):
            split_chromosome(s, _crom(k), LINEA, analyst_user)
        assert ml['split'] == []


# ============================================================================
# Unir
# ============================================================================
class TestUnir:
    def test_une_las_siluetas(self, analyst_user, media, ml):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0221', media)
        a = _crom(k, contour=TROZO_MAYOR['contour'])
        b = _crom(k, order=1, contour=TROZO_MENOR['contour'])
        join_chromosomes(s, a, b, analyst_user)
        a.refresh_from_db()
        assert ml['join'] == [[TROZO_MAYOR['contour'], TROZO_MENOR['contour']]]
        assert a.contour == ORIGINAL and a.bbox == {'x': 10, 'y': 20, 'w': 30, 'h': 90}
        ev = AuditEvent.objects.get(sample=s, event_type='JOIN')
        assert ev.payload['por_mascara'] is True
        assert ev.payload['previo'] == {'bbox': {'x': 10, 'y': 20, 'w': 30, 'h': 90},
                                        'contour': TROZO_MAYOR['contour']}

    def test_sin_las_dos_siluetas_une_las_cajas(self, analyst_user, media, ml):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0222', media)
        a = _crom(k, contour=None)
        b = _crom(k, order=1)
        join_chromosomes(s, a, b, analyst_user)
        a.refresh_from_db()
        assert ml['join'] == []
        assert a.contour is None
        assert AuditEvent.objects.get(sample=s, event_type='JOIN').payload['por_mascara'] is False


# ============================================================================
# Vista
# ============================================================================
def _url(s, c):
    return f'/api/clinic/samples/{s.id}/chromosomes/{c.id}/split/'


@pytest.fixture
def otro_analista(django_user_model):
    return django_user_model.objects.create_user(username='otra_analista_corte', password='x')


class TestVistaSeparar:
    def test_201_con_origen_y_creados(self, analyst_client, analyst_user, media, ml):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0231', media)
        c = _crom(k)
        r = analyst_client.post(_url(s, c), {'linea': LINEA}, format='json')
        assert r.status_code == 201
        assert r.data['origen']['id'] == str(c.id)
        assert [x['predicted_class'] for x in r.data['creados']] == ['18']
        cariotipo = analyst_client.get(f'/api/clinic/samples/{s.id}/karyotype/').data
        assert cariotipo['summary']['total'] == 2

    @pytest.mark.parametrize('falla, http, codigo', [
        (MLDegradedError('circuit_open'), 503, 'ML_UNAVAILABLE'),
        (CorteInvalidoError('la línea no separa el objeto'), 422, 'INVALID_CUT'),
    ])
    def test_fallos_del_corte(self, analyst_client, analyst_user, media, monkeypatch, falla, http, codigo):
        def lanza(*a, **kw):
            raise falla
        monkeypatch.setattr('apps.samples.services.pipeline_client.split', lanza)
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0232', media)
        r = analyst_client.post(_url(s, _crom(k)), {'linea': LINEA}, format='json')
        assert r.status_code == http
        assert r.data['code'] == codigo

    def test_sin_metafase_404(self, analyst_client, analyst_user, media, ml):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0233', media, imagen=False)
        r = analyst_client.post(_url(s, _crom(k)), {'linea': LINEA}, format='json')
        assert r.status_code == 404
        assert r.data['code'] == 'NO_METAPHASE_IMAGE'

    def test_descartado_409(self, analyst_client, analyst_user, media, ml):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0234', media)
        r = analyst_client.post(_url(s, _crom(k, activo=False)), {'linea': LINEA}, format='json')
        assert r.status_code == 409
        assert r.data['code'] == 'OBJECT_INACTIVE'

    def test_linea_mal_formada_400(self, analyst_client, analyst_user, media, ml):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0235', media)
        r = analyst_client.post(_url(s, _crom(k)), {'linea': [[1, 2]]}, format='json')
        assert r.status_code == 400

    def test_analista_ajeno_403(self, analyst_client, otro_analista, media, ml):
        s, k = _caso(otro_analista, 'CHN-2026-10-23-0236', media)
        r = analyst_client.post(_url(s, _crom(k)), {'linea': LINEA}, format='json')
        assert r.status_code == 403
        assert ml['split'] == []


# ============================================================================
# Cliente (httpx falso)
# ============================================================================
class _Resp:
    def __init__(self, status, cuerpo):
        self.status_code = status
        self._cuerpo = cuerpo

    def json(self):
        return self._cuerpo

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError('error', request=None, response=None)


def _cliente_falso(monkeypatch, respuesta=None, excepcion=None, enviado=None):
    class Falso:
        def __init__(self, *a, **kw):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, url, **kw):
            if enviado is not None:
                enviado.append((url, kw))
            if excepcion:
                raise excepcion
            return respuesta
    monkeypatch.setattr('apps.samples.pipeline_client.httpx.Client', Falso)


def _pc():
    return PipelineClient(base_url='http://ml', timeout=1, threshold=3, cooldown=60)


class TestCliente:
    def test_split_envia_caja_linea_y_silueta(self, monkeypatch):
        enviado = []
        _cliente_falso(monkeypatch, _Resp(200, {'trozos': [TROZO_MAYOR, TROZO_MENOR]}), enviado=enviado)
        trozos = _pc().split(b'img', {'x': 1, 'y': 2, 'w': 3, 'h': 4}, ORIGINAL, LINEA)
        assert trozos == [TROZO_MAYOR, TROZO_MENOR]
        url, kw = enviado[0]
        assert url == 'http://ml/api/v1/split/'
        assert json.loads(kw['data']['linea']) == LINEA
        assert json.loads(kw['data']['contour']) == ORIGINAL

    def test_split_sin_silueta_no_la_envia(self, monkeypatch):
        enviado = []
        _cliente_falso(monkeypatch, _Resp(200, {'trozos': [TROZO_MAYOR, TROZO_MENOR]}), enviado=enviado)
        _pc().split(b'img', {'x': 1, 'y': 2, 'w': 3, 'h': 4}, None, LINEA)
        assert 'contour' not in enviado[0][1]['data']

    def test_split_422_es_culpa_del_trazo_y_no_abre_el_circuito(self, monkeypatch):
        _cliente_falso(monkeypatch, _Resp(422, {'detail': 'la línea no separa el objeto'}))
        pc = _pc()
        for _ in range(5):
            with pytest.raises(CorteInvalidoError, match='no separa'):
                pc.split(b'img', {}, None, LINEA)
        assert pc._circuit_open() is False

    def test_split_caida_abre_el_circuito(self, monkeypatch):
        _cliente_falso(monkeypatch, excepcion=httpx.ConnectError('caído'))
        pc = _pc()
        for _ in range(3):
            with pytest.raises(MLDegradedError):
                pc.split(b'img', {}, None, LINEA)
        with pytest.raises(MLDegradedError, match='circuit_open'):
            pc.split(b'img', {}, None, LINEA)

    def test_split_respuesta_sin_trozos(self, monkeypatch):
        _cliente_falso(monkeypatch, _Resp(200, {'trozos': [TROZO_MAYOR]}))
        with pytest.raises(MLDegradedError):
            _pc().split(b'img', {}, None, LINEA)

    def test_join(self, monkeypatch):
        _cliente_falso(monkeypatch, _Resp(200, {'contour': ORIGINAL, 'bbox': {'x': 1, 'y': 1, 'w': 1, 'h': 1}}))
        assert _pc().join([ORIGINAL, ORIGINAL])['contour'] == ORIGINAL

    def test_join_incompleto_o_caido(self, monkeypatch):
        _cliente_falso(monkeypatch, _Resp(200, {'contour': ORIGINAL}))
        with pytest.raises(MLDegradedError):
            _pc().join([ORIGINAL, ORIGINAL])
        _cliente_falso(monkeypatch, excepcion=httpx.ConnectError('caído'))
        with pytest.raises(MLDegradedError):
            _pc().join([ORIGINAL, ORIGINAL])

    def test_join_circuito_abierto(self, monkeypatch):
        pc = _pc()
        monkeypatch.setattr(pc, '_circuit_open', lambda: True)
        with pytest.raises(MLDegradedError):
            pc.join([ORIGINAL, ORIGINAL])
