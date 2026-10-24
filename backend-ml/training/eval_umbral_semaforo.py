"""¿El umbral de 0.85 del semáforo separa aciertos de errores?

    python training/eval_umbral_semaforo.py [--casos 30]

## Por qué esta pregunta

RN-02 pinta de naranja todo cromosoma con confianza < 0.85 y bloquea la emisión
del informe. Todo el coste de corrección medido (34 de 64 acciones son resolver
naranjas) sale de ese número. Pero el número nunca se validó: se eligió.

En el RAG ya se midió lo análogo y salió que **el umbral de similitud no
discriminaba** —los rangos de acierto y fallo se solapaban— y por eso decide un
juez. Esta es la misma pregunta aplicada a la visión:

    de los cromosomas que el modelo clasifica MAL, ¿cuántos están en naranja?
    de los que clasifica BIEN, ¿cuántos están en naranja sin necesidad?

Si el umbral discrimina, los errores caen casi todos por debajo y los aciertos
casi todos por encima. Si no, el semáforo está mandando a revisión trabajo que
no hacía falta y dejando pasar errores en verde — que es lo grave.

## Cómo se mide

Solo cariogramas de la partición de VALIDACIÓN del cuaderno v3 (semilla 42,
15 % por cariograma): el modelo no los vio al entrenar. Se usan los recortes
del experto, donde la clase verdadera se conoce; sobre la metafase no hay con
qué parear (ver `eval_dos_caminos.py`).

Salida en ASCII puro (la consola de Windows rompe con Unicode).
"""
import argparse
import statistics
import sys
import time
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / 'backend-ml'))
sys.path.insert(0, str(Path(__file__).resolve().parent))

UMBRAL = 0.85
METAFASES = RAIZ / 'datasets' / 'metaclass' / 'metafases'


def predicciones(clf, recortes):
    """Devuelve [(confianza, acierto)] para los recortes de un caso."""
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
        probs = torch.softmax(clf._model(lote), dim=1)
        conf, idx = probs.max(dim=1)

    return [(float(c), clf.classes[int(i)] == v)
            for c, i, v in zip(conf.tolist(), idx.tolist(), verdades)]


def franja(titulo, valores):
    if not valores:
        return '  %-22s (ninguno)' % titulo
    return ('  %-22s n=%-5d min %.3f | p25 %.3f | mediana %.3f | p75 %.3f | max %.3f'
            % (titulo, len(valores), min(valores),
               np.percentile(valores, 25), statistics.median(valores),
               np.percentile(valores, 75), max(valores)))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--casos', type=int, default=30)
    opts = ap.parse_args()

    from eval_dos_caminos import casos_de_validacion

    from app.efficientnet import EfficientNetClassifier
    clf = EfficientNetClassifier()
    if not clf.is_trained:
        print('no hay modelo entrenado', file=sys.stderr)
        return 1
    print('modelo:', clf.name)

    por_grupo, elegibles = casos_de_validacion()
    elegidos = elegibles[:opts.casos]
    print('casos de VALIDACION medidos: %d\n' % len(elegidos))

    datos = []
    for g in elegidos:
        datos += predicciones(clf, por_grupo[g])

    aciertos = [c for c, ok in datos if ok]
    errores = [c for c, ok in datos if not ok]
    n = len(datos)

    print('=' * 74)
    print('DISTRIBUCION DE CONFIANZA')
    print('=' * 74)
    print(franja('aciertos', aciertos))
    print(franja('errores', errores))
    print()

    # Lo que de verdad importa: la matriz del semaforo contra la verdad.
    vp = sum(1 for c, ok in datos if not ok and c < UMBRAL)   # error, va a revision  -> BIEN
    fn = sum(1 for c, ok in datos if not ok and c >= UMBRAL)  # error, pasa en verde  -> GRAVE
    fp = sum(1 for c, ok in datos if ok and c < UMBRAL)       # acierto a revision    -> trabajo de mas
    vn = sum(1 for c, ok in datos if ok and c >= UMBRAL)      # acierto en verde      -> BIEN

    print('=' * 74)
    print('QUE HACE EL UMBRAL DE %.2f  (n=%d)' % (UMBRAL, n))
    print('=' * 74)
    print('                      | naranja (<0.85)   | verde (>=0.85)')
    print('  --------------------+-------------------+------------------')
    print('  el modelo ACIERTA   | %5d  revision de | %5d  correcto' % (fp, vn))
    print('                      |        mas        |')
    print('  el modelo FALLA     | %5d  bien cazado | %5d  ERROR EN VERDE' % (vp, fn))
    print()

    total_err = vp + fn
    total_ok = fp + vn
    print('  errores cazados por el semaforo : %d/%d (%.1f%%)'
          % (vp, total_err, 100 * vp / max(1, total_err)))
    print('  ERRORES QUE PASAN EN VERDE      : %d/%d (%.1f%%)  <- los que nadie revisa'
          % (fn, total_err, 100 * fn / max(1, total_err)))
    print('  aciertos mandados a revision    : %d/%d (%.1f%%)  <- trabajo evitable'
          % (fp, total_ok, 100 * fp / max(1, total_ok)))
    print()
    print('  de todo lo que se manda a revision, es error el %.1f%%'
          % (100 * vp / max(1, vp + fp)))
    print('  (si fuera azar puro seria el %.1f%%, la tasa de error global)'
          % (100 * total_err / max(1, n)))

    # ¿Existe algun umbral mejor? Se busca el que maximiza (errores cazados -
    # aciertos molestados), que es el criterio honesto: cada punto de revision
    # cuesta trabajo humano.
    print()
    print('=' * 74)
    print('BARRIDO DE UMBRALES')
    print('=' * 74)
    print('  umbral | errores cazados | aciertos molestados | precision del naranja')
    print('  -------+-----------------+---------------------+----------------------')
    for u in (0.50, 0.60, 0.70, 0.80, 0.85, 0.90, 0.95, 0.99):
        c_err = sum(1 for c, ok in datos if not ok and c < u)
        c_ok = sum(1 for c, ok in datos if ok and c < u)
        prec = 100 * c_err / max(1, c_err + c_ok)
        marca = '  <- actual' if abs(u - UMBRAL) < 1e-9 else ''
        print('   %.2f  | %5d (%5.1f%%) | %6d (%5.1f%%)      | %5.1f%%%s'
              % (u, c_err, 100 * c_err / max(1, total_err),
                 c_ok, 100 * c_ok / max(1, total_ok), prec, marca))

    return 0


if __name__ == '__main__':
    t0 = time.time()
    codigo = main()
    print('\n(%.0fs)' % (time.time() - t0))
    raise SystemExit(codigo)
