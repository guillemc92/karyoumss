"""¿Qué le hace el reparto (ADR-0033) al semáforo, sobre metafases REALES?

    python training/eval_asignacion_metafase.py [--casos 8]

## Por qué hace falta esta medición

`eval_asignacion.py` midió la ganancia del reparto sobre los **recortes limpios
del experto**: +1,2 pp de acierto en datos no vistos. Pero el sistema en
producción no ve recortes limpios: ve lo que produce la segmentación sobre una
metafase cruda, que es mucho peor (ver `eval_dos_caminos.py`: la confianza media
cae de 0,746 a 0,509).

Al forzar la estructura del cariotipo sobre una distribución mala, muchos
cromosomas se mueven fuera de su `argmax`. Y como la confianza que se persiste
es la del modelo para la clase FINALMENTE elegida (ADR-0033 D4), moverlos
**baja la confianza**. Menos confianza significa más naranjas (RN-02), y más
naranjas significa más trabajo de revisión: justo lo que se intentaba reducir.

Aquí no se mide acierto —por el camino de la metafase no se puede, no hay con
qué parear— sino las dos cosas que sí se pueden observar:

  1. cuánto mejora la ESTRUCTURA (copias por clase imposibles)
  2. cuánto empeora el SEMÁFORO (naranjas que alguien tendrá que revisar)

Salida en ASCII puro (la consola de Windows rompe con Unicode).
"""
import argparse
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / 'backend-ml'))
sys.path.insert(0, str(Path(__file__).resolve().parent))

UMBRAL = 0.85
COPIAS_NORMALES = 2
METAFASES = RAIZ / 'datasets' / 'metaclass' / 'metafases'


def exceso(clases: list) -> int:
    """Copias por encima de 2 en cualquier clase: lo biológicamente imposible."""
    return sum(max(0, n - COPIAS_NORMALES) for n in Counter(clases).values())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--casos', type=int, default=8)
    opts = ap.parse_args()

    from eval_dos_caminos import casos_de_validacion

    from app.asignacion import PENALIZACION, repartir
    from app.efficientnet import EfficientNetClassifier
    from app.main import load_gray
    from app.segmentation import segment

    clf = EfficientNetClassifier()
    if not clf.is_trained:
        print('no hay modelo entrenado', file=sys.stderr)
        return 1
    print('modelo:', clf.name, '| penalizacion:', PENALIZACION)

    _, elegibles = casos_de_validacion()
    elegidos = elegibles[:opts.casos]
    print('metafases de VALIDACION medidas: %d\n' % len(elegidos))

    torch = clf._torch
    from app.preprocess import letterbox, reference_height

    tot = {'exceso_off': 0, 'exceso_on': 0, 'nar_off': 0, 'nar_on': 0, 'n': 0,
           'movidos': 0}
    conf_off_all, conf_on_all = [], []

    print('%-7s %-22s %-22s' % ('caso', 'ARGMAX (hoy)', 'REPARTO (ADR-0033)'))
    print('-' * 74)
    for g in elegidos:
        gray = load_gray((METAFASES / ('metafase_%s.bmp' % g)).read_bytes())
        det = segment(gray)
        if not det:
            continue
        ref_h = reference_height([d.bbox[3] for d in det])
        lote = torch.stack([
            clf._tf(letterbox(gray[y:y + h, x:x + w], ref_h, canvas=clf._img_size))
            for (x, y, w, h) in (d.bbox for d in det)])
        with torch.no_grad():
            probs = torch.softmax(clf._model(lote), dim=1).cpu().numpy()

        idx_off = probs.argmax(axis=1)
        idx_on = repartir(probs, PENALIZACION)

        cls_off = [clf.classes[i] for i in idx_off]
        cls_on = [clf.classes[i] for i in idx_on]
        conf_off = [float(probs[f, i]) for f, i in enumerate(idx_off)]
        conf_on = [float(probs[f, i]) for f, i in enumerate(idx_on)]

        e_off, e_on = exceso(cls_off), exceso(cls_on)
        n_off = sum(1 for c in conf_off if c < UMBRAL)
        n_on = sum(1 for c in conf_on if c < UMBRAL)

        tot['exceso_off'] += e_off
        tot['exceso_on'] += e_on
        tot['nar_off'] += n_off
        tot['nar_on'] += n_on
        tot['n'] += len(det)
        tot['movidos'] += int((idx_off != idx_on).sum())
        conf_off_all += conf_off
        conf_on_all += conf_on

        print('%-7s exceso %2d  nar %2d/%-3d   exceso %2d  nar %2d/%-3d'
              % (g, e_off, n_off, len(det), e_on, n_on, len(det)))

    n = max(1, tot['n'])
    print('-' * 74)
    print('\nAGREGADO sobre %d cromosomas detectados\n' % n)
    print('  %-34s %10s %10s' % ('', 'argmax', 'reparto'))
    print('  %-34s %10d %10d' % ('copias imposibles (>2 por clase)',
                                 tot['exceso_off'], tot['exceso_on']))
    print('  %-34s %10.3f %10.3f' % ('confianza media',
                                     statistics.mean(conf_off_all),
                                     statistics.mean(conf_on_all)))
    print('  %-34s %9d%% %9d%%' % ('naranjas (< %.2f)' % UMBRAL,
                                   round(100 * tot['nar_off'] / n),
                                   round(100 * tot['nar_on'] / n)))
    print()
    print('  cromosomas movidos de su argmax : %d de %d (%.0f%%)'
          % (tot['movidos'], n, 100 * tot['movidos'] / n))
    print()

    d_exceso = tot['exceso_off'] - tot['exceso_on']
    d_nar = tot['nar_on'] - tot['nar_off']
    print('  ESTRUCTURA: %+d copias imposibles  (menos es mejor)' % -d_exceso)
    print('  SEMAFORO  : %+d naranjas           (menos es mejor)' % d_nar)
    print()
    print('  Cada naranja cuesta ~2 acciones al analista (ver XAI + aceptar),')
    print('  asi que %+d naranjas son ~%+d acciones de trabajo humano.'
          % (d_nar, 2 * d_nar))
    return 0


if __name__ == '__main__':
    t0 = time.time()
    codigo = main()
    print('\n(%.0fs)' % (time.time() - t0))
    raise SystemExit(codigo)
