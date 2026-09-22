"""¿Se puede localizar cada recorte del cariograma dentro de su metafase?

    python training/probar_localizacion.py [--caso 1] [--rotaciones 36]

## Que hipotesis se esta probando

ADR-0035 esta bloqueada por una frase: **no hay verdad de terreno para
segmentacion**. Los 48.467 recortes estan etiquetados por clase pero salen del
CARIOGRAMA, y `crops_manifest.csv` no guarda coordenadas sobre la metafase.

Pero el cariograma no se dibuja: **se construye recortando la metafase**. El
experto corta cada cromosoma de la foto y lo pega ordenado. Si esos pixeles son
una copia —y no un redibujado— entonces cada recorte se puede volver a
encontrar en su metafase, y esa posicion ES la caja que falta.

Y la correspondencia existe y es exacta: `export_from_mdf.py` exporta
`cario_{IdAnalisis}.bmp` y `metafase_{IdAnalisis}.bmp` desde **la misma fila**
de `SCAAnalisisCariotipos` (columnas `ImagenCariotipo` e `ImagenMetafase`).
453 metafases tienen ademas sus recortes etiquetados.

Si la hipotesis se sostiene, ADR-0035 deja de estar bloqueada por falta de
datos: habria cajas para 453 metafases sin anotar ni una a mano.

## Por que esto es una PRUEBA y no una implementacion

Se mide sobre un caso y se reporta la tasa de acierto de la localizacion. Si
sale baja, la hipotesis se descarta y queda escrito por que — que es tan util
como si sale alta. No se construye nada encima hasta ver el numero.

El riesgo conocido: el experto suele **rotar** los cromosomas al montarlos en
el cariograma. Por eso se prueban N rotaciones y se reporta cuantos se
encuentran sin rotar y cuantos rotando.

Salida en ASCII puro (la consola de Windows rompe con Unicode).
"""
import argparse
import collections
import csv
import io
import sys
from pathlib import Path

import cv2
import numpy as np

RAIZ = Path(__file__).resolve().parents[2]
DATASET = RAIZ / 'datasets' / 'metaclass'
METAFASES = DATASET / 'metafases'
CROPS = DATASET / 'crops'
MANIFIESTO = DATASET / 'crops_manifest.csv'

#: Por encima de esto se considera que el recorte se encontro. matchTemplate
#: con TM_CCOEFF_NORMED devuelve 1.0 en una copia exacta; 0.9 deja margen para
#: la compresion y el remuestreo.
UMBRAL = 0.90


def recortes_de(id_analisis):
    """[(ruta_png, clase)] de un IdAnalisis, segun el manifiesto."""
    salida = []
    for fila in csv.DictReader(io.open(MANIFIESTO, encoding='utf-8')):
        if fila['source'] == 'cario_%s.bmp' % id_analisis:
            salida.append((CROPS / fila['file'], fila['class']))
    return salida


