"""DD-OBS-001 — trazas de backend-clinic. Los tramos se recogen en memoria:
ninguna prueba necesita Tempo."""
import builtins
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from apps.samples.pipeline_client import PipelineClient
from clinic_backend import observabilidad

from .conftest import auth_client

PII = 'ZZPEREZJUAN1234567'


@pytest.fixture(scope='module')
def _trazas_del_modulo():
    """Trazas encendidas mientras dura este archivo, y apagadas al salir: el
    resto de la suite no debe correr instrumentado."""
    observabilidad.apagar()
    memoria = InMemorySpanExporter()
    assert observabilidad.configurar('backend-clinic', SimpleSpanProcessor(memoria))
    yield memoria
    observabilidad.apagar()


@pytest.fixture
def tramos(_trazas_del_modulo):
    _trazas_del_modulo.clear()
    return _trazas_del_modulo


@pytest.fixture
def apagada(monkeypatch):
    """Como en un proceso recién arrancado sin la variable: sin proveedor."""
    monkeypatch.setattr(observabilidad, '_proveedor', None)
    monkeypatch.delenv(observabilidad.VARIABLE, raising=False)


class _Registro:
    def __init__(self):
        self.llamadas = []

    def instrument(self, **kw):
        self.llamadas.append(kw)


@pytest.fixture
def instrumentaciones(monkeypatch):
    """Sustituye los tres instrumentadores reales por registros de llamadas."""
    registros = [_Registro(), _Registro(), _Registro()]
    monkeypatch.setattr(observabilidad, '_instrumentadores', lambda: registros)
    return registros


@pytest.fixture
def conexion_trazada(tramos, db):
    """En producción la conexión nace después de encender las trazas y sale ya
    envuelta. En la suite ya está abierta (pytest-django), así que se envuelve
    aquí con el mismo instrumentador y se restaura al terminar."""
    from django.db import connection
    from opentelemetry.instrumentation.sqlite3 import SQLite3Instrumentor
    connection.ensure_connection()
    original = connection.connection
    connection.connection = SQLite3Instrumentor().instrument_connection(
        original, tracer_provider=observabilidad._proveedor)
    yield tramos
    connection.connection = original


def atributos(span) -> str:
    return span.name + ' ' + ' '.join(f'{k}={v}' for k, v in span.attributes.items())


# ---------- apagado por omisión (D2) ----------

def test_sin_la_variable_no_se_enciende(apagada, instrumentaciones):
    assert observabilidad.configurar('backend-clinic') is False
    assert observabilidad.activa() is False
    assert all(r.llamadas == [] for r in instrumentaciones)


def test_sin_el_paquete_instalado_no_falla(apagada, monkeypatch):
    """RN-07: si falta opentelemetry, el servicio arranca sin trazas."""
    monkeypatch.setenv(observabilidad.VARIABLE, 'http://tempo:4318')
    importar = builtins.__import__

    def sin_otel(nombre, *args, **kwargs):
        if nombre.startswith('opentelemetry'):
            raise ImportError(nombre)
        return importar(nombre, *args, **kwargs)

    monkeypatch.setattr(builtins, '__import__', sin_otel)
    assert observabilidad.configurar('backend-clinic') is False
    assert observabilidad.activa() is False


def test_con_la_variable_se_instrumentan_django_httpx_y_sqlite(apagada, instrumentaciones, monkeypatch):
    monkeypatch.setenv(observabilidad.VARIABLE, 'http://127.0.0.1:9')     # nadie escucha: no debe fallar
    monkeypatch.delenv('OTEL_PYTHON_DJANGO_EXCLUDED_URLS', raising=False)

    assert observabilidad.configurar('backend-clinic') is True

    assert observabilidad.activa() is True
    django, httpx, sqlite = instrumentaciones
    proveedor = django.llamadas[0]['tracer_provider']
    assert proveedor.resource.attributes['service.name'] == 'backend-clinic'
    assert django.llamadas[0]['request_hook'] is observabilidad._limpiar_url
    assert httpx.llamadas == [{'tracer_provider': proveedor}]
    # D4: a sqlite no se le pide capturar parámetros.
    assert sqlite.llamadas == [{'tracer_provider': proveedor}]
    import os
    assert os.environ['OTEL_PYTHON_DJANGO_EXCLUDED_URLS'] == 'admin/login'
    proveedor.shutdown()
    monkeypatch.delenv('OTEL_PYTHON_DJANGO_EXCLUDED_URLS')


def test_configurar_dos_veces_no_instrumenta_dos_veces(tramos, instrumentaciones):
    assert observabilidad.configurar('backend-clinic') is True
    assert all(r.llamadas == [] for r in instrumentaciones)


