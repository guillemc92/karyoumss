"""DD-OBS-001 — trazas de backend-ml. Los tramos se recogen en memoria: ninguna
prueba necesita Tempo."""
import builtins

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from app import observabilidad
from app.concurrencia import LimiteInferencias
from app.main import app

ETAPAS = ('esperar_turno', 'segmentar', 'clasificar')


#: La app se instrumenta una sola vez por proceso, así que las pruebas comparten
#: un recolector en memoria y lo vacían antes de usarlo.
MEMORIA = InMemorySpanExporter()


@pytest.fixture
def tramos():
    """Trazas encendidas, con el recolector vacío."""
    if not observabilidad.activa():
        assert observabilidad.configurar('backend-ml', app, SimpleSpanProcessor(MEMORIA))
    MEMORIA.clear()
    return MEMORIA


@pytest.fixture
def apagada(monkeypatch):
    """Como en un proceso recién arrancado sin la variable: sin proveedor."""
    monkeypatch.setattr(observabilidad, '_proveedor', None)
    monkeypatch.delenv(observabilidad.VARIABLE, raising=False)


@pytest.fixture
def instrumentaciones(monkeypatch):
    """Sustituye la instrumentación real por un registro de llamadas."""
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    llamadas = []
    monkeypatch.setattr(FastAPIInstrumentor, 'instrument_app',
                        staticmethod(lambda app, **kw: llamadas.append(kw)))
    return llamadas


def por_nombre(memoria) -> dict:
    return {s.name: s for s in memoria.get_finished_spans()}


def segmentar(png: bytes, **cabeceras):
    return TestClient(app).post('/api/v1/segment/', files={'file': ('m.png', png, 'image/png')},
                                headers=cabeceras)


# ---------- apagado por omisión (D2) ----------

def test_sin_la_variable_no_se_enciende(apagada, instrumentaciones):
    assert observabilidad.configurar('backend-ml', app) is False
    assert observabilidad.activa() is False
    assert instrumentaciones == []


def test_apagado_el_tramo_no_hace_nada_y_el_servicio_responde(apagada, synthetic_png_bytes):
    with observabilidad.tramo('lo-que-sea', n=1) as span:
        assert span is None
    assert segmentar(synthetic_png_bytes).status_code == 200


def test_sin_el_paquete_instalado_no_falla(apagada, instrumentaciones, monkeypatch):
    """RN-07: si falta opentelemetry, el servicio arranca sin trazas."""
    monkeypatch.setenv(observabilidad.VARIABLE, 'http://tempo:4318')
    importar = builtins.__import__

    def sin_otel(nombre, *args, **kwargs):
        if nombre.startswith('opentelemetry'):
            raise ImportError(nombre)
        return importar(nombre, *args, **kwargs)

    monkeypatch.setattr(builtins, '__import__', sin_otel)
    assert observabilidad.configurar('backend-ml', app) is False
    assert observabilidad.activa() is False


def test_con_la_variable_se_enciende_con_el_exportador_otlp(apagada, instrumentaciones, monkeypatch):
    monkeypatch.setenv(observabilidad.VARIABLE, 'http://127.0.0.1:9')     # nadie escucha: no debe fallar

    assert observabilidad.configurar('backend-ml', app) is True

    assert observabilidad.activa() is True
    (llamada,) = instrumentaciones
    proveedor = llamada['tracer_provider']
    assert proveedor.resource.attributes['service.name'] == 'backend-ml'
    assert llamada['excluded_urls'] == 'health'
    proveedor.shutdown()


def test_configurar_dos_veces_no_instrumenta_dos_veces(tramos, instrumentaciones, synthetic_png_bytes):
    assert observabilidad.configurar('backend-ml', app) is True
    assert instrumentaciones == []

    segmentar(synthetic_png_bytes)

    assert [s.name for s in tramos.get_finished_spans()].count('segmentar') == 1


# ---------- la traza de una inferencia (D3) ----------

def test_una_inferencia_deja_un_tramo_por_etapa(tramos, synthetic_png_bytes):
    assert segmentar(synthetic_png_bytes).status_code == 200

    spans = por_nombre(tramos)
    assert set(ETAPAS) <= set(spans)
    peticion = spans['POST /api/v1/segment/']
    for etapa in ETAPAS:
        assert spans[etapa].context.trace_id == peticion.context.trace_id
        assert spans[etapa].parent.span_id == peticion.context.span_id
    assert peticion.resource.attributes['service.name'] == 'backend-ml'


def test_los_tramos_llevan_solo_numeros_del_proceso(tramos, synthetic_png_bytes):
    cuerpo = segmentar(synthetic_png_bytes).json()

    spans = por_nombre(tramos)
    assert spans['segmentar'].attributes['cromosomas'] == cuerpo['chromosome_count']
    assert (spans['segmentar'].attributes['ancho'], spans['segmentar'].attributes['alto']) == (
        cuerpo['image_width'], cuerpo['image_height'])
    assert spans['clasificar'].attributes['cromosomas'] == cuerpo['chromosome_count']
    assert spans['esperar_turno'].attributes['turno_conseguido'] is True


def test_continua_la_traza_que_llega_por_traceparent(tramos, synthetic_png_bytes):
    """Es lo que une backend-clinic con backend-ml en una sola traza."""
    traza = '0af7651916cd43dd8448eb211c80319c'

    segmentar(synthetic_png_bytes, traceparent=f'00-{traza}-b7ad6b7169203331-01')

    assert {format(s.context.trace_id, '032x') for s in tramos.get_finished_spans()} == {traza}


def test_el_healthcheck_no_deja_traza(tramos):
    assert TestClient(app).get('/health/').status_code == 200
    assert tramos.get_finished_spans() == ()


def test_sin_turno_el_tramo_de_espera_lo_dice(tramos):
    limite = LimiteInferencias(maximo=1, espera_s=0)
    with limite.turno():
        with pytest.raises(HTTPException) as error:
            with limite.turno():
                pass    # pragma: no cover - no se llega: no hay turno
    assert error.value.status_code == 503

    esperas = [s for s in tramos.get_finished_spans() if s.name == 'esperar_turno']
    assert [s.attributes['turno_conseguido'] for s in esperas] == [True, False]


# ---------- sin PII (D4) ----------

def test_ningun_tramo_guarda_el_nombre_del_archivo_ni_cabeceras(tramos, synthetic_png_bytes):
    """El nombre del archivo subido puede llevar el código del caso."""
    TestClient(app).post('/api/v1/segment/',
                         files={'file': ('PEREZ-JUAN-1234567.png', synthetic_png_bytes, 'image/png')},
                         headers={'X-Paciente': 'PEREZ JUAN'})

    for span in tramos.get_finished_spans():
        texto = ' '.join(f'{k}={v}' for k, v in span.attributes.items()) + span.name
        assert 'PEREZ' not in texto and '1234567' not in texto
