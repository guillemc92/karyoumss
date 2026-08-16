"""Las acciones del agente: el catálogo de herramientas + el RAG.

El agente elige entre **consultar estado** (las cuatro herramientas de
`tools.py`, que leen la base) y **consultar documentación** (el RAG sobre el
corpus). Es la disyuntiva del bucle agéntico: *tool* o *RAG*.

## Nada se reescribe

Los `schemas` se **derivan** del `CATALOGO` que ya existe: mismo nombre, misma
descripción, misma función. Si mañana se añade una quinta herramienta al
catálogo, el agente la ve sin tocar este módulo. Es la misma propiedad que hace
que el servidor MCP sea un envoltorio y no una copia.

## Seis acciones: cinco de lectura y una de escritura con guardrail

Las cinco de lectura —cuatro consultas de estado y el RAG— no necesitan
protección: leer no rompe nada.

La sexta, `preparar_validacion_de_caso`, sí escribe en el dominio, y por eso
lleva el guardrail **dentro de la herramienta** y no en el bucle: así viaja con
ella cuando se publica por MCP, a cualquier cliente que la descubra. Ver
`agente_escritura.py` para la política que implementa (RN-01) y por qué aquí es
más estricta que en el ejemplo de clase.
"""
from __future__ import annotations

from .agente_escritura import NOMBRE as NOMBRE_ESCRITURA
from .agente_escritura import SCHEMA as SCHEMA_ESCRITURA
from .agente_escritura import ejecutar as ejecutar_escritura
from .tools import CATALOGO, POR_NOMBRE

NOMBRE_RAG = 'buscar_documentacion'

INSTRUCCIONES = (
    'Eres el asistente del laboratorio de citogenética BIOMED UMSS. '
    'Respondes SOLO con lo que devuelvan tus herramientas: no sabes nada por tu '
    'cuenta y no inventas datos ni cifras.\n\n'
    'CÓMO ELEGIR:\n'
    f'- Preguntas sobre QUÉ HAY AHORA (casos en cada etapa, cromosomas '
    f'pendientes de revisar): usa las herramientas de consulta.\n'
    f'- Preguntas sobre POR QUÉ, QUÉ SIGNIFICA, QUÉ REGLA aplica o CÓMO '
    f'funciona algo: usa {NOMBRE_RAG}. SIEMPRE. Nunca respondas eso de memoria.\n'
    '\n'
    # Medido: ante «hay cromosomas pendientes, y por qué hay que revisarlos?»
    # el modelo consultó la herramienta, NO llamó al RAG, y se inventó los
    # motivos —incluido un umbral del 90% cuando el real es 85%— atribuyéndolos
    # a «la herramienta de consulta». Inventar es grave; atribuirlo a una fuente
    # que no lo dijo, más.
    'SI LA PREGUNTA TIENE DOS PARTES, HAZ DOS CONSULTAS:\n'
    'Ejemplo: «¿hay cromosomas pendientes, y por qué hay que revisarlos?» son '
    'DOS preguntas. Primero la herramienta para el "hay", después '
    f'{NOMBRE_RAG} para el "por qué". No respondas hasta tener las dos.\n'
    '\n'
    'PROHIBIDO:\n'
    '- Escribir «según la herramienta» delante de algo que la herramienta no '
    'devolvió. Si no está en una observación, no lo digas.\n'
    '- Dar cifras, umbrales o porcentajes que no aparezcan en una observación.\n'
    '- Responder de memoria. Si ninguna herramienta puede responder, dilo.\n\n'
    'Responde en español, breve y concreto. Cita siempre de dónde sale el dato.'
)


def _schema_de(tool) -> dict:
    """Traduce un ToolSpec del catálogo al formato de tool calling."""
    return {
        'type': 'function',
        'function': {
            'name': tool.name,
            'description': f'{tool.description} Fuente: tabla {tool.source}.',
            # Las consultas del catálogo no reciben parámetros: devuelven el
            # estado completo. Declararlo explícitamente evita que el modelo se
            # invente argumentos.
            'parameters': {'type': 'object', 'properties': {}, 'required': []},
        },
    }


SCHEMA_RAG = {
    'type': 'function',
    'function': {
        'name': NOMBRE_RAG,
        'description': (
            'Busca en la documentación del laboratorio: el estándar ISCN 2024, '
            'las decisiones de arquitectura y las reglas de negocio. Úsala para '
            'preguntas sobre qué significa algo, cómo se calcula, quién puede '
            'hacer qué o por qué el sistema se comporta de cierta forma. '
            'Devuelve fragmentos con su fuente y su similitud.'
        ),
        'parameters': {
            'type': 'object',
            'properties': {
                'pregunta': {
                    'type': 'string',
                    'description': 'La consulta a buscar en la documentación.',
                },
            },
            'required': ['pregunta'],
        },
    },
}


def schemas() -> list[dict]:
    """Todo lo que el agente puede hacer, en formato de tool calling."""
    return [_schema_de(t) for t in CATALOGO] + [SCHEMA_RAG, SCHEMA_ESCRITURA]


def ejecutar(nombre: str, argumentos: dict) -> dict:
    """Resuelve una acción. Es el callback que el bucle recibe.

    Devuelve siempre un dict — nunca lanza — porque el bucle entrega la
    observación al modelo y un error es información útil para que rectifique.
    """
    if nombre == NOMBRE_ESCRITURA:
        return ejecutar_escritura(argumentos)

    if nombre == NOMBRE_RAG:
        from .rag_qa import responder_documental

        r = responder_documental(argumentos.get('pregunta') or '')
        if not r.responde:
            return {'encontrado': False,
                    'motivo': r.motivo or 'la documentación no cubre eso'}
        return {
            'encontrado': True,
            'respuesta': r.texto,
            'fuentes': [{'documento': c.fragmento.fuente,
                         'seccion': c.fragmento.seccion or '—',
                         'similitud': c.porcentaje} for c in r.citas],
        }

    tool = POR_NOMBRE.get(nombre)
    if tool is None:
        # El modelo puede inventar un nombre pese al schema. Se le dice qué
        # existe en vez de fallar en silencio.
        return {'error': f'no existe la herramienta «{nombre}»',
                'disponibles': [t.name for t in CATALOGO] + [NOMBRE_RAG, NOMBRE_ESCRITURA]}

    filas = tool.run()
    return {'herramienta': tool.name, 'fuente': tool.source,
            'n': len(filas), 'filas': filas[:20]}
