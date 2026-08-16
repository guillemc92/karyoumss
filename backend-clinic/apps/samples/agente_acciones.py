"""Las acciones del agente: el catálogo de herramientas + el RAG.

El agente elige entre **consultar estado** (las cuatro herramientas de
`tools.py`, que leen la base) y **consultar documentación** (el RAG sobre el
corpus). Es la disyuntiva del bucle agéntico: *tool* o *RAG*.

## Nada se reescribe

Los `schemas` se **derivan** del `CATALOGO` que ya existe: mismo nombre, misma
descripción, misma función. Si mañana se añade una quinta herramienta al
catálogo, el agente la ve sin tocar este módulo. Es la misma propiedad que hace
que el servidor MCP sea un envoltorio y no una copia.

## Por qué todas las acciones son de LECTURA

El agente puede consultar cualquier cosa, pero **no escribe nada**. No es una
limitación técnica: RN-01 exige que la validación de un cromosoma naranja y la
firma de un informe las haga una persona identificada, no un proceso automático.

El patrón para cuando se añada una acción de escritura ya está decidido y es el
del material de clase: la herramienta recibe `confirmado: bool`, con
`confirmado=false` devuelve el plan de lo que haría, y **solo un humano puede
poner `confirmado=true`** — el modelo nunca. Se documenta aquí para que quien
añada la primera escritura no improvise.
"""
from __future__ import annotations

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
    return [_schema_de(t) for t in CATALOGO] + [SCHEMA_RAG]


def ejecutar(nombre: str, argumentos: dict) -> dict:
    """Resuelve una acción. Es el callback que el bucle recibe.

    Devuelve siempre un dict — nunca lanza — porque el bucle entrega la
    observación al modelo y un error es información útil para que rectifique.
    """
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
                'disponibles': [t.name for t in CATALOGO] + [NOMBRE_RAG]}

    filas = tool.run()
    return {'herramienta': tool.name, 'fuente': tool.source,
            'n': len(filas), 'filas': filas[:20]}
