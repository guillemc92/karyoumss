"""DD-OBS-001 D8: «motor ocupado» no es «motor caído».

backend-ml atiende una inferencia por vez. A quien espera turno más de
`ML_ESPERA_MAX_S` le responde 503 con `Retry-After`. Antes ese 503 se trataba
igual que una caída: contaba para el circuit breaker y el analista veía
«pipeline de IA no disponible». Aquí se fija lo contrario.
"""
from pathlib import Path

import httpx
import pytest
from django.conf import settings
from django.urls import reverse

from apps.samples.models import Sample, SampleImage, SampleStatus
from apps.samples.pipeline_client import (
    REINTENTO_MAX_S, MLBusyError, MLDegradedError, PipelineClient, _reintento, pipeline_client,
)

IMAGEN = b'\xff\xd8-bytes-de-una-metafase'
BBOX = {'x': 1, 'y': 2, 'w': 30, 'h': 40}


def _error_http(estado: int, cabeceras: dict | None = None) -> httpx.HTTPStatusError:
    peticion = httpx.Request('POST', 'http://ml:8001/api/v1/segment/')
    respuesta = httpx.Response(estado, headers=cabeceras or {}, request=peticion)
    return httpx.HTTPStatusError(f'{estado}', request=peticion, response=respuesta)


class _Red:
    """Doble de `httpx.Client`: cada `post` lanza lo que se le haya dicho."""

    def __init__(self, lanza):
        self.lanza = lanza
        self.llamadas = 0

    def __call__(self, **kwargs):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def post(self, *a, **kw):
        self.llamadas += 1
        raise self.lanza


def _cliente(**cambios) -> PipelineClient:
    valores = dict(base_url='http://ml:8001', timeout=0.2, threshold=2, cooldown=60)
    valores.update(cambios)
    return PipelineClient(**valores)


def _invocar(cliente: PipelineClient, metodo: str):
    if metodo == 'segment_image':
        return cliente.segment_image(IMAGEN)
    return getattr(cliente, metodo)(IMAGEN, BBOX)


# --- qué 503 es «sin turno» ---------------------------------------------------

class TestReintento:
    def test_503_con_retry_after_da_los_segundos(self):
        assert _reintento(_error_http(503, {'Retry-After': '25'})) == 25

    def test_503_sin_cabecera_no_es_ocupado(self):
        # Modelo sin cargar o clasificador sin resultado: 503 sin Retry-After.
        assert _reintento(_error_http(503)) is None

    @pytest.mark.parametrize('estado', [500, 502, 504, 429])
    def test_otro_estado_con_cabecera_no_es_ocupado(self, estado):
        assert _reintento(_error_http(estado, {'Retry-After': '25'})) is None

    def test_cabecera_con_fecha_no_es_ocupado(self):
        # Retry-After admite una fecha HTTP; backend-ml manda segundos. Lo que
        # no se entiende no se adivina: se trata como una caída.
        assert _reintento(_error_http(503, {'Retry-After': 'Fri, 13 Nov 2026 19:00:00 GMT'})) is None

    @pytest.mark.parametrize('valor,esperado', [('0', 1), ('-5', 1), ('99999', REINTENTO_MAX_S)])
    def test_los_segundos_se_acotan(self, valor, esperado):
        assert _reintento(_error_http(503, {'Retry-After': valor})) == esperado

    def test_un_timeout_no_es_ocupado(self):
        assert _reintento(httpx.TimeoutException('lento')) is None


# --- el cliente ---------------------------------------------------------------

METODOS = ['segment_image', 'xai_heatmap', 'classify_crop']


@pytest.mark.parametrize('metodo', METODOS)
def test_sin_turno_es_mlbusyerror_con_sus_segundos(monkeypatch, metodo):
    monkeypatch.setattr(httpx, 'Client', _Red(_error_http(503, {'Retry-After': '25'})))
    with pytest.raises(MLBusyError) as info:
        _invocar(_cliente(), metodo)
    assert info.value.retry_after == 25


def test_mlbusyerror_sigue_siendo_degradado_para_quien_no_lo_distingue():
    # Las vistas que solo capturan MLDegradedError no cambian de comportamiento.
    assert issubclass(MLBusyError, MLDegradedError)


def test_sin_turno_no_abre_el_circuito(monkeypatch):
    cliente = _cliente(threshold=2)
    red = _Red(_error_http(503, {'Retry-After': '25'}))
    monkeypatch.setattr(httpx, 'Client', red)
    for _ in range(5):
        with pytest.raises(MLBusyError):
            cliente.segment_image(IMAGEN)
    # Cinco «ocupado» seguidos, con el umbral en 2: el circuito sigue cerrado y
    # la sexta llamada sale a la red.
    assert not cliente._circuit_open()
    assert red.llamadas == 5


