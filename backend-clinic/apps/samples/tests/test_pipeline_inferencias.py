"""Ocupación del motor de IA: `GET /api/clinic/pipeline/inferencias/` (FSD-UC-007)."""
import httpx
import pytest
from django.conf import settings

from apps.samples.pipeline_client import MLDegradedError, PipelineClient, pipeline_client

URL = '/api/clinic/pipeline/inferencias/'
ESTADO = {'maximo': 1, 'en_curso': 1, 'libres': 0, 'espera_max_s': 25.0, 'en_espera': 2}


class _Respuesta:
    def __init__(self, cuerpo, estado=200):
        self._cuerpo, self.status_code = cuerpo, estado

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError('error', request=None, response=None)

    def json(self):
        if isinstance(self._cuerpo, Exception):
            raise self._cuerpo
        return self._cuerpo


class _Http:
    """Sustituto de `httpx.Client`: guarda lo que se le pide y responde lo dado."""

    def __init__(self, respuesta):
        self.respuesta, self.peticiones = respuesta, []

    def __call__(self, **kw):
        self.timeout = kw.get('timeout')
        return self

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def get(self, url, **kw):
        self.peticiones.append((url, kw))
        if isinstance(self.respuesta, Exception):
            raise self.respuesta
        return self.respuesta


def cliente() -> PipelineClient:
    return PipelineClient('http://ml:8000', timeout=120, threshold=2, cooldown=30)


# ---------- el cliente ----------

def test_pide_el_estado_con_el_secreto_interno_y_un_plazo_corto(monkeypatch):
    http = _Http(_Respuesta({**ESTADO, 'de_mas': 'se descarta'}))
    monkeypatch.setattr(httpx, 'Client', http)

    estado = cliente().estado_inferencias('s3cr3to')

    assert estado == ESTADO
    (url, opciones), = http.peticiones
    assert url == 'http://ml:8000/api/v1/inferencias/'
    assert opciones['headers'] == {'X-Internal-Secret': 's3cr3to'}
    assert http.timeout == 3.0          # no los 120 s de una inferencia


@pytest.mark.parametrize('respuesta', [
    httpx.TimeoutException('timeout'),
    httpx.ConnectError('caído'),
    _Respuesta({'detail': 'Secreto de servicio inválido'}, estado=403),
    _Respuesta(ValueError('no es JSON')),
    _Respuesta({'maximo': 1}),              # faltan campos
    _Respuesta(['una', 'lista']),
])
def test_cualquier_fallo_es_degradacion(monkeypatch, respuesta):
    monkeypatch.setattr(httpx, 'Client', _Http(respuesta))
    with pytest.raises(MLDegradedError):
        cliente().estado_inferencias('s3cr3to')


def test_mirar_el_estado_no_abre_el_circuit_breaker(monkeypatch):
    """Si lo abriera, una pantalla de estado podría dejar al visor en modo manual."""
    monkeypatch.setattr(httpx, 'Client', _Http(httpx.ConnectError('caído')))
    c = cliente()
    for _ in range(5):                      # más que el umbral (2)
        with pytest.raises(MLDegradedError):
            c.estado_inferencias('s3cr3to')
    assert c._circuit_open() is False


# ---------- la vista ----------

@pytest.mark.django_db
def test_devuelve_la_ocupacion_y_si_esta_ocupado(analyst_client, monkeypatch):
    recibido = {}

    def estado(secreto):
        recibido['secreto'] = secreto
        return dict(ESTADO)

    monkeypatch.setattr(pipeline_client, 'estado_inferencias', estado)

    respuesta = analyst_client.get(URL)

    assert respuesta.status_code == 200
    assert respuesta.json() == {**ESTADO, 'ocupado': True}
    assert recibido['secreto'] == settings.INTERNAL_SERVICE_SECRET


@pytest.mark.django_db
def test_con_huecos_libres_no_esta_ocupado(analyst_client, monkeypatch):
    libre = {**ESTADO, 'en_curso': 0, 'libres': 1, 'en_espera': 0}
    monkeypatch.setattr(pipeline_client, 'estado_inferencias', lambda secreto: libre)

    assert analyst_client.get(URL).json()['ocupado'] is False


@pytest.mark.django_db
def test_si_el_motor_no_responde_es_503_y_no_filtra_el_motivo(analyst_client, monkeypatch):
    def caido(secreto):
        raise MLDegradedError('ConnectError: http://ml:8000 s3cr3to')

    monkeypatch.setattr(pipeline_client, 'estado_inferencias', caido)

    respuesta = analyst_client.get(URL)

    assert respuesta.status_code == 503
    assert respuesta.json() == {'code': 'ML_DEGRADED', 'detail': 'El motor de IA no responde.'}


@pytest.mark.django_db
def test_sin_sesion_no_se_ve(api_client):
    assert api_client.get(URL).status_code == 401


@pytest.mark.django_db
def test_la_respuesta_no_lleva_el_secreto(analyst_client, monkeypatch):
    monkeypatch.setattr(pipeline_client, 'estado_inferencias', lambda secreto: dict(ESTADO))
    assert settings.INTERNAL_SERVICE_SECRET not in analyst_client.get(URL).content.decode()
