"""«El modelo propone, el código decide» — aplicado a la visión.

    python training/eval_asignacion.py [--casos 30]

## La idea, que viene del nivel 2 del módulo

En el enrutador de consultas la regla es: el modelo ELIGE una herramienta y el
código PRODUCE la respuesta. El modelo nunca escribe el dato.

Hoy la capa clínica no respeta esa regla. El clasificador mira cada recorte por
separado y su `argmax` **es** el cariotipo: nadie comprueba después si el
conjunto tiene sentido. Y un cariotipo tiene una estructura durísima que el
clasificador desconoce por completo:

    de cada autosoma hay DOS copias, no siete ni cero

Clasificar 46 cromosomas de forma independiente puede producir «nueve
cromosomas 1 y ningún 17», que es biológicamente imposible. Esa restricción es
conocimiento del dominio, no del modelo: le toca al código.

## Qué se mide

    (a) argmax independiente          <- lo que hace hoy el sistema
    (b) asignación global con cupos   <- el modelo propone probabilidades,
                                         el código reparte respetando la
                                         estructura del cariotipo

Ambas sobre los MISMOS recortes y el MISMO modelo, en la partición de
validación del cuaderno v3 (el modelo no los vio al entrenar).

## Por qué el cupo es BLANDO y no duro

Un cupo duro de 2 haría el sistema incapaz de ver una trisomía — justo lo que
se busca diagnosticar. Aquí cada clase tiene 2 plazas libres y una tercera
PENALIZADA: la tercera copia es posible, pero el modelo tiene que sostenerla
con evidencia fuerte. Con penalización 0 se parece al argmax; con penalización
infinita sería el cupo duro que prohíbe el síndrome de Down.

Salida en ASCII puro (la consola de Windows rompe con Unicode).
"""
import argparse
import sys
import time
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / 'backend-ml'))
sys.path.insert(0, str(Path(__file__).resolve().parent))

CUPO_LIBRE = 2       # copias por clase que no pagan nada
PLAZAS_EXTRA = 2     # copias adicionales posibles, penalizadas


def hungaro(coste: np.ndarray) -> np.ndarray:
    """Asignación de coste mínimo (Jonker-Volgenant, O(n^2 m)). filas <= columnas.

    Se implementa aquí porque backend-ml no tiene scipy y no merece la pena
    añadirlo por una función. Devuelve, para cada fila, la columna asignada.
    """
    n, m = coste.shape
    assert n <= m, 'hacen falta al menos tantas plazas como cromosomas'
    INF = float('inf')
    u = np.zeros(n + 1)
    v = np.zeros(m + 1)
    p = np.zeros(m + 1, dtype=int)
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


def probabilidades(clf, recortes):
    """Matriz (n_cromosomas x n_clases) y la clase verdadera de cada uno."""
    from PIL import Image

    from app.preprocess import letterbox

    torch = clf._torch
    grises, verdades = [], []
    for ruta, cls in recortes:
        with Image.open(ruta) as im:
            grises.append(np.array(im.convert('L')))
        verdades.append(cls)

    ref_h = float(np.median([g.shape[0] for g in grises]))
    lote = torch.stack([clf._tf(letterbox(g, ref_h, canvas=clf._img_size)) for g in grises])
    with torch.no_grad():
        probs = torch.softmax(clf._model(lote), dim=1).cpu().numpy()
    return probs, verdades


