"""Corpus clínico que fundamenta la narrativa asistida — ADR-0028.

ADR-0024 documentó una alucinación **medida**: el modelo describió la trisomía
21 como «una deficiencia crónica y progresiva de la función cerebral»,
clínicamente falso. La validación no lo detectó porque solo verifica coherencia
citogenética, no corrección médica de la prosa.

La causa es que el modelo redacta desde su memoria de entrenamiento. Este módulo
le da material verificado sobre el que redactar.

## Búsqueda por clave, no vectorial (ADR-0028 D1)

El ISCN llega como dato **estructurado que el propio sistema generó**. Para
hallar el contexto de `47,XY,+21` se lee la entrada `+21`: coincidencia exacta,
100% de precisión y trazabilidad — se puede probar qué entrada fundamentó cada
informe. La medición de ADR-0027 mostró que la similitud vectorial rinde ~60% en
este dominio; acá la clave ya existe, así que solo agregaría imprecisión.

## ⚠️ Las entradas semilla NO están revisadas por un clínico

Fueron redactadas por un asistente de IA desde conocimiento citogenético
general. Un error acá sería **peor** que la alucinación que este módulo combate:
entraría al sistema con apariencia de autoridad verificada.

Por eso `revisado_por` no es decorativo — la auditoría registra cuántas entradas
sin revisar fundamentaron cada informe, para poder rehacerlo si alguna resulta
incorrecta. Hasta que un profesional las firme, esa deuda es visible por caso.
"""
from __future__ import annotations

from dataclasses import dataclass

from .iscn import descomponer


@dataclass(frozen=True)
class EntradaCorpus:
    """Un hallazgo citogenético con su descripción verificable.

    `fuente` cita dónde se sostiene el dato. `revisado_por`/`revisado_el` marcan
    si un profesional lo validó: `None` significa **pendiente de revisión**, y
    ese estado viaja hasta el evento de auditoría.
    """

    clave: str
    nombre: str
    descripcion: str
    fuente: str
    revisado_por: str | None = None
    revisado_el: str | None = None

    @property
    def revisada(self) -> bool:
        return bool(self.revisado_por)


def _e(clave, nombre, descripcion, fuente):
    """Atajo para las entradas semilla — todas nacen SIN revisar (D2)."""
    return EntradaCorpus(clave=clave, nombre=nombre, descripcion=descripcion,
                         fuente=fuente, revisado_por=None, revisado_el=None)


# --- Aneuploidías autosómicas -----------------------------------------------
# Descripciones deliberadamente DESCRIPTIVAS, no pronósticas: el prompt del
# sistema prohíbe al modelo emitir pronóstico, y darle material pronóstico lo
# empujaría justo hacia lo prohibido.

_AUTOSOMICAS = [
    _e('+21', 'Trisomía 21',
       'Presencia de tres copias del cromosoma 21 en lugar de dos. Es la '
       'aneuploidía autosómica más frecuente compatible con la vida y '
       'corresponde al síndrome de Down.',
       'ISCN 2024 §5.3.2 i (nomenclatura); citogenética clínica general'),
    _e('+18', 'Trisomía 18',
       'Tres copias del cromosoma 18. Corresponde al síndrome de Edwards.',
       'ISCN 2024 §5.3.2 (nomenclatura); citogenética clínica general'),
    _e('+13', 'Trisomía 13',
       'Tres copias del cromosoma 13. Corresponde al síndrome de Patau.',
       'ISCN 2024 §5.3.2 (nomenclatura); citogenética clínica general'),
    _e('+8', 'Trisomía 8',
       'Tres copias del cromosoma 8. En estudios constitucionales suele '
       'presentarse en mosaico; también aparece como alteración adquirida en '
       'neoplasias hematológicas.',
       'ISCN 2024 §5.3.2 vii; citogenética clínica general'),
    _e('-21', 'Monosomía 21',
       'Una sola copia del cromosoma 21.',
       'ISCN 2024 §5.3.2 (nomenclatura)'),
    _e('-22', 'Monosomía 22',
       'Una sola copia del cromosoma 22.',
       'ISCN 2024 §5.3.2 iii (nomenclatura)'),
    _e('-7', 'Monosomía 7',
       'Pérdida de un cromosoma 7. Se observa con frecuencia como alteración '
       'adquirida en neoplasias mieloides.',
       'ISCN 2024 §6 (neoplasia); citogenética clínica general'),
]

# --- Complementos sexuales ---------------------------------------------------
# Se indexan por el complemento completo porque ISCN §5.1 f los escribe tal
# cual, nunca como anomalía con signo: la clave de `47,XXY` es «XXY», no «+X».

