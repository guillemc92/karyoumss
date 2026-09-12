"""Reparto global del cariotipo con cupos blandos — ADR-0033.

Lo que estas pruebas fijan, por orden de importancia:

  1. El reparto NO prohibe una trisomia (D3). Es la razon de que el cupo sea
     blando: un sistema que no puede representar el sindrome de Down no sirve
     para lo que se construyo.
  2. El codigo corrige lo que el modelo no sabe: dos copias por autosoma.
  3. Degrada en vez de fallar cuando no hay plazas suficientes (RN-07).
"""
import numpy as np
import pytest

from app.asignacion import CUPO_LIBRE, PLAZAS_EXTRA, hungaro, repartir


def probs_de(filas: list[dict], n_clases: int) -> np.ndarray:
    """Construye la matriz de probabilidades desde {clase: prob} por cromosoma."""
    m = np.full((len(filas), n_clases), 0.001)
    for i, fila in enumerate(filas):
        for c, p in fila.items():
            m[i, c] = p
    return m / m.sum(axis=1, keepdims=True)


# --- el algoritmo ----------------------------------------------------------

def test_hungaro_encuentra_el_reparto_optimo():
    # La diagonal es barata; cualquier otra combinacion cuesta mas.
    coste = np.array([[1.0, 9.0, 9.0],
                      [9.0, 1.0, 9.0],
                      [9.0, 9.0, 1.0]])
    assert list(hungaro(coste)) == [0, 1, 2]


def test_hungaro_prefiere_el_total_sobre_la_avaricia():
    """El optimo global NO es quedarse con el minimo de cada fila."""
    # Si la fila 0 se queda su minimo (col 0), la fila 1 paga 10.
    coste = np.array([[1.0, 2.0],
                      [1.0, 10.0]])
    asignacion = list(hungaro(coste))
    assert asignacion == [1, 0]                      # coste total 3, no 11
    assert coste[0, asignacion[0]] + coste[1, asignacion[1]] == 3.0


def test_hungaro_admite_mas_columnas_que_filas():
    coste = np.array([[5.0, 1.0, 5.0]])
    assert list(hungaro(coste)) == [1]


def test_hungaro_rechaza_menos_plazas_que_cromosomas():
    with pytest.raises(ValueError):
        hungaro(np.zeros((3, 2)))


# --- la decision que sostiene el ADR ---------------------------------------

def test_no_prohibe_la_trisomia():
    """D3: con cupo BLANDO, tres copias siguen siendo posibles.

    Tres cromosomas que el modelo ve clarisimamente como clase 0. Un cupo duro
    de 2 mandaria el tercero a otra clase; el blando lo deja donde debe estar.
    """
    probs = probs_de([{0: 0.99}, {0: 0.99}, {0: 0.99}], n_clases=4)
    assert list(repartir(probs, penalizacion=1.0)) == [0, 0, 0]


def test_una_trisomia_debil_si_cede():
    """La tercera copia no es gratis: si el modelo duda, se reparte a otra parte.

    El tercer cromosoma esta casi empatado entre la clase 0 y la 1. La
    penalizacion de la 3a plaza inclina la balanza hacia la 1, que esta libre.
    """
    probs = probs_de([{0: 0.99}, {0: 0.99}, {0: 0.40, 1: 0.38}], n_clases=4)
    assert list(repartir(probs, penalizacion=1.0)) == [0, 0, 1]


def test_penalizacion_alta_se_comporta_como_cupo_duro():
    probs = probs_de([{0: 0.99}, {0: 0.99}, {0: 0.99, 1: 0.005}], n_clases=4)
    assert list(repartir(probs, penalizacion=1000.0)) == [0, 0, 1]


# --- lo que el codigo corrige y el modelo no sabe --------------------------

def test_corrige_el_exceso_de_copias_que_el_argmax_permite():
    """Cuatro cromosomas que el argmax mandaria todos a la clase 0."""
    probs = probs_de([
        {0: 0.90, 1: 0.05},
        {0: 0.85, 1: 0.10},
        {0: 0.60, 1: 0.35},
        {0: 0.55, 1: 0.40},
    ], n_clases=3)

    assert list(probs.argmax(axis=1)) == [0, 0, 0, 0]      # lo que hace hoy

    repartido = list(repartir(probs, penalizacion=1.0))
    assert repartido.count(0) == CUPO_LIBRE                 # el cupo se respeta
    # Ceden los dos que el modelo sostenia con menos fuerza, no dos cualesquiera.
    assert repartido[0] == 0 and repartido[1] == 0
    assert repartido[2] == 1 and repartido[3] == 1


def test_sin_penalizacion_coincide_con_el_argmax_cuando_no_hay_conflicto():
    probs = probs_de([{0: 0.9}, {1: 0.9}, {2: 0.9}], n_clases=3)
    assert list(repartir(probs, penalizacion=1.0)) == list(probs.argmax(axis=1))


# --- degradacion (RN-07) ---------------------------------------------------

def test_sin_plazas_suficientes_cae_al_argmax_en_vez_de_fallar():
    """Una metafase muy sobre-segmentada no puede repartirse sin romper el cupo."""
    n_clases = 2
    plazas = n_clases * (CUPO_LIBRE + PLAZAS_EXTRA)
    probs = probs_de([{0: 0.9}] * (plazas + 1), n_clases=n_clases)
    assert list(repartir(probs)) == list(probs.argmax(axis=1))


def test_sin_cromosomas_no_revienta():
    assert list(repartir(np.zeros((0, 5)))) == []
