"""¿De dónde salen los naranjas: del clasificador o de la segmentación?

    python training/eval_dos_caminos.py [--casos 12]

## La pregunta

Al procesar una metafase real, ~95% de los cromosomas salen naranjas (confianza
< 0.85) y la media ronda 0.54. `eval_correccion.py` atribuye el grueso del coste
a "resolver naranjas" (34 de 64 acciones) y solo 4 a la segmentación. De ahí se
concluyó que el detector no era el cuello de botella.

Esa conclusión puede ser un artefacto del instrumento: `estructura` se mide como
|detectados - reales|, así que si el detector junta dos cromosomas Y parte otro,
los errores se CANCELAN y la segmentación parece inocente. Y si los naranjas
fueran consecuencia de recortes malos, "resolver naranjas" no sería un coste
independiente: sería la sombra de la segmentación.

## El experimento

El MISMO caso por los dos caminos, con el mismo modelo:

  A · recortes limpios del cariograma que hizo el citogenetista
  B · la metafase entera, segmentada por OpenCV + watershed

Si A da confianzas altas y B bajas, los naranjas los produce la segmentación,
no el clasificador.

Se miden solo cariogramas de la partición de VALIDACIÓN del cuaderno v3
(semilla 42, 15% por cariograma): el modelo no los vio al entrenar. Medir sobre
casos de entrenamiento inflaría el camino A y el experimento no valdría nada.

Salida en ASCII puro (la consola de Windows rompe con Unicode).
"""
import argparse
import os
import random
import re
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / 'backend-ml'))

SEED = 42
VAL_FRAC = 0.15
UMBRAL = 0.85
PAT = re.compile(r'^cario(\d+)_\d+\.png$')

CROPS = RAIZ / 'datasets' / 'metaclass' / 'crops'
METAFASES = RAIZ / 'datasets' / 'metaclass' / 'metafases'


def casos_de_validacion():
    """Reproduce el split del cuaderno v3: barajado por cariograma, semilla 42."""
    por_grupo = defaultdict(list)
    for cls in sorted(os.listdir(CROPS)):
        cdir = CROPS / cls
        if not cdir.is_dir():
            continue
        for fn in sorted(os.listdir(cdir)):
            m = PAT.match(fn)
            if m:
                por_grupo[m.group(1)].append((cdir / fn, cls))

    grupos = sorted(por_grupo)
    barajado = grupos[:]
    random.Random(SEED).shuffle(barajado)
    val = set(barajado[:max(1, int(len(barajado) * VAL_FRAC))])
    return por_grupo, [g for g in sorted(val, key=int)
                       if (METAFASES / ('metafase_%s.bmp' % g)).exists()]


def camino_a(clf, recortes):
    """Recortes limpios del experto. ref_h = mediana del caso, como en el entreno."""
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
    predichas = [clf.classes[int(i)] for i in idx.tolist()]
    confianzas = [float(c) for c in conf.tolist()]
    aciertos = sum(1 for p, v in zip(predichas, verdades) if p == v)
    return confianzas, aciertos, len(verdades)


def camino_b(clf, ruta_metafase):
    """La metafase entera, segmentada como en produccion."""
    from app.main import load_gray
    from app.segmentation import segment

    gray = load_gray(ruta_metafase.read_bytes())
    detecciones = segment(gray)
    return [c for _, c in clf.classify_all(gray, detecciones)], len(detecciones)


def resumen(nombre, confianzas):
    naranjas = sum(1 for c in confianzas if c < UMBRAL)
    return ('  %-28s n=%-4d media %.3f | mediana %.3f | naranjas %d/%d (%.0f%%)' % (
        nombre, len(confianzas), statistics.mean(confianzas),
        statistics.median(confianzas), naranjas, len(confianzas),
        100 * naranjas / max(1, len(confianzas))))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--casos', type=int, default=12)
    opts = ap.parse_args()

    from app.efficientnet import EfficientNetClassifier
    clf = EfficientNetClassifier()
    if not clf.is_trained:
        print('no hay modelo entrenado', file=sys.stderr)
        return 1
    print('modelo:', clf.name)

    por_grupo, elegibles = casos_de_validacion()
    elegidos = elegibles[:opts.casos]
    print('casos de VALIDACION con metafase: %d (se miden %d)\n'
          % (len(elegibles), len(elegidos)))

    todas_a, todas_b = [], []
    aciertos_a = total_a = 0
    print('%-8s %-28s %-28s' % ('caso', 'A recortes del experto', 'B desde la metafase'))
    print('-' * 72)
    for g in elegidos:
        conf_a, ok, n = camino_a(clf, por_grupo[g])
        conf_b, n_det = camino_b(clf, METAFASES / ('metafase_%s.bmp' % g))
        todas_a += conf_a
        todas_b += conf_b
        aciertos_a += ok
        total_a += n
        print('%-8s media %.3f  nar %2d/%-3d   media %.3f  nar %2d/%-3d' % (
            g, statistics.mean(conf_a), sum(1 for c in conf_a if c < UMBRAL), len(conf_a),
            statistics.mean(conf_b), sum(1 for c in conf_b if c < UMBRAL), len(conf_b)))

    print('-' * 72)
    print('\nAGREGADO')
    print(resumen('A · recortes del experto', todas_a))
    print(resumen('B · desde la metafase', todas_b))
    print('\n  acierto real del camino A: %d/%d (%.1f%%)  <- contra la clase del experto'
          % (aciertos_a, total_a, 100 * aciertos_a / max(1, total_a)))
    print('\n  El camino B no tiene acierto medible: la segmentacion no produce')
    print('  los mismos objetos que el experto, asi que no hay con que parear.')
    print('  Eso YA es parte de la respuesta.')
    return 0


if __name__ == '__main__':
    t0 = time.time()
    codigo = main()
    print('\n(%.0fs)' % (time.time() - t0))
    raise SystemExit(codigo)
