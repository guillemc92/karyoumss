"""Respuesta fundamentada sobre el corpus — el paso de generación del RAG.

## Por qué esta capa existe: el umbral de similitud NO discrimina

Medido sobre el banco de 18 preguntas de `eval_rag`, con el índice de 1.144
fragmentos y `nomic-embed-text`:

    preguntas cubiertas por el corpus   similitud top-1: 0.601 – 0.695
    preguntas fuera del corpus          similitud top-1: 0.608 – 0.662

El rango de las que hay que rechazar está **dentro** del rango de las buenas.
Ningún umbral las separa: el barrido de 0.50 a 0.75 da 56% de acierto global en
todos los valores útiles. Con el umbral alto se gana abstención y se pierden 10
de 12 preguntas legítimas.

La causa no es el modelo: es que el coseno mide parecido **temático**, y todo el
corpus habla del mismo dominio. «¿Cuál es el teléfono del doctor Rojas?» se
parece a un ADR sobre el rol de administrador tanto como una pregunta legítima.
Es el mismo fenómeno que ADR-0027 midió sobre datos estructurados, ahora
reproducido sobre documentos.

## La separación de responsabilidades que sí funciona

    el ÍNDICE recupera candidatos  ->  el MODELO decide si responden

El índice se usa con umbral bajo, orientado a **recuperar** (que el fragmento
correcto esté entre los candidatos). El modelo hace de juez: se le entrega la
pregunta y los fragmentos, y se le exige responder **solo** con lo que esté ahí
o declarar que no está. Es la misma regla que rige el resto del sistema — el
modelo decide, el código produce — aplicada a la pertinencia.

Cada afirmación va con su cita, porque una respuesta clínica sin fuente no es
verificable, y una respuesta inventada con aspecto de fundamentada es peor que
un «no sé».
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field

from django.conf import settings

from .rag_index import RagError, Resultado, indice
from .rag_sugerencias import Sugerencia, sugerir

# Umbral de RECUPERACIÓN, no de decisión: se quiere que el fragmento correcto
# entre entre los candidatos aunque venga acompañado de ruido. Quien descarta
# el ruido es el modelo, no este número (ver docstring).
UMBRAL_RECUPERACION = 0.50
# Menos candidatos y más cortos. Medido: con 5 fragmentos de 2.000 caracteres
# (~10.000 de contexto) un modelo de 3B en CPU tardaba 420-671 s por pregunta y
# se abstenía en 11 de 12 preguntas que SÍ estaban cubiertas — se ahogaba en el
# ruido en vez de encontrar la respuesta.
CANDIDATOS = 3
MAX_CHARS_FRAGMENTO = 900
# El juez sigue viendo 3 —más lo ahogaban—, pero la búsqueda trae más vecinos
# porque las sugerencias (paso 6) los aprovechan. No cuesta nada: la consulta
# ya está embebida y el producto matriz-vector ya está hecho; solo se conservan
# más filas del mismo ranking. Con 3 pasaba que los tres eran del mismo
# documento y solo se podía sugerir un sitio.
VECINOS = 8

SYSTEM_PROMPT = (
    'Eres un asistente documental de un laboratorio de citogenética. '
    'Respondes ÚNICAMENTE con lo que digan los fragmentos que se te entregan.\n\n'
    # Este prompt se midió dos veces. La primera versión decía «ante la duda,
    # responde=false» y el modelo se abstuvo en 11 de 12 preguntas que SÍ
    # estaban cubiertas: acierto global 39%, peor que no tener juez (56%).
    # Ahora la instrucción por defecto es RESPONDER, y abstenerse es la
    # excepción acotada a categorías concretas.
    'CÓMO DECIDIR:\n'
    '1. Si los fragmentos contienen la información —aunque sea parcial o haya '
    'que resumirla— devuelve responde=true y respóndela. Ese es el caso normal.\n'
    '2. Devuelve responde=false SOLO cuando los fragmentos traten de algo '
    'claramente distinto a lo que se pregunta: personas concretas, teléfonos, '
    'precios, presupuestos, inventario, agenda o compras.\n'
    '3. NO uses conocimiento propio: si no está en los fragmentos, no existe.\n'
    '4. En `fuentes` cita los números de los fragmentos que usaste, y solo esos.\n'
    '5. Sé breve y concreto. Registro técnico, sin adornos.'
)

RESPUESTA_SCHEMA = {
    'type': 'json_schema',
    'json_schema': {
        'name': 'respuesta_documental',
        'strict': True,
        'schema': {
            'type': 'object',
            'properties': {
                'responde': {
                    'type': 'boolean',
                    'description': 'true solo si los fragmentos contienen la respuesta',
                },
                'respuesta': {
                    'type': 'string',
                    'description': 'La respuesta, o cadena vacía si responde=false.',
                },
                'fuentes': {
                    'type': 'array',
                    'items': {'type': 'integer'},
                    'description': 'Números de los fragmentos usados.',
                },
            },
            'required': ['responde', 'respuesta', 'fuentes'],
            'additionalProperties': False,
        },
    },
}


@dataclass
class RespuestaRag:
    """Lo que el RAG devuelve, con la traza de cómo llegó."""

    responde: bool
    texto: str
    citas: list[Resultado] = field(default_factory=list)
    candidatos: list[Resultado] = field(default_factory=list)
    # Los que se recuperaron pero NO se le dieron al juez. Solo alimentan las
    # sugerencias; nunca la respuesta, que se funda únicamente en `citas`.
    vecinos: list[Resultado] = field(default_factory=list)
    latency_ms: int = 0
    motivo: str = ''

    @property
    def sugerencias(self) -> list[Sugerencia]:
        """Dónde seguir mirando (paso 6). Se calcula sobre lo ya recuperado.

        Importa sobre todo cuando `responde` es False: sin esto, el «no sé» es
        un callejón sin salida y el usuario no sabe si reformular o rendirse.
        """
        return sugerir(self.candidatos + self.vecinos, self.citas,
                       respondio=self.responde)

    def as_dict(self) -> dict:
        return {
            'responde': self.responde,
            'texto': self.texto,
            'citas': [{'fuente': r.fragmento.fuente,
                       'seccion': r.fragmento.seccion,
                       'similitud': r.porcentaje} for r in self.citas],
            'sugerencias': [s.as_dict() for s in self.sugerencias],
            'candidatos_evaluados': len(self.candidatos),
            'latency_ms': self.latency_ms,
            'motivo': self.motivo,
        }


def _bloque_fragmentos(candidatos: list[Resultado]) -> str:
    partes = []
    for n, r in enumerate(candidatos, 1):
        donde = r.fragmento.fuente
        if r.fragmento.seccion:
            donde += f' — {r.fragmento.seccion}'
        texto = r.fragmento.texto[:MAX_CHARS_FRAGMENTO]
        partes.append(f'[{n}] {donde} (similitud {r.porcentaje})\n{texto}')
    return '\n\n'.join(partes)


def responder_documental(pregunta: str) -> RespuestaRag:
    """Recupera candidatos y deja que el modelo decida si responden.

    Nunca lanza por culpa del modelo: si el LLM no está disponible se degrada a
    «no puedo responder» (RN-07), igual que el resto del sistema.
    """
    inicio = time.time()

    def cerrar(responde, texto, citas=(), candidatos=(), vecinos=(), motivo=''):
        return RespuestaRag(responde=responde, texto=texto, citas=list(citas),
                            candidatos=list(candidatos), vecinos=list(vecinos),
                            motivo=motivo,
                            latency_ms=int((time.time() - inicio) * 1000))

    if not (pregunta or '').strip():
        return cerrar(False, '', motivo='consulta vacía')

    try:
        recuperados = indice().buscar(pregunta, k=VECINOS,
                                      umbral=UMBRAL_RECUPERACION)
    except RagError as exc:
        return cerrar(False, '', motivo=f'índice no disponible: {exc}')

    if not recuperados:
        return cerrar(False, '', motivo='ningún fragmento supera el umbral de recuperación')

    candidatos, vecinos = recuperados[:CANDIDATOS], recuperados[CANDIDATOS:]

    if not getattr(settings, 'CLINIC_LLM_ENABLED', False):
        # Sin modelo no hay juez. Se prefiere no responder antes que volcar el
        # fragmento más parecido y dejar que el usuario decida si le vale.
        return cerrar(False, '', candidatos=candidatos, vecinos=vecinos,
                      motivo='IA desactivada: sin juez no se puede fundamentar')

    try:
        from openai import OpenAI
        cliente = OpenAI(
            base_url=getattr(settings, 'CLINIC_LLM_URL', 'http://localhost:11434/v1'),
            api_key='ollama',
            timeout=float(getattr(settings, 'CLINIC_LLM_TIMEOUT', 240.0)),
        )
        r = cliente.chat.completions.create(
            model=getattr(settings, 'CLINIC_LLM_MODEL', 'llama3.2:3b'),
            messages=[
                {'role': 'system', 'content': SYSTEM_PROMPT},
                {'role': 'user', 'content':
                    f'FRAGMENTOS:\n\n{_bloque_fragmentos(candidatos)}\n\n'
                    f'PREGUNTA: {pregunta}'},
            ],
            response_format=RESPUESTA_SCHEMA,
            temperature=0.0,
            max_tokens=500,
        )
        datos = json.loads(r.choices[0].message.content or '{}')
    except Exception as exc:                        # noqa: BLE001 — degradación
        return cerrar(False, '', candidatos=candidatos, vecinos=vecinos,
                      motivo=f'modelo no disponible: {exc}')

    if not datos.get('responde'):
        return cerrar(False, '', candidatos=candidatos, vecinos=vecinos,
                      motivo='el corpus no cubre la pregunta')

    # Las citas se resuelven contra los candidatos REALES: si el modelo cita un
    # número que no existe, se ignora en vez de inventar una fuente.
    citas = [candidatos[n - 1] for n in datos.get('fuentes', [])
             if isinstance(n, int) and 1 <= n <= len(candidatos)]
    return cerrar(True, (datos.get('respuesta') or '').strip(),
                  citas=citas or candidatos[:1], candidatos=candidatos,
                  vecinos=vecinos)
