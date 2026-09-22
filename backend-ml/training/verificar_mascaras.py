"""Mide si las mascaras derivadas caen de verdad sobre los cromosomas.

    python training/verificar_mascaras.py --caso 1
    python training/verificar_mascaras.py --caso 1 --pintar salida.png

## Por que hace falta este guion

`derivar_cajas.py` dice cuantos recortes coloco, pero no si los coloco BIEN.
La comprobacion que trae dentro (cero solapes tras el reparto) solo mira las
cajas entre si: un conjunto de cajas perfectamente disjuntas puede estar
entero sobre el fondo blanco y pasar esa prueba.

Aqui se compara contra la imagen: se umbraliza la metafase y se mide que
fraccion de los pixeles de mascara caen sobre tinta. Si las cajas estuvieran
mal colocadas, ese numero se hunde; es la prueba que el propio guion no puede
hacerse a si mismo.

## El fallo que este guion caza, y que ya cazo una vez

La primera version rotaba la mascara con `rotar()`, que rellena el borde nuevo
con 255 porque esta escrita para recortes en escala de grises, donde 255 es el
fondo blanco. En una mascara binaria 255 es el CROMOSOMA: el giro convertia el
rectangulo entero en primer plano y la «mascara» dejaba de serlo.

    con rotar()          precision 49,3 %   (la silueta era el rectangulo)
    con rotar_mascara()  precision 99,3 %

El numero de cajas no cambiaba, y el recuento de solapes seguia dando cero.
Sin esta medida el error se habria ido al dataset. Octava vez en el proyecto
que el instrumento falla antes que el sistema medido.

## Que significa cada cifra

  precision  px de mascara que caen sobre tinta / px de mascara
             Es la que dice si las cajas estan bien puestas. Debe rondar 99 %.
  cobertura  px de tinta cubiertos / px de tinta de la metafase
             NO tiene que dar 100 %: solo se cubre lo que tiene caja, y la
             metafase lleva ademas numeros impresos y restos de tincion.
  reparto    manchas de tinta con 1, con varias y con ninguna caja dentro.
             Las de area grande con varias cajas son racimos RESUELTOS, que es
             justo lo que un detector necesita aprender.

Salida en ASCII puro (la consola de Windows rompe con Unicode).
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from derivar_cajas import (CROPS, METAFASES, gris, mascara_de,  # noqa: E402
                           rotar_mascara)

#: Una mancha de tinta menor que esto es un numero impreso o polvo, no un
#: cromosoma. Medido sobre el caso 1: los cromosomas van de 900 a 3.000 px.
AREA_MINIMA = 400


def mascara_en_metafase(fila, forma):
    """Mascara de una instancia, ya colocada en coordenadas de la metafase."""
    ruta = CROPS / fila['recorte']
    if not ruta.exists():                     # registros antiguos: solo basename
        ruta = CROPS / str(fila['clase']) / fila['recorte']
    m = mascara_de(gris(ruta))
    if fila['grados']:
        m = rotar_mascara(m, fila['grados'])
    x, y, w, h = fila['bbox']
    if m.shape != (h, w):
        m = cv2.resize(m, (w, h), interpolation=cv2.INTER_NEAREST)
    alto, ancho = forma
    lienzo = np.zeros(forma, np.uint8)
    y2, x2 = min(alto, y + h), min(ancho, x + w)
    if y2 <= y or x2 <= x:
        return None
    lienzo[y:y2, x:x2] = m[:y2 - y, :x2 - x]
    return lienzo


def tinta_de(metafase):
    _, t = cv2.threshold(metafase, 0, 255,
                         cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    return cv2.morphologyEx(t, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--caso', required=True)
    ap.add_argument('--cajas', default=None,
                    help='JSONL de derivar_cajas (por defecto cajas_<caso>.jsonl)')
    ap.add_argument('--pintar', default=None, help='PNG con las siluetas tintadas')
    opts = ap.parse_args()

    ruta_cajas = Path(opts.cajas or ('cajas_%s.jsonl' % opts.caso))
    if not ruta_cajas.exists():
        raise SystemExit('no existe %s (generalo con derivar_cajas.py --salida)'
                         % ruta_cajas)
    filas = [json.loads(l) for l in ruta_cajas.open(encoding='utf-8')]
    metafase = gris(METAFASES / ('metafase_%s.bmp' % opts.caso))
    tinta = tinta_de(metafase)

    acumulada = np.zeros(metafase.shape, np.uint8)
    color = cv2.cvtColor(metafase, cv2.COLOR_GRAY2BGR)
    rng = np.random.default_rng(0)
    centros, ocupacion = [], []
    for fila in filas:
        m = mascara_en_metafase(fila, metafase.shape)
        if m is None:
            continue
        x, y, w, h = fila['bbox']
        centros.append((int(y + h / 2), int(x + w / 2)))
        ocupacion.append(100.0 * (m > 0).sum() / float(w * h))
        if opts.pintar:
            tinte = np.array(rng.integers(60, 255, 3).tolist())
            color[m > 0] = (0.4 * color[m > 0] + 0.6 * tinte).astype(np.uint8)
        acumulada[m > 0] = 255

    px_mascara = int((acumulada > 0).sum())
    px_tinta = int((tinta > 0).sum())
    interseccion = int(((acumulada > 0) & (tinta > 0)).sum())

    # Reparto sobre las manchas de tinta: aisladas, racimos y huerfanas.
    n, etiquetas, stats, _ = cv2.connectedComponentsWithStats(tinta, 8)
    manchas = {i: int(stats[i, cv2.CC_STAT_AREA]) for i in range(1, n)
               if stats[i, cv2.CC_STAT_AREA] > AREA_MINIMA}
    cuenta = Counter()
    for cy, cx in centros:
        if 0 <= cy < etiquetas.shape[0] and 0 <= cx < etiquetas.shape[1]:
            cuenta[int(etiquetas[cy, cx])] += 1
    solas = [a for i, a in manchas.items() if cuenta.get(i, 0) == 1]
    racimos = [a for i, a in manchas.items() if cuenta.get(i, 0) > 1]
    vacias = [a for i, a in manchas.items() if cuenta.get(i, 0) == 0]

    def media(v):
        return int(np.mean(v)) if v else 0

    print('caso %s | metafase %dx%d | %d instancias'
          % (opts.caso, metafase.shape[1], metafase.shape[0], len(centros)))
    print()
    print('  la mascara ocupa del bbox (media)  : %.1f %%' % np.mean(ocupacion))
    print('  PRECISION (mascara sobre tinta)    : %.1f %%'
          % (100.0 * interseccion / max(1, px_mascara)))
    print('  cobertura (tinta con mascara)      : %.1f %%'
          % (100.0 * interseccion / max(1, px_tinta)))
    print()
    print('  manchas de tinta > %d px           : %d' % (AREA_MINIMA, len(manchas)))
    print('    con 1 instancia  (aislado)       : %-3d (area media %d px)'
          % (len(solas), media(solas)))
    print('    con 2+ (RACIMO RESUELTO)         : %-3d (area media %d px)'
          % (len(racimos), media(racimos)))
    print('    sin ninguna                      : %-3d (area media %d px)'
          % (len(vacias), media(vacias)))
    print()
    if 100.0 * interseccion / max(1, px_mascara) < 90:
        print('  LECTURA: la precision esta por debajo del 90 %. Las mascaras NO')
        print('  estan cayendo sobre los cromosomas: revisar el giro y el bbox')
        print('  ANTES de usar estas etiquetas para entrenar nada.')
    else:
        print('  LECTURA: las mascaras caen sobre los cromosomas. Las etiquetas')
        print('  de este caso sirven como verdad de terreno de instancia.')

    if opts.pintar:
        cv2.imwrite(opts.pintar, color)
        print('\n  pintado en %s' % opts.pintar)
    return 0


if __name__ == '__main__':
    sys.exit(main())
