"""Enrutador de preguntas a herramientas — tool calling (Módulo 6, semana 3).

Decide **qué** herramienta responde una pregunta. Nunca decide **qué** contesta:
eso lo produce el código de `tools.py` contra la base de datos.

## Los tres caminos posibles

    KEYWORD    la pregunta usa una palabra del catálogo → se ejecuta sin modelo
    LLM        ninguna palabra coincide → el modelo elige entre las publicadas
    SIN_MATCH  ni las palabras ni el modelo encontraron herramienta → "no sé"

`SIN_MATCH` **no es un error**. Es la respuesta correcta cuando el dato no está
en el sistema, y viene acompañada del catálogo para que el usuario sepa qué sí
puede preguntar.

## Por qué el camino KEYWORD existe

No es una optimización: es lo que hace que el sistema **siga respondiendo con la
IA apagada**. Con `CLINIC_LLM_ENABLED=false`, las preguntas del vocabulario del
dominio se resuelven igual, con los mismos datos y las mismas fuentes. Lo único
que se pierde es la tolerancia a sinónimos — y esa diferencia, medida, es
exactamente lo que aporta el modelo.
"""
from __future__ import annotations

import logging
import time
from dataclasses import asdict, dataclass

from django.conf import settings

from .tools import CATALOGO, POR_NOMBRE, ToolSpec, buscar_por_palabra_clave, catalogo_publicado

logger = logging.getLogger(__name__)

# El modelo solo elige un nombre del catálogo (o NINGUNA). No redacta, no
# resume, no toca datos: por eso el esquema es mínimo y `strict`.
SELECCION_JSON_SCHEMA = {
    'type': 'json_schema',
    'json_schema': {
        'name': 'seleccion_herramienta',
        'strict': True,
        'schema': {
            'type': 'object',
            'properties': {
                'herramienta': {
                    'type': 'string',
                    'enum': [t.name for t in CATALOGO] + ['NINGUNA'],
                    'description': 'Nombre exacto de la herramienta, o NINGUNA si ninguna aplica.',
                },
                'motivo': {
                    'type': 'string',
                    'description': 'Una frase breve explicando la elección.',
                },
            },
            'required': ['herramienta', 'motivo'],
            'additionalProperties': False,
        },
    },
}


def _prompt_sistema() -> str:
    lineas = [
        'Eres un enrutador de consultas de un laboratorio de citogenética.',
        'Tu ÚNICA tarea es elegir qué herramienta responde la pregunta del usuario.',
        '',
        'REGLAS ESTRICTAS:',
        '1. NO respondas la pregunta. NO inventes datos. Solo eliges una herramienta.',
        '2. Elige por el SIGNIFICADO de la pregunta, no por coincidencia de palabras.',
        '3. Devuelve "NINGUNA" salvo que una herramienta responda EXACTAMENTE lo '
        'que se pregunta. Que la pregunta mencione palabras del laboratorio NO basta.',
        '',
        # La abstención necesita ejemplos y no solo una regla: medido sobre 30
        # preguntas etiquetadas, con la regla suelta el modelo elegía una
        # herramienta en 4 de 6 preguntas fuera de alcance (acierto 33%).
        'CUÁNDO DEVOLVER "NINGUNA" — son casos frecuentes, no excepcionales:',
        '- Estadísticas, totales o históricos: «cuántos X el año pasado», promedios.',
        '- Personas: quién es el jefe, quién atendió un caso, de quién es una muestra.',
        '- Documentación o procedimientos: qué dice el manual, cómo se hace algo.',
        '- Inventario: reactivos, equipos, insumos, fechas de vencimiento.',
        '- Dinero: precios, costos, presupuestos, facturación.',
        '- Datos de un paciente concreto.',
        '',
        'Las herramientas SOLO listan el estado ACTUAL de casos y cromosomas del '
        'flujo de trabajo. No cuentan, no promedian, no explican, no consultan '
        'documentos y no saben de personas ni de insumos.',
        '',
        'Elegir una herramienta equivocada es PEOR que devolver "NINGUNA": el '
        'usuario recibiría datos reales que no responden a su pregunta.',
        '',
        'HERRAMIENTAS DISPONIBLES:',
    ]
    lineas += [f'- {t.name}: {t.description}' for t in CATALOGO]
    return '\n'.join(lineas)