def gris(ruta):
    img = cv2.imread(str(ruta), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise SystemExit('no se pudo leer %s' % ruta)
    return img


def rotar(plantilla, grados):
    """Rota manteniendo todo el contenido (el lienzo crece)."""
    h, w = plantilla.shape
    centro = (w / 2.0, h / 2.0)
    m = cv2.getRotationMatrix2D(centro, grados, 1.0)
    cos, sin = abs(m[0, 0]), abs(m[0, 1])
    nw, nh = int(h * sin + w * cos), int(h * cos + w * sin)
    m[0, 2] += nw / 2.0 - centro[0]
    m[1, 2] += nh / 2.0 - centro[1]
    # Borde en blanco: el fondo de estas imagenes es claro.
    return cv2.warpAffine(plantilla, m, (nw, nh), flags=cv2.INTER_LINEAR,
                          borderMode=cv2.BORDER_CONSTANT, borderValue=255)


def localizar(metafase, plantilla, rotaciones, con_espejo=False):
    """Mejor coincidencia probando rotaciones Y reflexion.

    **La reflexion se probo y NO explica nada**: con espejo se localizan los
    mismos 3 de 6, y ninguno de los encontrados lo necesita. Se deja como
    opcion (`--espejo`) y apagada por defecto, porque duplica el coste sin
    aportar. Queda escrito para que nadie vuelva a proponerlo como si fuera
    obvio: era mi segunda hipotesis y era falsa.

    Devuelve (score, bbox, grados, espejado).
    """
    mejor = (-1.0, None, None, False)
    for espejo in ((False, True) if con_espejo else (False,)):
        base = cv2.flip(plantilla, 1) if espejo else plantilla
        for grados in rotaciones:
            plt = base if grados == 0 else rotar(base, grados)
            if plt.shape[0] > metafase.shape[0] or plt.shape[1] > metafase.shape[1]:
                continue
            res = cv2.matchTemplate(metafase, plt, cv2.TM_CCOEFF_NORMED)
            _, score, _, loc = cv2.minMaxLoc(res)
            if score > mejor[0]:
                h, w = plt.shape
                mejor = (float(score), (loc[0], loc[1], w, h), grados, espejo)
    return mejor


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--caso', default='1', help='IdAnalisis a probar')
    ap.add_argument('--rotaciones', type=int, default=36,
                    help='cuantos angulos probar (360/N grados de paso)')
    ap.add_argument('--tope', type=int, default=0,
                    help='cuantos recortes probar (0 = todos)')
    ap.add_argument('--espejo', action='store_true',
                    help='probar tambien la imagen espejada (medido: no aporta)')
    opts = ap.parse_args()

    ruta_meta = METAFASES / ('metafase_%s.bmp' % opts.caso)
    if not ruta_meta.exists():
        raise SystemExit('no existe %s' % ruta_meta)
    metafase = gris(ruta_meta)
    trozos = recortes_de(opts.caso)
    if opts.tope:
        trozos = trozos[:opts.tope]
    if not trozos:
        raise SystemExit('el caso %s no tiene recortes en el manifiesto' % opts.caso)

    paso = max(1, 360 // max(1, opts.rotaciones))
    angulos = [0] + [g for g in range(paso, 360, paso)]
    print('caso %s | metafase %dx%d | %d recortes | %d angulos (paso %d grados)'
          % (opts.caso, metafase.shape[1], metafase.shape[0], len(trozos),
             len(angulos), paso))
    print()
    print('%-22s %-6s %-8s %-6s %-7s %s'
          % ('recorte', 'clase', 'score', 'giro', 'espejo', 'bbox'))
    print('-' * 78)

    encontrados, espejados, scores = 0, 0, []
    por_clase = collections.Counter()
    for ruta, clase in trozos:
        if not ruta.exists():
            continue
        plantilla = gris(ruta)
        score, bbox, grados, espejo = localizar(metafase, plantilla, angulos,
                                                con_espejo=opts.espejo)
        scores.append(score)
        ok = score >= UMBRAL
        encontrados += int(ok)
        if ok and espejo:
            espejados += 1
        if ok:
            por_clase[clase] += 1
        print('%-22s %-6s %-8.3f %-6s %-7s %s'
              % (ruta.name, clase, score, '%d' % grados, 'si' if espejo else 'no',
                 bbox if ok else '(no encontrado)'))

    n = len(scores)
    print('-' * 78)
    print()
    print('RESULTADO')
    print('  recortes probados                 : %d' % n)
    print('  localizados (score >= %.2f)        : %d (%.0f%%)'
          % (UMBRAL, encontrados, 100.0 * encontrados / max(1, n)))
    print('  ...de esos, espejados             : %d' % espejados)
    print('  score medio                       : %.3f' % (sum(scores) / max(1, n)))
    print('  score maximo                      : %.3f' % max(scores or [0]))
    print()
    if encontrados == 0:
        print('  LECTURA: los recortes NO son copia de pixeles de la metafase.')
        print('  La hipotesis se descarta: ADR-0035 sigue sin verdad de terreno')
        print('  por esta via, y hay que anotar a mano o usar ADR-0034 (SAM 2).')
    elif encontrados >= 0.8 * n:
        print('  LECTURA: los recortes SI se localizan. Hay cajas de verdad de')
        print('  terreno para %d metafases sin anotar ni una a mano.' % 453)
        print('  ADR-0035 deja de estar bloqueada por falta de datos.')
    else:
        print('  LECTURA: se localiza una parte. Hay que entender que distingue')
        print('  a los que si de los que no antes de construir nada encima.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
