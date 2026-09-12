"""El bucle del agente (ReAct) — nivel 4 de la escalera.

    Pensamiento -> Acción -> Observación -> ... -> Respuesta final

Los niveles anteriores decidían **una** cosa y respondían: el tool calling elige
una herramienta, el RAG recupera unos fragmentos. El agente encadena: puede
consultar el estado, después la documentación, y combinar ambas cosas en una
respuesta. Esa es toda la diferencia.

## Tres reglas, y la tercera no es opcional

1. Si el modelo pide herramientas, se ejecutan y se le devuelve el resultado.
2. Si el modelo responde texto, ese texto es la respuesta final: se corta.
3. Si se llega a `MAX_PASOS`, se corta igual. **Un agente sin tope es un bucle
   infinito con factura**: el modelo puede pedir la misma herramienta una y otra
   vez sin converger, y aquí cada paso cuesta ~100 s de CPU.

## El bucle NO sabe qué herramientas existen

Recibe los *schemas* y un callback `ejecutar`. Por eso el mismo bucle vale con
herramientas locales (`agente_acciones.py`) o descubiertas por MCP: cambia el
transporte, no la lógica. Es la separación que hace que el nivel 4 no obligue a
reescribir el nivel 2.

## Traza

Cada paso queda registrado con su tipo y su detalle. No es depuración: es la
evidencia que la consigna pide —«respuestas más traza completa»— y, en un
sistema clínico, la única forma de reconstruir por qué el agente dijo lo que
dijo. Sin traza, un agente es un oráculo.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Callable

from django.conf import settings

logger = logging.getLogger(__name__)

MAX_PASOS = 6
TEMPERATURA = 0.0        # decisiones técnicas: reproducibles, no creativas


class AgenteError(Exception):
    """El modelo no está disponible. El llamador degrada (RN-07)."""


@dataclass
class Traza:
    """Registro paso a paso: la observabilidad mínima de un agente."""

    pasos: list[dict] = field(default_factory=list)
    tokens_entrada: int = 0
    tokens_salida: int = 0
    inicio: float = field(default_factory=time.time)

    def registrar(self, tipo: str, detalle: str) -> None:
        self.pasos.append({
            'n': len(self.pasos) + 1,
            'tipo': tipo,                    # pregunta|accion|observacion|respuesta|corte
            'detalle': detalle,
            'ms': int((time.time() - self.inicio) * 1000),
        })

    @property
    def latency_ms(self) -> int:
        return int((time.time() - self.inicio) * 1000)

    def as_dict(self) -> dict:
        return {
            'pasos': self.pasos,
            'n_pasos': len(self.pasos),
            'tokens_entrada': self.tokens_entrada,
            'tokens_salida': self.tokens_salida,
            'latency_ms': self.latency_ms,
        }

    def resumen(self) -> str:
        """Una línea por paso, para consola o informe."""
        return '\n'.join(
            f"  [{p['n']:02d}] {p['tipo']:12} {p['detalle'][:100]}"
            for p in self.pasos
        )


@dataclass
class ResultadoAgente:
    respuesta: str
    traza: Traza
    completado: bool = True          # False si se cortó por MAX_PASOS
    mensajes: list[dict] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            'respuesta': self.respuesta,
            'completado': self.completado,
            'traza': self.traza.as_dict(),
        }


def _cliente():
    from openai import OpenAI
    return OpenAI(
        base_url=getattr(settings, 'CLINIC_LLM_URL', 'http://localhost:11434/v1'),
        api_key='ollama',
        timeout=float(getattr(settings, 'CLINIC_LLM_TIMEOUT', 240.0)),
    )


def ejecutar_agente(pregunta: str,
                    schemas: list[dict],
                    ejecutar: Callable[[str, dict], dict],
                    instrucciones: str,
                    max_pasos: int = MAX_PASOS,
                    mensajes_previos: list[dict] | None = None) -> ResultadoAgente:
    """Corre el bucle ReAct hasta una respuesta final o el tope de pasos.

    `ejecutar(nombre, argumentos) -> dict` es lo único que el bucle sabe hacer
    con una acción. Quién la resuelve —código local o un servidor MCP— es
    problema del llamador.
    """
    if not getattr(settings, 'CLINIC_LLM_ENABLED', False):
        raise AgenteError('llm_disabled')

    traza = Traza()
    traza.registrar('pregunta', pregunta)

    mensajes = list(mensajes_previos or [{'role': 'system', 'content': instrucciones}])
    mensajes.append({'role': 'user', 'content': pregunta})

    try:
        cliente = _cliente()
    except Exception as exc:                        # noqa: BLE001
        raise AgenteError(str(exc)) from exc

    for _ in range(max_pasos):
        try:
            r = cliente.chat.completions.create(
                model=getattr(settings, 'CLINIC_LLM_MODEL', 'llama3.2:3b'),
                messages=mensajes,
                tools=schemas,
                temperature=TEMPERATURA,
            )
        except Exception as exc:                    # noqa: BLE001
            traza.registrar('error', str(exc)[:200])
            raise AgenteError(str(exc)) from exc

        uso = getattr(r, 'usage', None)
        if uso:
            traza.tokens_entrada += getattr(uso, 'prompt_tokens', 0) or 0
            traza.tokens_salida += getattr(uso, 'completion_tokens', 0) or 0

        msg = r.choices[0].message

        # Regla 2 — texto: es la respuesta final.
        if not getattr(msg, 'tool_calls', None):
            texto = msg.content or ''
            traza.registrar('respuesta', texto or '(vacía)')
            mensajes.append({'role': 'assistant', 'content': texto})
            return ResultadoAgente(texto, traza, True, mensajes)

        # Regla 1 — acción -> observación.
        mensajes.append(msg.model_dump(exclude_none=True))
        for tc in msg.tool_calls:
            nombre = tc.function.name
            try:
                argumentos = json.loads(tc.function.arguments or '{}')
            except json.JSONDecodeError:
                argumentos = {}
            traza.registrar('accion', f'{nombre}({tc.function.arguments})')

            # Un fallo de una herramienta NO tumba al agente: se le devuelve el
            # error como observación para que pueda corregir o abandonar.
            try:
                resultado = ejecutar(nombre, argumentos)
            except Exception as exc:                # noqa: BLE001
                logger.warning('herramienta %s falló: %s', nombre, exc)
                resultado = {'error': str(exc)}

            observacion = json.dumps(resultado, ensure_ascii=False)
            traza.registrar('observacion', observacion)
            mensajes.append({
                'role': 'tool',
                'tool_call_id': tc.id,
                'content': observacion[:4000],      # el 3B se ahoga con más
            })

    # Regla 3 — tope de pasos.
    aviso = (f'Alcancé el límite de {max_pasos} pasos sin llegar a una '
             f'respuesta final. Lo consultado queda en la traza.')
    traza.registrar('corte', aviso)
    return ResultadoAgente(aviso, traza, False, mensajes)
