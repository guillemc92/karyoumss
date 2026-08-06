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

# --- Gramática del override manual (ISCN 2024, cap. 4 y 5) ---
#
# Se valida por DESCOMPOSICIÓN, no con una expresión regular monolítica: el
# ISCN es un lenguaje con estructura (líneas celulares → recuento, sexo,
# anomalías) y una regex única sería ilegible y —como ya ocurrió— demasiado
# estrecha sin que nadie lo note.
#
# Lo que se valida es la FORMA. La autoridad médica es el Supervisor: puede
# reportar hallazgos que el motor no deriva del conteo. Un falso rechazo le
# bloquea trabajo legítimo, así que ante la duda se acepta.

# Prefijos de línea celular (ISCN §4.5.3): mosaico y quimera.
_PREFIJOS = ('mos ', 'chi ')

# Complemento sexual: 'U' = no revelado (§5.2); combinaciones X/Y (§5.3.1.1);
# vacío cuando ambos sexuales están en un reordenamiento (§5.5.18.1.1 iv).
_SEXO_RE = re.compile(r'^(?:U|X{1,4}Y{0,3}|Y)?$')

# Recuento: 46, o un rango con tilde para clones (§4.2.1.j) — «45~48».
_RECUENTO_RE = re.compile(r'^\d{2,3}(?:~\d{2,3})?$')

# Sufijos de origen/herencia (§3, §4.2.1): constitucional, materno, paterno,
# de novo, heredado, y las formas derivadas (parcialmente heredado).
_SUFIJOS = r'(?:c|mat|pat|dn|inh|dmat|dpat|dinh)?'

# Una anomalía = [signo] [?] cuerpo [sufijo] [xN].
#   signo   + / -  ganancia o pérdida (§5.1 f)
#   ?       identificación dudosa (§4.2.1 k): «+?8», «?del(1)(p36.1)»
#   cuerpo  un átomo numérico o una expresión estructural
#   xN      copias múltiples de un reordenamiento (§5.6)
#
# El signo puede preceder a una estructura completa: «+der(5)t(2;5)(q21;q31)»
# es la ganancia de un cromosoma derivado supernumerario (§5.5.3, tabla 5).

# Átomos que pueden ganarse o perderse sin ser una estructura.
_ATOMO = r'(?:\d{1,2}|X|Y|mar\d*|r\d*|dmin|ace|min)'

# Abreviaturas de reordenamiento estructural (§3).
# El orden importa: las compuestas van primero para que la alternancia no
# corte 'psu dic' en 'psu'. Llevan espacio interno obligatorio (§4.4.1 b).
_ABREV = (r'psu dic|psu idic|psu trc|dic r|trc r|'
          r'del|dup|inv|ins|der|add|dic|idic|trc|psu|rob|rec|fra|hsr|tas|'
          r'trp|qdp|neo|fis|sce|ider|mar|min|cht|chr|ace|dmin|[tir]')

# Una estructura es una o más abreviaturas encadenadas, cada una con su
# cromosoma y, opcionalmente, sus puntos de rotura — que no se repiten al
# volver a citar la anomalía (§4.2.1 f).
_ESTRUCTURA = rf'(?:\??(?:{_ABREV})\([^()]*\)(?:\([^()]*\))?)+'

_ANOMALIA_RE = re.compile(
    rf'^[+-]?\??(?:{_ESTRUCTURA}|{_ATOMO})'
    rf'{_SUFIJOS}(?:\s?(?:{_SUFIJOS}))?(?:[x×]\d+)?$',
    re.IGNORECASE,
)

# Recuento de metafases: [20] o el compuesto [cp10] (§6.3.5).
_CORCHETE_RE = re.compile(r'\[(?:cp)?\d+\]$')

_RECUENTO_MIN, _RECUENTO_MAX = 20, 200


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


def _valida_anomalia(token: str) -> None:
    """Una anomalía es numérica (+21) o estructural (del(5)(q13)). Nada más."""
    if not token:
        raise IscnError('hay una coma sin anomalía detrás')
    if _ANOMALIA_RE.match(token):
        return
    raise IscnError(f'anomalía no reconocida: {token!r}')


def _valida_linea_celular(linea: str) -> None:
    """Una línea celular es: recuento, sexo [, anomalía]* [recuento de células].

    ISCN §4.2.1: el número de cromosomas va primero, luego el complemento
    sexual, y después las anomalías — todo separado por comas sin espacios.
    """
    linea = _CORCHETE_RE.sub('', linea)      # [20] / [cp10] son opcionales
    if not linea:
        raise IscnError('línea celular vacía')

    partes = linea.split(',')
    if len(partes) < 2:
        raise IscnError(f'falta el complemento sexual en {linea!r}')

    recuento, sexo, anomalias = partes[0], partes[1], partes[2:]

    if not _RECUENTO_RE.match(recuento):
        raise IscnError(f'recuento inválido: {recuento!r}')
    # El límite biológico se aplica al extremo inferior de un rango.
    total = int(recuento.split('~')[0])
    if not _RECUENTO_MIN <= total <= _RECUENTO_MAX:
        raise IscnError(f'recuento fuera de rango biológico: {total}')

    # El sexo puede venir vacío cuando ambos sexuales están reordenados
    # (§5.5.18.1.1 iv: «46,t(X;18)(p11.2;q11.2),t(Y;1)...»), y en ese caso el
    # token es en realidad la primera anomalía.
    if not _SEXO_RE.match(sexo):
        _valida_anomalia(sexo)

    for anomalia in anomalias:
        _valida_anomalia(anomalia)


def validate_iscn(iscn: str) -> str:
    """Valida un ISCN escrito a mano (override del Supervisor, ADR-0023 D4).

    Se valida la **gramática**, no la plausibilidad clínica: el Supervisor es la
    autoridad médica y puede reportar hallazgos que el motor no sabe derivar del
    conteo. Lo que no se acepta es un string sintácticamente roto que después
    nadie pueda parsear.

    Cubre lo que el estándar ISCN 2024 admite en el formato de cariotipo:
    mosaicismo y quimerismo (`mos`/`chi`, líneas separadas por `/`), sexo no
    revelado (`U`), reordenamientos estructurales con sus puntos de rotura,
    sufijos de herencia (`mat`, `pat`, `dn`, `c`…) y recuentos de metafases.

    Devuelve el ISCN normalizado (sin espacios internos). Lanza IscnError.
    """
    texto = (iscn or '').strip()
    if not texto:
        raise IscnError('el ISCN no puede estar vacío')

    # El prefijo mos/chi lleva espacio obligatorio (§4.4.1 c); se conserva.
    prefijo = ''
    for p in _PREFIJOS:
        if texto.lower().startswith(p):
            prefijo, texto = texto[:len(p)].lower(), texto[len(p):]
            break

    # §4.4.1: el espacio es SIGNIFICATIVO en ISCN («psu dic», «+mar c»).
    # Borrarlos todos corrompería el dato clínico, así que solo se normalizan
    # los adyacentes a separadores —donde §4.2.1 a los prohíbe— y los repetidos.
    limpio = re.sub(r'\s*([,/])\s*', lambda m: m.group(1), texto)
    limpio = re.sub(r'\s+', ' ', limpio).strip()
    if not limpio:
        raise IscnError('el ISCN no puede estar vacío')

    # `//` separa receptor de donante en quimeras post-trasplante (§4.5.3).
    for linea in re.split(r'/{1,2}', limpio):
        if linea:                              # `//46,XX[20]` deja un vacío
            _valida_linea_celular(linea)

    return prefijo + limpio
