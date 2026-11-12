"""Trazas con OpenTelemetry (DD-OBS-001).

Apagado por omisión: sin `OTEL_EXPORTER_OTLP_ENDPOINT` no se crea nada y el
servicio se comporta como antes (D2). Si el paquete no está instalado, tampoco
falla (RN-07).

`tramo()` marca una etapa del pipeline. Con las trazas apagadas no hace nada.

RN-03: los atributos de un tramo son solo números del proceso (cuántos
cromosomas, tamaño de la imagen). Nunca datos del paciente.
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterator

VARIABLE = 'OTEL_EXPORTER_OTLP_ENDPOINT'
NOMBRE_TRAZADOR = 'biomed.backend-ml'
#: El healthcheck de Docker llama a /health/ cada pocos segundos: sería ruido.
URLS_EXCLUIDAS = 'health'

_proveedor: Any = None


def activa() -> bool:
    return _proveedor is not None


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


def configurar(servicio: str, app: Any, procesador: Any = None) -> bool:
    """Enciende las trazas de `app` (FastAPI). Devuelve si quedaron encendidas.

    Se instrumenta UNA vez por proceso: la librería no deja instrumentar dos
    veces la misma app. `procesador` solo lo usan las pruebas, para recoger los
    tramos en memoria.
    """
    global _proveedor
    if _proveedor is not None:
        return True
    if procesador is None and not os.environ.get(VARIABLE):
        return False
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        proveedor = _crear_proveedor(servicio, procesador)
    except ImportError:
        return False
    # Sin los tramos internos «http receive/send» de ASGI: son ruido en la traza.
    FastAPIInstrumentor.instrument_app(app, tracer_provider=proveedor, excluded_urls=URLS_EXCLUIDAS,
                                       exclude_spans=['receive', 'send'])
    # Starlette arma la cadena de middlewares en la primera petición y la guarda.
    # Si ya estaba armada, la instrumentación no entraría: se obliga a rearmarla.
    app.middleware_stack = None
    _proveedor = proveedor
    return True


@contextmanager
def tramo(nombre: str, **atributos: int | float | str | bool) -> Iterator[Any]:
    """Una etapa dentro de la traza en curso. Sin trazas, no hace nada."""
    if _proveedor is None:
        yield None
        return
    trazador = _proveedor.get_tracer(NOMBRE_TRAZADOR)
    with trazador.start_as_current_span(nombre, attributes=atributos) as span:
        yield span
