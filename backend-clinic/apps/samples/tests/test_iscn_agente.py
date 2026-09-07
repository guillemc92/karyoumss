"""Ejercicio 1 del LabX — tests del motor ISCN generados por un agente, AUDITADOS.

    generados por  llama3.2:3b (local, sin red)
    coste          2.050 tokens de entrada, 359 de salida, 587 s
    devueltos      8 tests
    sobrevivieron  1

La copia intacta de lo que devolvio el modelo esta en
`docs/M7_UNIT_AGENTE/salida_agente/iscn_ronda1_crudo.py`. Este fichero contiene
solo lo que paso las tres preguntas de la auditoria, corregido; el detalle
test por test esta en `docs/M7_UNIT_AGENTE/README.md`.

## Por que sobrevivio uno solo

Siete de los ocho pedian casos que el fichero a mano YA cubria —y ahi la culpa
es del prompt, que listo como «ausentes» casos que estaban—. El octavo pedia
algo que de verdad faltaba, y aun asi vino con la entrada mal: `{'8': 3}` son
tres cromosomas, no un cariotipo con trisomia del 8.

Lo que el agente aporto fue **la idea del caso**. La entrada correcta, el valor
esperado y el nombre los puso la persona. Esa es la division del trabajo que el
modulo pide: el agente escribe, la persona decide.
"""
import pytest

from apps.samples.iscn import generate_iscn
from apps.samples.tests.test_iscn import _normal

pytestmark = pytest.mark.auditado


def test_trisomia_8_en_un_cariotipo_masculino_da_47_XY_mas_8():
    """Version auditada de `test_cariotipo_masculino_trisomia_8`.

    El agente escribio `counts = {'8': 3}` esperando `'47,XY,+8'`. Son dos
    errores en una linea: ese conteo son tres cromosomas —el motor lo rechaza
    por recuento fuera de rango biologico— y ademas no dice de que sexo es el
    cariotipo, asi que no habia forma de que saliera XY.

    Corregido: se parte de un cariotipo masculino normal y se le pone una copia
    de mas del 8. El caso NO estaba a mano (el parametrizado prueba `{'8': 3,
    '21': 1}` y `{'8': 4}`, pero no la trisomia 8 sola sobre XY), asi que el
    agente si aporto la idea.
    """
    counts = _normal('XY')
    counts['8'] = 3

    assert generate_iscn(counts) == '47,XY,+8'
