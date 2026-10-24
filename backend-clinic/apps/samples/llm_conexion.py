"""Conexión con el LLM local: reintentos explícitos y límite de concurrencia.

DD-AUD-001 F2 (issue #3), hallazgo CON-04 de la auditoría de M8.

## Por qué existe

Cinco módulos (`llm_client`, `tool_router`, `rag_qa`, `agente`, `agente_grafo`)
construían cada uno su cliente del SDK. Ninguno fijaba `max_retries`, y el SDK
de OpenAI reintenta **2 veces por defecto también tras un timeout**
(`openai/_base_client.py`, `DEFAULT_MAX_RETRIES = 2`). Con
`CLINIC_LLM_TIMEOUT = 240 s`, una petición podía esperar unos 12 minutos.

Aquí se construyen todos, con `max_retries` explícito
(`CLINIC_LLM_MAX_RETRIES`, por defecto 0). Un reintento tras 240 s de espera
solo duplica la espera del usuario; los fallos de disponibilidad ya los cubre
el circuit breaker de cada llamador.

## Límite de llamadas simultáneas

El modelo local tarda entre 30 y 120 s por respuesta (auditoría, P4) y corre en
la misma CPU que todo lo demás. `turno_llm()` deja pasar como mucho
`CLINIC_LLM_MAX_CONCURRENTES` llamadas a la vez (por defecto 2). La siguiente
espera hasta `CLINIC_LLM_ESPERA_MAX_S` (5 s) y, si no hay hueco, recibe
`LlmOcupado`: un rechazo rápido y explicable en vez de una cola invisible.
Estar ocupado **no** es un fallo del servicio, así que no debe abrir ningún
circuit breaker.
"""
from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import Iterator

from django.conf import settings

API_KEY_OLLAMA = 'ollama'   # Ollama no valida la clave, pero el SDK exige una


class LlmOcupado(Exception):
    """Todas las plazas para llamar al LLM están ocupadas."""


def _max_retries() -> int:
    return int(getattr(settings, 'CLINIC_LLM_MAX_RETRIES', 0))


def crear_cliente_llm(base_url: str | None = None, timeout: float | None = None):
    """Cliente del SDK de OpenAI contra el LLM local, con `max_retries` explícito."""
    from openai import OpenAI          # import perezoso: el SDK es opcional (RN-07)
    return OpenAI(
        base_url=base_url or settings.CLINIC_LLM_URL,
        api_key=API_KEY_OLLAMA,
        timeout=float(timeout if timeout is not None else settings.CLINIC_LLM_TIMEOUT),
        max_retries=_max_retries(),
    )


def crear_modelo_chat(**kwargs):
    """Modelo de LangChain (agente con LangGraph), con el mismo `max_retries`."""
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        base_url=settings.CLINIC_LLM_URL,
        api_key=API_KEY_OLLAMA,
        model=settings.CLINIC_LLM_MODEL,
        timeout=float(settings.CLINIC_LLM_TIMEOUT),
        max_retries=_max_retries(),
        **kwargs,
    )


class LimiteLlm:
    def __init__(self, maximo: int, espera_s: float) -> None:
        if maximo < 1:
            raise ValueError(f'CLINIC_LLM_MAX_CONCURRENTES debe ser >= 1, no {maximo}')
        if espera_s < 0:
            raise ValueError(f'CLINIC_LLM_ESPERA_MAX_S no puede ser negativo, no {espera_s}')
        self.maximo = maximo
        self.espera_s = espera_s
        self._semaforo = threading.BoundedSemaphore(maximo)

    @contextmanager
    def turno(self) -> Iterator[None]:
        if not self._semaforo.acquire(timeout=self.espera_s):
            raise LlmOcupado(f'el asistente está ocupado: {self.maximo} consultas en curso')
        try:
            yield
        finally:
            self._semaforo.release()


limite_llm = LimiteLlm(
    maximo=int(getattr(settings, 'CLINIC_LLM_MAX_CONCURRENTES', 2)),
    espera_s=float(getattr(settings, 'CLINIC_LLM_ESPERA_MAX_S', 5.0)),
)


def turno_llm():
    """Ocupa una plaza mientras dura una llamada al LLM; `LlmOcupado` si no hay.

    Se resuelve `limite_llm` en cada llamada, no al importar, para que las
    pruebas puedan sustituirlo.
    """
    return limite_llm.turno()
