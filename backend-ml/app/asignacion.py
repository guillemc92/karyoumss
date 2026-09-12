"""Reparto global del cariotipo con cupos blandos — ADR-0033.

El clasificador mira cada recorte por separado. Un cariotipo, en cambio, tiene
estructura: **de cada autosoma hay dos copias**. Tomar el `argmax` de cada
cromosoma por su cuenta puede producir nueve cromosomas 1 y ningún 17, que es
biológicamente imposible.

Esa restricción es conocimiento del dominio, no del modelo. Aquí la aplica el
código: el modelo propone una distribución de probabilidad por cromosoma y este
módulo reparte las plazas al coste total mínimo.

## El cupo es BLANDO, y es la decisión que sostiene el módulo

Cada clase tiene `CUPO_LIBRE` plazas gratis y `PLAZAS_EXTRA` penalizadas. Un
cupo duro de dos copias haría el sistema incapaz de representar una trisomía
—es decir, incapaz de diagnosticar el síndrome de Down—, y además mide peor.

`PENALIZACION` está en unidades de `-log p`, así que 1.0 significa que una
tercera copia solo se acepta si es unas 2,7 veces más probable que colocar ese
cromosoma en otra parte. Medido sobre dos bancos disjuntos de la partición de
validación: +1,45 pp en el de ajuste y +1,22 pp en uno nuevo. No se eligió por
ser el máximo de ninguno de los dos —los máximos no coinciden— sino por ser el
valor estable; ver ADR-0033 §Medición.
"""
from __future__ import annotations

import numpy as np

#: Copias por clase que no pagan penalización (un cariotipo normal).
CUPO_LIBRE = 2
#: Copias adicionales posibles por clase, cada una más cara que la anterior.
PLAZAS_EXTRA = 2
#: Coste en -log p de cada copia por encima del cupo libre (ADR-0033 D3).
PENALIZACION = 1.0


def hungaro(coste: np.ndarray) -> np.ndarray:
    """Asignación de coste mínimo (Jonker-Volgenant). Requiere filas <= columnas.

    Se implementa aquí en vez de traer scipy: es una función, y backend-ml no
    necesita la dependencia. Misma regla del nivel mínimo que llevó a usar NumPy
    por fuerza bruta en el RAG (ADR-0029 D3).

    Devuelve, para cada fila, el índice de la columna que se le asignó.
    """
    n, m = coste.shape
    if n > m:
        raise ValueError('hacen falta al menos tantas plazas como cromosomas')

    INF = float('inf')
    u = np.zeros(n + 1)
    v = np.zeros(m + 1)
    p = np.zeros(m + 1, dtype=int)      # p[j] = fila asignada a la columna j
    camino = np.zeros(m + 1, dtype=int)

    for i in range(1, n + 1):
        p[0] = i
        j0 = 0
        minv = np.full(m + 1, INF)
        usada = np.zeros(m + 1, dtype=bool)
        while True:
            usada[j0] = True
            i0 = p[j0]
            delta = INF
            j1 = -1
            for j in range(1, m + 1):
                if usada[j]:
                    continue
                cur = coste[i0 - 1, j - 1] - u[i0] - v[j]
                if cur < minv[j]:
                    minv[j] = cur
                    camino[j] = j0
                if minv[j] < delta:
                    delta = minv[j]
                    j1 = j
            for j in range(m + 1):
                if usada[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while j0:
            j1 = camino[j0]
            p[j0] = p[j1]
            j0 = j1

    asignacion = np.zeros(n, dtype=int)
    for j in range(1, m + 1):
        if p[j] > 0:
            asignacion[p[j] - 1] = j - 1
    return asignacion


def _plazas(n_clases: int, penalizacion: float) -> list[tuple[int, float]]:
    """Columnas del problema: (clase, recargo). Las extra encarecen al crecer."""
    columnas: list[tuple[int, float]] = []
    for c in range(n_clases):
        columnas.extend((c, 0.0) for _ in range(CUPO_LIBRE))
        columnas.extend((c, penalizacion * (extra + 1)) for extra in range(PLAZAS_EXTRA))
    return columnas


def repartir(probs: np.ndarray, penalizacion: float = PENALIZACION) -> np.ndarray:
    """Índice de clase asignado a cada cromosoma, respetando los cupos.

    `probs` es (n_cromosomas x n_clases). Si hay más cromosomas que plazas —una
    metafase muy sobre-segmentada— no se puede repartir sin romper el cupo: se
    devuelve el `argmax`, que es exactamente el comportamiento previo. Degradar
    vale más que fallar (RN-07).
    """
    if probs.ndim != 2 or probs.shape[0] == 0:
        return probs.argmax(axis=1) if probs.size else np.empty(0, dtype=int)

    n, k = probs.shape
    columnas = _plazas(k, penalizacion)
    if n > len(columnas):
        return probs.argmax(axis=1)

    logp = -np.log(np.clip(probs, 1e-9, 1.0))
    coste = np.empty((n, len(columnas)))
    for j, (c, recargo) in enumerate(columnas):
        coste[:, j] = logp[:, c] + recargo

    eleccion = hungaro(coste)
    return np.array([columnas[j][0] for j in eleccion], dtype=int)
