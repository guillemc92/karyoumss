"""Trazas con OpenTelemetry (DD-OBS-001).

Apagado por omisión: sin `OTEL_EXPORTER_OTLP_ENDPOINT` no se crea nada y el
servicio se comporta como antes (D2). Si el paquete no está instalado, tampoco
falla (RN-07).

Qué se instrumenta (D3):
- Django: una traza por petición;
- httpx: la llamada a backend-ml sale con `traceparent`, y allí continúa la traza;
- sqlite3: un tramo por consulta, con la sentencia y SIN sus parámetros.

RN-03 (D4): no se capturan cabeceras, cuerpos ni parámetros de SQL, y a la URL
se le quita la cadena de consulta, que puede llevar un texto de búsqueda.
"""
from __future__ import annotations

import os
from typing import Any

VARIABLE = 'OTEL_EXPORTER_OTLP_ENDPOINT'
#: El healthcheck de Docker llama a /admin/login/ cada pocos segundos: sería ruido.
URLS_EXCLUIDAS = 'admin/login'
#: Atributos de la petición que llevan la URL con su cadena de consulta.
_CON_CONSULTA = ('http.url', 'http.target', 'url.full')
_SOLO_CONSULTA = ('url.query',)

_proveedor: Any = None


def activa() -> bool:
    return _proveedor is not None


def sin_consulta(valor: str) -> str:
    """`/ruta?buscar=algo` → `/ruta`."""
    return valor.split('?', 1)[0]


def _limpiar_url(span: Any, request: Any) -> None:
    """Se ejecuta al abrir el tramo de cada petición: quita la cadena de consulta."""
    if span is None or not span.is_recording():
        return
    atributos = getattr(span, 'attributes', None) or {}
    for clave in _CON_CONSULTA:
        if clave in atributos:
            span.set_attribute(clave, sin_consulta(str(atributos[clave])))
    for clave in _SOLO_CONSULTA:
        if clave in atributos:
            span.set_attribute(clave, '')


def _crear_proveedor(servicio: str, procesador: Any = None) -> Any:
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider

    proveedor = TracerProvider(resource=Resource.create({'service.name': servicio}))
    if procesador is None:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        procesador = BatchSpanProcessor(OTLPSpanExporter())
    proveedor.add_span_processor(procesador)
    return proveedor


def _instrumentadores() -> list[Any]:
    from opentelemetry.instrumentation.django import DjangoInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.instrumentation.sqlite3 import SQLite3Instrumentor
    return [DjangoInstrumentor(), HTTPXClientInstrumentor(), SQLite3Instrumentor()]


def configurar(servicio: str, procesador: Any = None) -> bool:
    """Enciende las trazas. Devuelve si quedaron encendidas.

    Hay que llamarla ANTES de `get_wsgi_application()`: Django lee la lista de
    middlewares al crear la aplicación. `procesador` solo lo usan las pruebas.
    """
    global _proveedor
    if _proveedor is not None:
        return True
    if procesador is None and not os.environ.get(VARIABLE):
        return False
    try:
        instrumentadores = _instrumentadores()
        proveedor = _crear_proveedor(servicio, procesador)
    except ImportError:
        return False
    os.environ.setdefault('OTEL_PYTHON_DJANGO_EXCLUDED_URLS', URLS_EXCLUIDAS)
    django, httpx, sqlite = instrumentadores
    django.instrument(tracer_provider=proveedor, request_hook=_limpiar_url)
    httpx.instrument(tracer_provider=proveedor)
    sqlite.instrument(tracer_provider=proveedor)
    _proveedor = proveedor
    return True


def apagar() -> None:
    """Deshace `configurar`. Lo usan las pruebas para no dejar estado global."""
    global _proveedor
    if _proveedor is None:
        return
    for instrumentador in _instrumentadores():
        instrumentador.uninstrument()
    _proveedor.shutdown()
    _proveedor = None
