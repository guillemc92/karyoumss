"""El agente como grafo de estados con memoria persistente — nivel 5.

    Pensar -> ¿pide herramientas? -> Actuar -> Pensar -> ... -> Respuesta
                     |
                     no -> fin

## Qué añade sobre el nivel 4, y qué NO

El bucle ReAct de `agente.py` funciona y sigue en pie: esto **no lo sustituye**.
Lo que el nivel 4 no puede hacer es recordar. Su lista de mensajes vive en la
petición y muere con ella, así que una repregunta —«¿y de esos cuál es el más
urgente?»— llega sin contexto y el modelo no tiene de dónde agarrarse.

LangGraph aporta exactamente eso: un **checkpointer** que guarda el estado del
hilo tras cada paso. La conversación sobrevive al proceso y se reanuda por
`thread_id`.

## Lo que deliberadamente NO se mueve aquí

El estado **clínico** no vive en estos checkpoints y no va a vivir. Un caso
avanza READY -> ANALYST_VALIDATED -> SIGNED -> REPORTED en PostgreSQL, con un
audit trail append-only encadenado por SHA-256 (ADR-0022) que es lo que sostiene
la firma electrónica. Duplicar esa máquina de estados en un checkpointer crearía
**una segunda fuente de verdad para un proceso auditado**: cuando alguien
pregunte en qué estado estaba un caso, no puede haber dos respuestas. Es una
objeción de cumplimiento, no de complejidad (ADR-0031).

Por la misma razón no se usa el `interrupt` de LangGraph para la aprobación
humana. Suena a que encaja —«aprobar desde otra sesión» es literalmente RN-06—
pero `preparar_validacion_de_caso` **nunca ejecuta**, ni con confirmación: la
validación real exige un analista identificado y la firma MFA de un supervisor.
Un `interrupt` sobre el agente sería aprobar algo que de todos modos no escribe.

Aquí el nivel 5 es **memoria conversacional**. Nada más, y es bastante.

## El catálogo no se duplica

El grafo recibe `schemas()` y `ejecutar()` de `agente_acciones`, los mismos que
usan el bucle del nivel 4 y el servidor MCP. Si mañana aparece una séptima
herramienta, este módulo la ve sin tocarse. Y el guardrail de escritura sigue
viviendo **dentro** de la herramienta, así que viaja con ella por cualquier
camino.

Verificado: `bind_tools()` acepta los schemas en formato OpenAI tal cual, sin
traducirlos. Y **hace falta el system prompt**: sin `INSTRUCCIONES`, `llama3.2:3b`
no pide herramientas aunque las tenga declaradas.

## Privacidad

En el checkpoint queda el historial de la conversación, que incluye lo que
devuelven las herramientas: códigos CHN y referencias anónimas (`ANON-…`), que
es precisamente el dato ya anonimizado del sistema (ADR-0003). **Ninguna
herramienta del catálogo devuelve PII**, así que no la hay que proteger aquí
(RN-03). El fichero es local y está fuera de git.
"""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Annotated, TypedDict

from django.conf import settings
# LangGraph se importa arriba porque el esquema de estado necesita resolver
# `add_messages` al declararse. Para que el sistema siga arrancando sin la
# dependencia (RN-07), quien use este módulo debe importarlo DENTRO de la
# función, no en la cabecera —igual que se hace con el RAG—.
from langgraph.graph.message import add_messages

from .agente import MAX_PASOS, TEMPERATURA, AgenteError, ResultadoAgente, Traza
from .agente_acciones import INSTRUCCIONES, ejecutar, schemas

# La memoria del agente es SUYA: fichero aparte de la base clínica. Mezclarlas
# invitaría justo a la confusión que este módulo evita (ver docstring).
RUTA_MEMORIA = Path(__file__).resolve().parents[2] / 'agente_memoria.sqlite3'

# `recursion_limit` cuenta pasos del grafo, y un ciclo son DOS (pensar + actuar).
# Se mantiene el mismo tope de llamadas al modelo que el nivel 4.
LIMITE_RECURSION = 2 * MAX_PASOS + 1


class EstadoAgente(TypedDict):
    """Lo único que el grafo arrastra entre pasos: la conversación.

    `add_messages` es el reductor: cada nodo devuelve los mensajes NUEVOS y
    LangGraph los concatena al hilo. Por eso los nodos no manipulan el historial.
    """

    messages: Annotated[list, add_messages]


_grafo = None
_conexion = None


def _modelo():
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        base_url=getattr(settings, 'CLINIC_LLM_URL', 'http://localhost:11434/v1'),
        api_key='ollama',
        model=getattr(settings, 'CLINIC_LLM_MODEL', 'llama3.2:3b'),
        temperature=TEMPERATURA,           # decisiones reproducibles, no creativas
        timeout=float(getattr(settings, 'CLINIC_LLM_TIMEOUT', 240.0)),
    ).bind_tools(schemas())


