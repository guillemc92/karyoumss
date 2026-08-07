"""Catálogo de herramientas consultables — tool calling (Módulo 6, semana 3).

**La regla que ordena todo este módulo: el modelo ELIGE la herramienta, el
código PRODUCE la respuesta.** El LLM nunca ve la base de datos, nunca redacta
un dato y nunca inventa un número. Recibe una pregunta y devuelve el nombre de
una herramienta; a partir de ahí corre Django ORM y nada más.

Es la misma separación que ya rige el ISCN (ADR-0024 D1: el LLM redacta pero no
calcula), aplicada ahora a las consultas.

## Los dos caminos

    pregunta ──> ¿coincide una palabra clave del catálogo?
                 │
                 ├── sí ──> KEYWORD: ejecuta la herramienta. NO llama al modelo.
                 │
                 └── no ──> LLM: el modelo elige entre las herramientas
                            publicadas. Si no encaja ninguna, dice que no sabe.

El camino KEYWORD existe porque la mayoría de las preguntas reales usan las
palabras del dominio. Resolverlas sin modelo es más rápido, más barato y —lo que
importa acá— **sigue funcionando con la IA apagada**.

## Procedencia

Cada resultado declara `tool` y `source` (la tabla real). Sin eso, un usuario no
puede distinguir un dato consultado de uno inventado, que es exactamente lo que
esta arquitectura busca hacer imposible.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from typing import Callable

from .models import CONFIDENCE_THRESHOLD, Chromosome, Sample, SampleStatus


@dataclass(frozen=True)
class ToolSpec:
    """Una herramienta publicada al modelo.

    `keywords` son las palabras del dominio que la resuelven **sin** modelo.
    `description` es lo único que el LLM ve para decidir: se escribe para él,
    no para un humano.
    """

    name: str
    description: str
    source: str                      # tabla real, para la procedencia
    keywords: tuple[str, ...]
    run: Callable[[], list[dict]] = field(compare=False, repr=False)


# ---------------------------------------------------------------------------
# Las consultas. Django ORM puro: ningún dato pasa por el modelo.
# ---------------------------------------------------------------------------

# Tope de filas por consulta. Una lista sin límite puede volcar miles de filas a
# la respuesta; 50 basta para una consulta conversacional.
#
# Que se trunque NO puede quedar callado: la respuesta dice «estos son los
# cromosomas que hay que revisar», y mostrar 50 de 100 sin avisar esconde la
# mitad de la cola de trabajo. El llamador compara `len(filas)` contra este tope
# para advertirlo (ver `_ejecutar` en tool_router).
LIMITE_FILAS = 50


def _muestras_por_estado(estado: str) -> list[dict]:
    filas = (
        Sample.objects.filter(status=estado, is_active=True)
        .order_by('-created_at')
        .values('chn_code', 'status', 'sample_type', 'created_at')[:LIMITE_FILAS]
    )
    return [
        {
            'chn_code': f['chn_code'],
            'estado': f['status'],
            'tipo_muestra': f['sample_type'] or '—',
            'creada': f['created_at'].strftime('%Y-%m-%d'),
        }
        for f in filas
    ]


def cromosomas_para_revision() -> list[dict]:
    """Cromosomas 'naranjas': confianza bajo el umbral, sin resolver (RN-02).

    Son los que el analista debe revisar a mano antes de validar el caso — el
    corazón del human-in-the-loop del sistema.
    """
    filas = (
        Chromosome.objects.filter(
            resolution_status='PENDING',
            is_active=True,
            confidence_score__lt=CONFIDENCE_THRESHOLD,
        )
        .select_related('karyotype__sample')
        .order_by('confidence_score')[:LIMITE_FILAS]
    )
    return [
        {
            'caso': c.karyotype.sample.chn_code,
            'clase': c.predicted_class,
            'confianza': f'{float(c.confidence_score) * 100:.1f}%' if c.confidence_score else '—',
            'estado': 'Pendiente de revisión',
        }
        for c in filas
    ]


def casos_pendientes_de_firma() -> list[dict]:
    """Casos validados por el analista, esperando al Supervisor (FSD-UC-005)."""
    return _muestras_por_estado(SampleStatus.ANALYST_VALIDATED)


def casos_reportados() -> list[dict]:
    """Casos cerrados: con nomenclatura ISCN emitida (S3)."""
    filas = (
        Sample.objects.filter(status=SampleStatus.REPORTED, is_active=True)
        .order_by('-iscn_generated_at')
        .values('chn_code', 'iscn_nomenclature', 'iscn_generated_at')[:LIMITE_FILAS]
    )
    return [
        {
            'chn_code': f['chn_code'],
            'iscn': f['iscn_nomenclature'] or '—',
            'reportado': f['iscn_generated_at'].strftime('%Y-%m-%d') if f['iscn_generated_at'] else '—',
        }
        for f in filas
    ]


def casos_en_proceso() -> list[dict]:
    """Muestras que el pipeline de IA todavía no terminó de procesar."""
    return _muestras_por_estado(SampleStatus.PROCESSING)


# ---------------------------------------------------------------------------
# El catálogo
# ---------------------------------------------------------------------------

CATALOGO: tuple[ToolSpec, ...] = (
    ToolSpec(
        name='CROMOSOMAS_PARA_REVISION',
        description=(
            'Lista CROMOSOMAS individuales marcados en naranja: los que se '
            'clasificaron con confianza por debajo del umbral (85%) y que el '
            'analista todavía no resolvió. Úsala para preguntas sobre qué '
            'cromosomas requieren revisión manual, están dudosos, mal '
            'clasificados o tienen baja confianza. '
            'NO sirve para saber en qué está trabajando el sistema ni qué '
            'casos están en cada etapa: esta herramienta baja al detalle de '
            'los cromosomas dentro de un caso.'
        ),
        source='clinic_chromosomes',
        keywords=('naranja', 'naranjas', 'baja confianza', 'sin resolver', 'pendiente de revision'),
        run=cromosomas_para_revision,
    ),
    ToolSpec(
        name='CASOS_PENDIENTES_FIRMA',
        description=(
            'Lista CASOS completos que el analista ya validó y que esperan la '
            'firma digital del Supervisor. Úsala para preguntas sobre qué casos '
            'esperan al supervisor, qué toca firmar o autorizar, qué está '
            'pendiente de firma, o qué está listo para la última revisión antes '
            'de emitir el informe. Es la última etapa antes de reportar.'
        ),
        source='clinic_samples',
        keywords=('pendiente de firma', 'esperando firma', 'validado por analista', 'sin firmar'),
        run=casos_pendientes_de_firma,
    ),
    ToolSpec(
        name='CASOS_REPORTADOS',
        description=(
            'Lista CASOS ya cerrados y firmados, con su nomenclatura ISCN '
            'emitida. Úsala para preguntas sobre casos terminados, reportados, '
            'entregados al médico solicitante, con resultado final o que ya '
            'completaron todo el proceso. Es la etapa final: aquí ya no queda '
            'nada por hacer.'
        ),
        source='clinic_samples',
        keywords=('reportado', 'reportados', 'con iscn', 'cerrado', 'cerrados'),
        run=casos_reportados,
    ),
    ToolSpec(
        name='CASOS_EN_PROCESO',
        description=(
            'Lista las muestras que el sistema está analizando AHORA MISMO: el '
            'pipeline todavía no termina con ellas. Úsala para preguntas sobre '
            'qué está corriendo, qué está procesando la máquina, en qué está '
            'trabajando el sistema, qué hay en la cola, o qué muestras todavía '
            'no terminan el análisis. Es el trabajo en curso, antes de que '
            'haya resultados que revisar.'
        ),
        source='clinic_samples',
        keywords=('en proceso', 'procesando', 'en cola'),
        run=casos_en_proceso,
    ),
)

POR_NOMBRE: dict[str, ToolSpec] = {t.name: t for t in CATALOGO}


def _normaliza(texto: str) -> str:
    """Minúsculas y sin acentos: «¿Por qué…?» debe casar con «por que»."""
    plano = unicodedata.normalize('NFKD', (texto or '').lower())
    return ''.join(c for c in plano if not unicodedata.combining(c))


# Los dos puntos ciegos de la coincidencia literal, medidos sobre el banco:
#
# 1. No sabe ABSTENERSE. «¿Qué significa que un cromosoma esté naranja?» contiene
#    «naranja» y devolvía la lista de cromosomas a una pregunta de documentación.
# 2. No ve la NEGACIÓN. «¿Qué estudios están validados pero NO cerrados?» dispara
#    con «cerrados» y devuelve justo lo contrario de lo que se pide.
#
# Ambos son inherentes al método, no defectos del catálogo: se detectan antes de
# tomar el atajo y se deja pasar la pregunta al modelo, que sí interpreta.

_PIDE_EXPLICACION = (
    'que significa', 'que quiere decir', 'por que', 'porque', 'como se ',
    'como funciona', 'para que sirve', 'quien puede', 'quien tiene permiso',
    'cuanto tarda', 'cuanto cuesta', 'que umbral', 'deberiamos', 'deberia',
)

# OJO: aquí NO puede ir « sin ». Es negación en castellano, pero también forma
# parte de dos claves del catálogo («sin resolver», «sin firmar»), así que
# incluirla desactiva el atajo para preguntas legítimas — y con la IA apagada
# esas preguntas pasarían a responder «no sé» en vez de dar los datos, que es
# exactamente la propiedad que el camino KEYWORD existe para garantizar.
_NIEGA = (' no ', ' excepto', ' salvo ', ' tampoco')


def _es_atajo_inseguro(texto: str) -> bool:
    """¿Tomar el atajo por palabra clave sería una trampa para esta pregunta?

    Una pregunta que pide una EXPLICACIÓN («qué significa…», «por qué…») o que
    NIEGA («validados pero no cerrados») no se puede resolver mirando si una
    cadena aparece: hace falta interpretarla. El atajo daría datos reales que no
    responden lo que se preguntó, que es peor que no responder.
    """
    return any(p in texto for p in _PIDE_EXPLICACION) or any(n in texto for n in _NIEGA)


def buscar_por_palabra_clave(pregunta: str) -> ToolSpec | None:
    """Resuelve por coincidencia literal, sin llamar al modelo.

    Se prefiere la palabra clave más larga que coincida: 'pendiente de revision'
    es más específico que 'pendiente' y debe ganar.

    Devuelve `None` —cediendo al modelo— cuando la pregunta pide explicación o
    niega: ver `_es_atajo_inseguro`.
    """
    texto = _normaliza(pregunta)
    if _es_atajo_inseguro(texto):
        return None
    mejor: tuple[int, ToolSpec] | None = None
    for tool in CATALOGO:
        for kw in tool.keywords:
            if kw in texto and (mejor is None or len(kw) > mejor[0]):
                mejor = (len(kw), tool)
    return mejor[1] if mejor else None


def catalogo_publicado() -> list[dict]:
    """Lo que el sistema declara saber responder.

    Se muestra cuando ninguna herramienta aplica: decir 'no sé' sin decir qué sí
    se sabe deja al usuario sin salida.
    """
    return [{'herramienta': t.name, 'responde': t.description, 'fuente': t.source} for t in CATALOGO]
