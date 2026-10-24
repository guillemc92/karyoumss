"""Paso 6 del RAG: comparar los porcentajes de similitud y sugerir dónde mirar.

## Qué se midió antes de escribir esto, y qué salió

La consigna pide «comparar porcentajes de similitud para ofrecer la respuesta
más óptima y sugerencias apropiadas». La tentación es construir la sugerencia
sobre el puntaje: *si la similitud es alta, sugiere con confianza*. Se midió si
eso se sostiene, sobre el banco de 18 preguntas de `eval_rag` y el índice de
1.144 fragmentos:

    señal                cubiertas por corpus   fuera del corpus
    similitud top-1      0.601 – 0.695          0.608 – 0.662
    margen top1-top2     0.000 – 0.033          0.006 – 0.024
    dispersión del top-5 0.002 – 0.019          0.004 – 0.018

**Las tres se solapan.** En margen y dispersión el rango de las preguntas que
hay que rechazar queda *contenido dentro* del de las buenas: no hay corte
posible. El mejor umbral concebible sobre cualquiera de ellas acierta 67-72%,
por debajo del 89% que ya da el juez.

Y hay un segundo hallazgo, más útil que el primero: **los márgenes son
diminutos**. Los cinco candidatos llegan separados por milésimas, es decir,
prácticamente empatados. Eso desmonta la idea de «el fragmento más parecido es
la respuesta»: el top-1 no destaca sobre el top-5 lo suficiente como para que
la diferencia signifique algo.

## Qué se hace en consecuencia

Dos reglas de diseño, ambas consecuencia directa de lo medido:

1. **La respuesta más óptima la elige el juez, no el puntaje.** Este módulo no
   decide si el corpus responde — eso ya lo hace el modelo en `rag_qa`. Aquí
   solo se ordena y se reporta.

2. **Ninguna sugerencia afirma pertinencia.** Como el puntaje no predice si un
   fragmento responde, una sugerencia solo puede decir *«esto es lo más
   parecido que hay»*, nunca *«esto responde a tu pregunta»*. La redacción de
   `TITULOS` está escrita para no prometer lo que el número no respalda.

Como los candidatos vienen empatados, quedarse con el top-1 sería arbitrario:
se listan varios sitios distintos, que es lo que de verdad le sirve a quien
pregunta —dónde seguir leyendo—.

## Qué se agrupa en cada caso, y por qué no es lo mismo

Se probó contra el índice real y salió una diferencia que no se había previsto.
Al ampliar, el usuario ya sabe qué documento responde y lo útil es la
**sección**: otra parte del mismo ADR es una ampliación legítima. Al explorar,
en cambio, lo útil es el **documento**: preguntando por el teléfono de una
persona, las tres primeras sugerencias eran tres secciones del mismo ADR-0011 —
tres formas de decir lo mismo, ocupando el sitio de otros documentos que sí
podrían orientar. Por eso `explorar` agrupa por documento y `ampliar` por
sección.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Tres bastan: es una ayuda a la navegación, no un índice del corpus. Más
# sugerencias sobre candidatos empatados es ruido con aspecto de precisión.
MAX_SUGERENCIAS = 3

# `ampliar`  — el corpus respondió; esto es material contiguo no citado.
# `explorar` — el corpus NO respondió; esto es lo más cercano que existe.
TITULOS = {
    'ampliar': 'También hay material relacionado en:',
    'explorar': 'El corpus no cubre esa pregunta. Lo más parecido que contiene es:',
}


def seccion_legible(seccion: str) -> str:
    """La sección, sin la miga de pan ni los escapes de Markdown.

    El troceador guarda la jerarquía completa del encabezado
    (`4.2 FSD-UC-002 … > 4.3 FSD-UC-003 … > 5\\. Reglas de negocio ⚡🔧`). Eso
    sirve para embeber —da contexto al vector— pero como sugerencia es
    ilegible: lo que el usuario necesita es el último tramo, que es la sección
    de verdad.
    """
    if not seccion:
        return ''
    ultimo = seccion.split('>')[-1].strip()
    ultimo = re.sub(r'\\(.)', r'\1', ultimo)        # 5\. -> 5.
    return ultimo.strip()


@dataclass(frozen=True)
class Sugerencia:
    """Un sitio del corpus al que merece la pena ir, con cuánto se parecía."""

    tipo: str            # 'ampliar' | 'explorar'
    fuente: str
    seccion: str
    similitud: float

    @property
    def porcentaje(self) -> str:
        return f'{self.similitud * 100:.1f}%'

    @property
    def donde(self) -> str:
        return f'{self.fuente} — {self.seccion}' if self.seccion else self.fuente

    def as_dict(self) -> dict:
        return {'tipo': self.tipo, 'documento': self.fuente,
                'seccion': self.seccion or '—', 'similitud': self.porcentaje}


def sugerir(candidatos, citas=(), respondio: bool = False) -> list[Sugerencia]:
    """Compara los candidatos recuperados y devuelve dónde seguir mirando.

    `candidatos` y `citas` son `Resultado` de `rag_index`. Función pura: no
    consulta el índice ni el modelo, solo ordena lo que ya se recuperó.

    Cuando el corpus **sí** respondió, se sugiere lo recuperado que no se citó
    —repetir la cita no aporta—. Cuando **no** respondió, se sugiere todo,
    porque ahí no hay ninguna cita y la alternativa sería un callejón sin
    salida.
    """
    if not candidatos:
        return []

    respondio = bool(respondio)
    tipo = 'ampliar' if respondio else 'explorar'

    # Al ampliar interesa la sección; al explorar, el documento (ver docstring).
    def clave(r):
        return (r.fragmento.fuente, r.fragmento.seccion) if respondio else (r.fragmento.fuente,)

    # Lo ya citado se identifica por (documento, sección): otra sección del
    # mismo documento sigue siendo una ampliación legítima.
    citado = {(c.fragmento.fuente, c.fragmento.seccion) for c in citas}

    vistos: set[tuple] = set()
    fuera: list[Sugerencia] = []
    # De mayor a menor parecido. El orden importa aunque las diferencias sean
    # milésimas: es el único criterio disponible y hay que ser consistente.
    for r in sorted(candidatos, key=lambda x: -x.similitud):
        if (r.fragmento.fuente, r.fragmento.seccion) in citado:
            continue
        k = clave(r)
        if k in vistos:
            continue
        vistos.add(k)
        fuera.append(Sugerencia(tipo=tipo, fuente=r.fragmento.fuente,
                                seccion=seccion_legible(r.fragmento.seccion),
                                similitud=r.similitud))
        if len(fuera) == MAX_SUGERENCIAS:
            break
    return fuera


def texto(sugerencias: list[Sugerencia]) -> str:
    """Las sugerencias en una línea por sitio, listas para mostrar.

    Cadena vacía si no hay ninguna: quien la use no debe imprimir un
    encabezado huérfano.
    """
    if not sugerencias:
        return ''
    lineas = [TITULOS[sugerencias[0].tipo]]
    lineas += [f'  - {s.donde} ({s.porcentaje})' for s in sugerencias]
    return '\n'.join(lineas)