def construir():
    """Compila el grafo una vez por proceso, con el checkpointer enchufado."""
    global _grafo, _conexion
    if _grafo is not None:
        return _grafo

    from langchain_core.messages import ToolMessage
    from langgraph.checkpoint.sqlite import SqliteSaver
    from langgraph.graph import END, StateGraph

    modelo = _modelo()

    def pensar(estado: EstadoAgente) -> dict:
        return {'messages': [modelo.invoke(estado['messages'])]}

    def actuar(estado: EstadoAgente) -> dict:
        """Ejecuta lo que el modelo pidió. El dato sale del código, no del modelo."""
        salidas = []
        for llamada in estado['messages'][-1].tool_calls:
            # `ejecutar` nunca lanza: devuelve el error como observación para que
            # el modelo rectifique en el siguiente paso.
            resultado = ejecutar(llamada['name'], llamada.get('args') or {})
            salidas.append(ToolMessage(content=str(resultado),
                                       tool_call_id=llamada['id'],
                                       name=llamada['name']))
        return {'messages': salidas}

    def siguiente(estado: EstadoAgente) -> str:
        ultimo = estado['messages'][-1]
        return 'actuar' if getattr(ultimo, 'tool_calls', None) else END

    g = StateGraph(EstadoAgente)
    g.add_node('pensar', pensar)
    g.add_node('actuar', actuar)
    g.set_entry_point('pensar')
    g.add_conditional_edges('pensar', siguiente, {'actuar': 'actuar', END: END})
    g.add_edge('actuar', 'pensar')

    # `check_same_thread=False`: el servidor de desarrollo atiende peticiones en
    # hilos distintos y la conexión se comparte.
    _conexion = sqlite3.connect(str(RUTA_MEMORIA), check_same_thread=False)
    _grafo = g.compile(checkpointer=SqliteSaver(_conexion))
    return _grafo


def _traza_desde(mensajes: list, desde: int, inicio: float) -> Traza:
    """Reconstruye la traza del nivel 4 a partir de los mensajes del hilo.

    Se emite con la MISMA forma que el bucle ReAct para que la evidencia sea
    comparable entre niveles y el endpoint no cambie de contrato.
    """
    from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

    traza = Traza()
    traza.inicio = inicio
    for m in mensajes[desde:]:
        if isinstance(m, HumanMessage):
            traza.registrar('pregunta', str(m.content))
        elif isinstance(m, AIMessage):
            for c in (m.tool_calls or []):
                traza.registrar('accion', f"{c['name']}({c.get('args') or {}})")
            if m.content:
                traza.registrar('respuesta', str(m.content))
            uso = getattr(m, 'usage_metadata', None) or {}
            traza.tokens_entrada += uso.get('input_tokens', 0)
            traza.tokens_salida += uso.get('output_tokens', 0)
        elif isinstance(m, ToolMessage):
            traza.registrar('observacion', f'{m.name} -> {str(m.content)[:200]}')
    return traza


def conversar(pregunta: str, thread_id: str) -> ResultadoAgente:
    """Un turno de conversación sobre un hilo que persiste.

    Con el mismo `thread_id`, el agente recuerda los turnos anteriores aunque el
    proceso se haya reiniciado entre medias — que es la diferencia con el nivel 4.

    Degrada como el resto del sistema (RN-07): si el modelo no está disponible
    se lanza `AgenteError` y el llamador responde sin IA.
    """
    if not getattr(settings, 'CLINIC_LLM_ENABLED', False):
        raise AgenteError('IA desactivada')

    from langchain_core.messages import HumanMessage
    from langgraph.errors import GraphRecursionError

    inicio = time.time()
    app = construir()
    cfg = {'configurable': {'thread_id': thread_id},
           'recursion_limit': LIMITE_RECURSION}

    # Cuántos mensajes había ya en el hilo: la traza de ESTE turno empieza ahí.
    previos = app.get_state(cfg)
    desde = len(previos.values.get('messages', [])) if previos.values else 0

    entrada = {'messages': [HumanMessage(content=pregunta)]}
    if desde == 0:
        # El system prompt se inyecta solo al abrir el hilo: repetirlo en cada
        # turno lo duplicaría en el historial y encarecería cada llamada.
        from langchain_core.messages import SystemMessage
        entrada['messages'].insert(0, SystemMessage(content=INSTRUCCIONES))

    completado = True
    try:
        estado = app.invoke(entrada, cfg)
        mensajes = estado['messages']
    except GraphRecursionError:
        # Mismo freno que el nivel 4: un agente sin tope es una fuga de dinero.
        completado = False
        mensajes = app.get_state(cfg).values.get('messages', [])
    except Exception as exc:                          # noqa: BLE001 — RN-07
        raise AgenteError(f'modelo no disponible: {exc}') from exc

    traza = _traza_desde(mensajes, desde, inicio)
    if not completado:
        traza.registrar('corte', f'tope de {MAX_PASOS} pasos alcanzado')

    ultimo = mensajes[-1] if mensajes else None
    respuesta = str(getattr(ultimo, 'content', '') or '') if completado else (
        'No pude completar la consulta dentro del límite de pasos.')
    return ResultadoAgente(respuesta=respuesta, traza=traza, completado=completado)


def olvidar(thread_id: str) -> None:
    """Borra un hilo. La memoria conversacional es descartable **a propósito**:
    no es un registro clínico y no está sujeta a RN-05 (append-only)."""
    construir()
    if _conexion is None:
        return
    for tabla in ('checkpoints', 'writes'):
        try:
            _conexion.execute(f'DELETE FROM {tabla} WHERE thread_id = ?', (thread_id,))
        except sqlite3.OperationalError:
            pass                                     # la tabla aún no existe
    _conexion.commit()