@dataclass
class Respuesta:
    """Resultado de una consulta. `camino` es la evidencia de cómo se resolvió."""

    camino: str                  # KEYWORD | LLM | SIN_MATCH
    tool: str | None
    source: str | None           # tabla real de la que salió el dato
    filas: list[dict]
    mensaje: str
    motivo: str = ''             # por qué el modelo eligió (solo camino LLM)
    latency_ms: int = 0
    catalogo: list[dict] | None = None   # se adjunta solo en SIN_MATCH

    def as_dict(self) -> dict:
        d = asdict(self)
        if self.catalogo is None:
            d.pop('catalogo')
        return d


def _ejecutar(tool: ToolSpec, camino: str, inicio: float, motivo: str = '') -> Respuesta:
    """Corre la herramienta. Acá el dato sale de la base, nunca del modelo."""
    filas = tool.run()
    return Respuesta(
        camino=camino,
        tool=tool.name,
        source=tool.source,
        filas=filas,
        mensaje=f'{len(filas)} resultado(s).' if filas else 'Sin resultados para esa consulta.',
        motivo=motivo,
        latency_ms=int((time.time() - inicio) * 1000),
    )


def _sin_match(inicio: float, detalle: str) -> Respuesta:
    """No hay herramienta para eso. No es un error: es la respuesta correcta."""
    return Respuesta(
        camino='SIN_MATCH',
        tool=None,
        source=None,
        filas=[],
        mensaje=f'No puedo responder eso. {detalle}',
        latency_ms=int((time.time() - inicio) * 1000),
        catalogo=catalogo_publicado(),
    )


def _elegir_con_modelo(pregunta: str) -> tuple[str, str]:
    """Pide al modelo el NOMBRE de una herramienta. Devuelve (nombre, motivo).

    Lanza RuntimeError si el servicio no está disponible; el llamador degrada.
    """
    from openai import OpenAI

    client = OpenAI(
        base_url=getattr(settings, 'CLINIC_LLM_URL', 'http://localhost:11434/v1'),
        api_key='ollama',
        timeout=float(getattr(settings, 'CLINIC_LLM_TIMEOUT', 240.0)),
    )
    resp = client.chat.completions.create(
        model=getattr(settings, 'CLINIC_LLM_MODEL', 'llama3.2:3b'),
        messages=[
            {'role': 'system', 'content': _prompt_sistema()},
            {'role': 'user', 'content': pregunta},
        ],
        response_format=SELECCION_JSON_SCHEMA,
        temperature=0.0,      # enrutar es determinista, no creativo
        max_tokens=200,
    )
    import json
    datos = json.loads(resp.choices[0].message.content or '{}')
    return datos.get('herramienta', 'NINGUNA'), datos.get('motivo', '')


def responder(pregunta: str) -> Respuesta:
    """Resuelve una pregunta contra el catálogo.

    Nunca lanza por culpa del modelo: si el LLM cae, se degrada a SIN_MATCH con
    el catálogo publicado (el sistema sigue usable, solo pierde los sinónimos).
    """
    inicio = time.time()
    pregunta = (pregunta or '').strip()
    if not pregunta:
        return _sin_match(inicio, 'La consulta está vacía.')

    # Camino 1 — vocabulario del dominio. No llama al modelo.
    tool = buscar_por_palabra_clave(pregunta)
    if tool is not None:
        return _ejecutar(tool, 'KEYWORD', inicio)

    # Camino 2 — el modelo elige. Solo si la IA está habilitada.
    if not getattr(settings, 'CLINIC_LLM_ENABLED', False):
        return _sin_match(
            inicio,
            'La asistencia por IA está desactivada y la consulta no usa el '
            'vocabulario del catálogo.',
        )

    try:
        nombre, motivo = _elegir_con_modelo(pregunta)
    except Exception as exc:                      # noqa: BLE001 — degradación
        logger.warning('Enrutador LLM no disponible: %s', exc)
        return _sin_match(inicio, 'La asistencia por IA no está disponible en este momento.')

    if nombre == 'NINGUNA' or nombre not in POR_NOMBRE:
        # El modelo puede devolver un nombre inexistente pese al enum: se trata
        # igual que NINGUNA en vez de confiar en que respetó el esquema.
        return _sin_match(inicio, 'Ninguna herramienta del catálogo responde esa pregunta.')

    return _ejecutar(POR_NOMBRE[nombre], 'LLM', inicio, motivo)