def asignar(probs: np.ndarray, clases: list, penalizacion: float) -> list:
    """Reparte los cromosomas entre las plazas de cada clase, al coste mínimo."""
    n, k = probs.shape
    # Plazas: CUPO_LIBRE gratis + PLAZAS_EXTRA que pagan `penalizacion` cada una.
    columnas = []          # (indice_de_clase, recargo)
    for c in range(k):
        for _ in range(CUPO_LIBRE):
            columnas.append((c, 0.0))
        for extra in range(PLAZAS_EXTRA):
            columnas.append((c, penalizacion * (extra + 1)))

    coste = np.zeros((n, len(columnas)))
    logp = -np.log(np.clip(probs, 1e-9, 1.0))
    for j, (c, recargo) in enumerate(columnas):
        coste[:, j] = logp[:, c] + recargo

    eleccion = hungaro(coste)
    return [clases[columnas[j][0]] for j in eleccion]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--casos', type=int, default=30)
    ap.add_argument('--desde', type=int, default=0,
                    help='salta los N primeros casos; con --desde 30 se mide sobre '
                         'los que NO se usaron para ajustar la penalizacion')
    opts = ap.parse_args()

    from eval_dos_caminos import casos_de_validacion

    from app.efficientnet import EfficientNetClassifier
    clf = EfficientNetClassifier()
    if not clf.is_trained:
        print('no hay modelo entrenado', file=sys.stderr)
        return 1
    print('modelo:', clf.name)

    por_grupo, elegibles = casos_de_validacion()
    elegidos = elegibles[opts.desde:opts.desde + opts.casos]
    if opts.desde:
        print('BANCO NUEVO: casos %d..%d, sin solape con el de ajuste (0..%d)'
              % (opts.desde, opts.desde + len(elegidos) - 1, opts.desde - 1))
    print('casos de VALIDACION medidos: %d' % len(elegidos))
    print('cupo: %d plazas libres + %d penalizadas por clase\n' % (CUPO_LIBRE, PLAZAS_EXTRA))

    cacheado = []
    for g in elegidos:
        probs, verdades = probabilidades(clf, por_grupo[g])
        cacheado.append((probs, verdades))

    total = sum(len(v) for _, v in cacheado)

    # (a) lo que hace hoy el sistema
    ok_argmax = 0
    for probs, verdades in cacheado:
        pred = [clf.classes[i] for i in probs.argmax(axis=1)]
        ok_argmax += sum(1 for p, v in zip(pred, verdades) if p == v)

    print('=' * 74)
    print('(a) ARGMAX INDEPENDIENTE  — lo que hace hoy el sistema')
    print('=' * 74)
    print('    acierto: %d/%d = %.2f%%\n' % (ok_argmax, total, 100 * ok_argmax / total))

    print('=' * 74)
    print('(b) ASIGNACION GLOBAL CON CUPOS  — el codigo reparte')
    print('=' * 74)
    print('  penalizacion | acierto        | delta vs argmax')
    print('  -------------+----------------+-----------------')
    mejor = (None, -1)
    for pen in (0.0, 0.5, 1.0, 2.0, 4.0, 8.0, 100.0):
        ok = 0
        for probs, verdades in cacheado:
            pred = asignar(probs, clf.classes, pen)
            ok += sum(1 for p, v in zip(pred, verdades) if p == v)
        pct = 100 * ok / total
        delta = pct - 100 * ok_argmax / total
        etiqueta = 'cupo duro' if pen >= 100 else ('sin cupo' if pen == 0 else '')
        print('     %6.1f    | %5d  %6.2f%% | %+6.2f pp   %s' % (pen, ok, pct, delta, etiqueta))
        if pct > mejor[1]:
            mejor = (pen, pct)

    print()
    print('  mejor penalizacion: %.1f  ->  %.2f%%  (%+.2f pp sobre argmax)'
          % (mejor[0], mejor[1], mejor[1] - 100 * ok_argmax / total))
    print()
    print('  OJO: el cupo duro (100) prohibe la tercera copia, es decir, prohibe')
    print('  diagnosticar una trisomia. Si sale el mejor, es porque el banco de')
    print('  validacion son casi todos casos normales — NO es la configuracion')
    print('  que se debe llevar a produccion.')
    return 0


if __name__ == '__main__':
    t0 = time.time()
    codigo = main()
    print('\n(%.0fs)' % (time.time() - t0))
    raise SystemExit(codigo)
