"""Motor de nomenclatura ISCN — ADR-0023 D4, ADR-0025.

**Función pura**: recibe el conteo por clase y devuelve el string ISCN. Sin ORM,
sin I/O, sin estado. Mismo input → mismo output, siempre.

Esa pureza es lo que hace **auditable** el dato clínico, y es la razón por la que
ADR-0024 D1 prohíbe que lo produzca el LLM: `47,XY,+21` es un diagnóstico de
síndrome de Down. Un modelo generativo puede alucinar una trisomía; una función
determinística no.

Gramática soportada (ISCN 2024, subconjunto de ADR-0025 D4):

    <total>,<sexo>[,<anomalías numéricas en orden ascendente>]

    46,XX        femenino normal
    46,XY        masculino normal
    47,XY,+21    trisomía 21 (síndrome de Down)
    45,X         monosomía X (síndrome de Turner)
    47,XXY       Klinefelter — la copia extra va en el sexo, no como anomalía
    48,XXY,+21   Klinefelter + trisomía 21

Las anomalías **estructurales** (del, dup, t, inv) quedan fuera de alcance:
requieren bandeo y marcado por cromosoma, no solo conteo. El override manual del
Supervisor las cubre mientras tanto.
"""
from __future__ import annotations

import re

# Conteo esperado en un cariotipo humano normal: 2 copias de cada autosoma.
AUTOSOMAS = [str(n) for n in range(1, 23)]
COPIAS_NORMALES = 2

# Gramática para validar un override manual (ADR-0023 D4).
# Sexo: XX, XY, X, XXY, XXX, XYY... Anomalías: +N / -N, o estructurales.
_SEXO = r'(?:X{1,3}Y{0,2}|Y)'
_ANOMALIA = r'(?:[+-](?:\d{1,2}|X|Y)|(?:del|dup|inv|t|der|add|i|r)\([^)]+\))'
ISCN_RE = re.compile(rf'^\d{{2,3}},{_SEXO}(?:,{_ANOMALIA})*$')


class IscnError(ValueError):
    """El ISCN provisto no cumple la gramática (ADR-0023 D4)."""


def generate_iscn(counts: dict[str, int]) -> str:
    """Construye el ISCN a partir del conteo por clase.

    `counts` mapea clase ('1'..'22', 'X', 'Y') → número de cromosomas de esa
    clase en el caso, ya validado por el analista (las correcciones de P3 se
    reflejan en `predicted_class`, así que el conteo es el final).

    Lanza IscnError si el conteo está vacío: sin cromosomas no hay cariotipo que
    reportar, y devolver un '46,XX' por defecto sería inventar un diagnóstico.
    """
    counts = {k: int(v) for k, v in (counts or {}).items() if v}
    if not counts:
        raise IscnError('sin cromosomas: no hay cariotipo que reportar')

    total = sum(counts.values())
    sexo = _componente_sexual(counts.get('X', 0), counts.get('Y', 0))
    anomalias = _anomalias_numericas(counts)

    return ','.join([str(total), sexo, *anomalias])


def _componente_sexual(n_x: int, n_y: int) -> str:
    """Los cromosomas sexuales se escriben tal cual, NO como anomalía.

    Una copia extra de X se nota `47,XXY`, no `46,XY,+X`. Esa es la convención
    ISCN y la razón por la que este componente se construye aparte.
    """
    if n_x == 0 and n_y == 0:
        raise IscnError('sin cromosomas sexuales: el cariotipo está incompleto')
    return 'X' * n_x + 'Y' * n_y


def _anomalias_numericas(counts: dict[str, int]) -> list[str]:
    """Ganancias/pérdidas de autosomas, en orden numérico ascendente.

    El orden importa: ISCN exige `+18` antes de `+21` (ADR-0023 D4). Ordenar por
    el string daría '+21' antes de '+8', que es inválido.
    """
    anomalias = []
    for clase in AUTOSOMAS:                       # ya está en orden numérico
        delta = counts.get(clase, 0) - COPIAS_NORMALES
        if delta == 0:
            continue
        signo = '+' if delta > 0 else '-'
        anomalias.extend([f'{signo}{clase}'] * abs(delta))
    return anomalias


def validate_iscn(iscn: str) -> str:
    """Valida un ISCN escrito a mano (override del Supervisor, ADR-0023 D4).

    Se valida la **gramática**, no la plausibilidad clínica: el Supervisor es la
    autoridad médica y puede reportar hallazgos que el motor no sabe derivar del
    conteo (estructurales, mosaicismos). Lo que no se acepta es un string
    sintácticamente roto que después nadie pueda parsear.

    Devuelve el ISCN normalizado (sin espacios). Lanza IscnError si no cumple.
    """
    limpio = (iscn or '').strip().replace(' ', '')
    if not limpio:
        raise IscnError('el ISCN no puede estar vacío')
    if not ISCN_RE.match(limpio):
        raise IscnError(f'no cumple la gramática ISCN: {iscn!r}')

    # Coherencia interna: el total declarado debe ser un número plausible.
    total = int(limpio.split(',')[0])
    if not 20 <= total <= 200:
        raise IscnError(f'recuento fuera de rango biológico: {total}')
    return limpio