_SEXUALES = [
    _e('X', 'Monosomía X',
       'Un único cromosoma sexual X, sin segundo X ni Y. Corresponde al '
       'síndrome de Turner.',
       'ISCN 2024 §5.3.1.1 i (nomenclatura); citogenética clínica general'),
    _e('XXY', 'Complemento XXY',
       'Dos cromosomas X y un Y. Corresponde al síndrome de Klinefelter. '
       'La copia adicional se escribe dentro del complemento sexual, no como '
       'anomalía numérica.',
       'ISCN 2024 §5.3.1.1 y §5.1 f; citogenética clínica general'),
    _e('XXX', 'Trisomía X',
       'Tres cromosomas X. Frecuentemente cursa sin hallazgos clínicos '
       'llamativos y puede detectarse de forma incidental.',
       'ISCN 2024 §5.3.1.1 ii; citogenética clínica general'),
    _e('XYY', 'Complemento XYY',
       'Un cromosoma X y dos Y. Suele cursar sin hallazgos clínicos '
       'llamativos.',
       'ISCN 2024 §5.3.1.1 iii; citogenética clínica general'),
    _e('XXXY', 'Complemento XXXY',
       'Tres cromosomas X y un Y — una variante de las aneuploidías de los '
       'cromosomas sexuales.',
       'ISCN 2024 §5.3.1.1 iv'),
]

# --- Complementos normales ---------------------------------------------------
# Están en el corpus a propósito: sin una entrada para el caso normal, el modelo
# redacta el resultado más frecuente sin ningún anclaje.

_NORMALES = [
    _e('XX', 'Complemento femenino normal',
       'Dos cromosomas X. Complemento sexual femenino sin alteraciones '
       'numéricas.',
       'ISCN 2024 §5.2 i'),
    _e('XY', 'Complemento masculino normal',
       'Un cromosoma X y un Y. Complemento sexual masculino sin alteraciones '
       'numéricas.',
       'ISCN 2024 §5.2 ii'),
    _e('U', 'Complemento sexual no revelado',
       'El resultado no revela los cromosomas sexuales. «U» los reemplaza '
       'cuando no procede informarlos.',
       'ISCN 2024 §5.2 iii'),
]

CORPUS: dict[str, EntradaCorpus] = {
    e.clave: e for e in (*_AUTOSOMICAS, *_SEXUALES, *_NORMALES)
}


def buscar_contexto(iscn: str) -> list[EntradaCorpus]:
    """Entradas que fundamentan las anomalías presentes en un ISCN.

    El complemento sexual va primero, siguiendo el mismo orden en que ISCN §4.3
    escribe las alteraciones: sexuales antes que autosómicas.

    Devuelve `[]` cuando no hay coincidencias. **El corpus no es exhaustivo y no
    debe pretenderlo** (ADR-0028 D3): ante un hallazgo sin entrada la narrativa
    se genera igual, con menos fundamento. Bloquearla convertiría un vacío
    documental en un fallo clínico, y RN-07 lo prohíbe.
    """
    sexo, anomalias = descomponer(iscn)

    encontradas: list[EntradaCorpus] = []
    if sexo and sexo in CORPUS:
        encontradas.append(CORPUS[sexo])
    for anomalia in anomalias:
        entrada = CORPUS.get(anomalia)
        # Una anomalía repetida (tetrasomía: «+21,+21») no duplica el contexto.
        if entrada and entrada not in encontradas:
            encontradas.append(entrada)
    return encontradas


def formatear_para_prompt(entradas: list[EntradaCorpus]) -> str:
    """Bloque de referencia para el prompt. Cadena vacía si no hay entradas.

    Se rotula como material de referencia y no como texto a copiar: el modelo
    debe redactar SOBRE él (ADR-0028 D3), no devolverlo.
    """
    if not entradas:
        return ''
    lineas = ['REFERENCIA CLÍNICA VERIFICADA (redacta apoyándote en esto, '
              'no lo copies literalmente):']
    lineas += [f'- {e.nombre}: {e.descripcion}' for e in entradas]
    return '\n'.join(lineas)


def resumen_auditoria(entradas: list[EntradaCorpus]) -> dict:
    """Qué fundamentó el informe, para el evento de auditoría (ADR-0028 D2).

    `sin_revisar` es el dato que importa: identifica los informes apoyados en
    material que ningún profesional firmó todavía, para poder rehacerlos si una
    entrada resulta incorrecta.
    """
    return {
        'corpus_entradas': [e.clave for e in entradas],
        'corpus_sin_revisar': sum(1 for e in entradas if not e.revisada),
    }