def test_sin_turno_borra_los_fallos_anteriores(monkeypatch):
    # El motor contestó: está vivo. Un fallo previo no debe sumarse a otro
    # posterior para abrir el circuito con un «ocupado» en medio.
    cliente = _cliente(threshold=2)
    monkeypatch.setattr(httpx, 'Client', _Red(httpx.ConnectError('caído')))
    with pytest.raises(MLDegradedError):
        cliente.segment_image(IMAGEN)
    monkeypatch.setattr(httpx, 'Client', _Red(_error_http(503, {'Retry-After': '25'})))
    with pytest.raises(MLBusyError):
        cliente.segment_image(IMAGEN)
    monkeypatch.setattr(httpx, 'Client', _Red(httpx.ConnectError('caído')))
    with pytest.raises(MLDegradedError):
        cliente.segment_image(IMAGEN)
    assert not cliente._circuit_open()


def test_una_caida_de_verdad_sigue_abriendo_el_circuito(monkeypatch):
    cliente = _cliente(threshold=2)
    monkeypatch.setattr(httpx, 'Client', _Red(_error_http(503)))
    for _ in range(2):
        with pytest.raises(MLDegradedError) as info:
            cliente.segment_image(IMAGEN)
        assert not isinstance(info.value, MLBusyError)
    assert cliente._circuit_open()


# --- la vista -----------------------------------------------------------------

@pytest.fixture
def muestra(analyst_user):
    sample = Sample.objects.create(
        chn_code='CHN-2026-11-13-0001', patient_ref='ANON-OCUPADO', analyst=analyst_user,
        status=SampleStatus.PENDING_AI,
    )
    rel = f'{sample.chn_code}/img0.img'
    ruta = Path(settings.MEDIA_ROOT) / rel
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_bytes(IMAGEN)
    SampleImage.objects.create(sample=sample, image_path=rel, order=0, source='upload')
    return sample


@pytest.fixture(autouse=True)
def _circuito_limpio():
    pipeline_client._failures = 0
    pipeline_client._circuit_open_until = 0.0
    yield
    pipeline_client._failures = 0
    pipeline_client._circuit_open_until = 0.0


def _url(sample) -> str:
    return reverse('samples:sample-process', kwargs={'pk': sample.pk})


@pytest.mark.django_db
class TestProcesarConElMotorOcupado:
    def _ocupar(self, monkeypatch, segundos=25):
        def ocupado(*a, **kw):
            raise MLBusyError(segundos)
        monkeypatch.setattr(pipeline_client, 'segment_image', ocupado)

    def test_responde_503_ml_busy_con_los_segundos(self, analyst_client, muestra, monkeypatch):
        self._ocupar(monkeypatch, 25)
        resp = analyst_client.post(_url(muestra), {}, format='json')
        assert resp.status_code == 503
        assert resp.data['code'] == 'ML_BUSY'
        assert resp.data['retry_after_seconds'] == 25
        assert resp['Retry-After'] == '25'

    def test_el_mensaje_no_manda_al_modo_manual(self, analyst_client, muestra, monkeypatch):
        self._ocupar(monkeypatch)
        detalle = analyst_client.post(_url(muestra), {}, format='json').data['detail']
        assert 'otro caso' in detalle
        assert 'manual' not in detalle.lower()

    def test_la_muestra_no_cambia(self, analyst_client, muestra, monkeypatch):
        self._ocupar(monkeypatch)
        analyst_client.post(_url(muestra), {}, format='json')
        muestra.refresh_from_db()
        assert muestra.status == SampleStatus.PENDING_AI
        assert not hasattr(muestra, 'karyotype') or muestra.karyotype is None

    def test_la_caida_sigue_siendo_ml_degraded(self, analyst_client, muestra, monkeypatch):
        def caido(*a, **kw):
            raise MLDegradedError('connect error')
        monkeypatch.setattr(pipeline_client, 'segment_image', caido)
        resp = analyst_client.post(_url(muestra), {}, format='json')
        assert resp.status_code == 503
        assert resp.data['code'] == 'ML_DEGRADED'
        assert 'Retry-After' not in resp

    def test_de_punta_a_punta_con_el_503_de_backend_ml(self, analyst_client, muestra, monkeypatch):
        # Sin doblar `segment_image`: el 503 con Retry-After llega por la red
        # doblada y atraviesa cliente, servicio y vista.
        monkeypatch.setattr(httpx, 'Client', _Red(_error_http(503, {'Retry-After': '25'})))
        resp = analyst_client.post(_url(muestra), {}, format='json')
        assert resp.status_code == 503
        assert resp.data['code'] == 'ML_BUSY'
        assert resp.data['retry_after_seconds'] == 25
        assert not pipeline_client._circuit_open()