def test_apagar_sin_trazas_no_hace_nada(apagada):
    observabilidad.apagar()
    assert observabilidad.activa() is False


# ---------- limpiar la URL (D4) ----------

def test_sin_consulta():
    assert observabilidad.sin_consulta('/api/clinic/samples/?search=PEREZ') == '/api/clinic/samples/'
    assert observabilidad.sin_consulta('/api/clinic/samples/') == '/api/clinic/samples/'


class _Span:
    def __init__(self, atributos, grabando=True):
        self.attributes = dict(atributos)
        self._grabando = grabando

    def is_recording(self):
        return self._grabando

    def set_attribute(self, clave, valor):
        self.attributes[clave] = valor


def test_limpiar_url_quita_la_consulta_de_todos_los_atributos():
    span = _Span({'http.url': 'http://x/a?b=1', 'http.target': '/a?b=1', 'url.full': 'http://x/a?b=1',
                  'url.query': 'b=1', 'http.method': 'GET'})

    observabilidad._limpiar_url(span, request=None)

    assert span.attributes == {'http.url': 'http://x/a', 'http.target': '/a', 'url.full': 'http://x/a',
                               'url.query': '', 'http.method': 'GET'}


def test_limpiar_url_aguanta_un_tramo_que_no_graba():
    observabilidad._limpiar_url(None, request=None)
    span = _Span({'http.url': 'http://x/a?b=1'}, grabando=False)
    observabilidad._limpiar_url(span, request=None)
    assert span.attributes['http.url'] == 'http://x/a?b=1'


# ---------- la traza de una petición (D3 y D4) ----------

def test_una_peticion_deja_su_tramo_y_los_de_sql(conexion_trazada, analyst_user):
    tramos = conexion_trazada
    respuesta = auth_client(analyst_user).get('/api/clinic/samples/')
    assert respuesta.status_code == 200

    spans = tramos.get_finished_spans()
    peticion = next(s for s in spans if s.name.startswith('GET '))
    consultas = [s for s in spans if s.attributes.get('db.system') == 'sqlite']
    assert peticion.resource.attributes['service.name'] == 'backend-clinic'
    # Las consultas de los fixtures van fuera de la petición, en trazas propias.
    de_la_peticion = [s for s in consultas if s.context.trace_id == peticion.context.trace_id]
    assert de_la_peticion, 'la petición debería dejar al menos un tramo de SQL dentro de su traza'


def test_la_traza_no_guarda_la_consulta_de_la_url_ni_los_parametros_de_sql(conexion_trazada, analyst_user):
    """El texto de búsqueda viaja en la URL y acaba como parámetro de SQL: no
    debe quedar en ningún tramo."""
    respuesta = auth_client(analyst_user).get(f'/api/clinic/samples/?search={PII}&chn_code={PII}')
    assert respuesta.status_code == 200

    spans = conexion_trazada.get_finished_spans()
    assert any(s.attributes.get('db.system') == 'sqlite' for s in spans)
    for span in spans:
        assert PII not in atributos(span)


@pytest.mark.django_db
def test_la_traza_no_guarda_el_token(tramos, analyst_user):
    cliente = auth_client(analyst_user)
    token = cliente._credentials['HTTP_AUTHORIZATION'].split()[1]

    cliente.get('/api/clinic/samples/')

    for span in tramos.get_finished_spans():
        assert token not in atributos(span)


# ---------- la llamada a backend-ml lleva la traza (D3) ----------

class _Eco(BaseHTTPRequestHandler):
    cabeceras = []

    def do_POST(self):
        self.rfile.read(int(self.headers.get('Content-Length', 0)))
        _Eco.cabeceras.append(dict(self.headers))
        cuerpo = b'{"chromosomes": [], "model_version": "eco"}'
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def log_message(self, *args):
        pass


@pytest.fixture
def backend_ml_de_mentira():
    _Eco.cabeceras = []
    servidor = HTTPServer(('127.0.0.1', 0), _Eco)
    hilo = threading.Thread(target=servidor.serve_forever, daemon=True)
    hilo.start()
    yield f'http://127.0.0.1:{servidor.server_port}'
    servidor.shutdown()
    servidor.server_close()


def test_la_llamada_a_backend_ml_sale_con_traceparent(tramos, backend_ml_de_mentira):
    cliente = PipelineClient(backend_ml_de_mentira, timeout=5, threshold=3, cooldown=30)

    cliente.segment_image(b'bytes-de-una-imagen')

    (cabeceras,) = _Eco.cabeceras
    (llamada,) = [s for s in tramos.get_finished_spans() if s.name == 'POST']
    traza = format(llamada.context.trace_id, '032x')
    assert cabeceras['traceparent'].split('-')[1] == traza
