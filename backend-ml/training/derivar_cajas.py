"""Deriva cajas de verdad de terreno localizando cada recorte en su metafase.

    python training/derivar_cajas.py --caso 1
    python training/derivar_cajas.py --casos 5 --salida cajas.jsonl

## De donde sale esto

ADR-0035 esta bloqueada por «no hay verdad de terreno para segmentacion». Pero
el cariograma no se dibuja: **se construye recortando la metafase**, y
`export_from_mdf.py` exporta `cario_N.bmp` y `metafase_N.bmp` desde la misma
fila de la base. Si los pixeles del recorte son copia, su posicion en la
metafase ES la caja que falta.

`probar_localizacion.py` confirmo la hipotesis: scores de hasta **0,994**, que
es coincidencia exacta de pixeles.

## El error que este guion corrige, y por que importa

La primera version elegia para cada recorte su mejor posicion **de forma
independiente**. Resultado aparente: 39 de 47 (83 %). Resultado real: **17 de
esos 39 apuntaban al mismo cromosoma que otro recorte**, casi todos pares
homologos —clase 10 con clase 10, IoU 0,97— porque los homologos se parecen y
`matchTemplate` no distingue «encontre este» de «encontre uno igual».

    lo que parecia:  39 de 47 = 83 %
    lo que era:      22 de 47 = 47 %

Es **exactamente el fallo que ADR-0033 arreglo en el clasificador**: decidir
cada objeto por su cuenta produce un conjunto imposible. Alli eran nueve copias
de la clase 1; aqui son dos recortes sobre un mismo cromosoma. Y la solucion es
la misma: **decidir globalmente**.

Aqui la restriccion no es un cupo por clase sino espacial —dos cajas no pueden
ocupar el mismo sitio—, asi que no es Hungarian sino una pasada codiciosa con
veto de solape: se ordenan todos los candidatos por score y se acepta uno si su
recorte sigue libre y su caja no pisa ninguna ya aceptada.

Entrenar con las 17 etiquetas falsas habria enseñado al detector a poner dos
cajas sobre un cromosoma. El instrumento fallo antes que el sistema, por
septima vez en este proyecto.

Salida en ASCII puro (la consola de Windows rompe con Unicode).
"""
import argparse
import csv
import io
import json
import sys
from pathlib import Path

import cv2
import numpy as np

RAIZ = Path(__file__).resolve().parents[2]
DATASET = RAIZ / 'datasets' / 'metaclass'
METAFASES = DATASET / 'metafases'
CROPS = DATASET / 'crops'
MANIFIESTO = DATASET / 'crops_manifest.csv'

#: Score minimo para considerar que un candidato es el mismo cromosoma.
UMBRAL = 0.90
#: Dos cajas que se pisan mas que esto son el mismo cromosoma.
IOU_MAX = 0.30
#: Candidatos que se guardan por recorte. Con 1 no hay alternativa cuando el
#: mejor se lo lleva otro, y el recorte se queda sin caja pudiendo tenerla.
CANDIDATOS = 5


def recortes_de(id_analisis):
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
    h, w = plantilla.shape
    centro = (w / 2.0, h / 2.0)
    m = cv2.getRotationMatrix2D(centro, grados, 1.0)
    cos, sin = abs(m[0, 0]), abs(m[0, 1])
    nw, nh = int(h * sin + w * cos), int(h * cos + w * sin)
    m[0, 2] += nw / 2.0 - centro[0]
    m[1, 2] += nh / 2.0 - centro[1]
    return cv2.warpAffine(plantilla, m, (nw, nh), flags=cv2.INTER_LINEAR,
                          borderMode=cv2.BORDER_CONSTANT, borderValue=255)


def rotar_mascara(mascara, grados):
    """Como rotar(), pero el borde que el giro anade es FONDO (0).

    No es un detalle: en un recorte en escala de grises 255 es el fondo blanco,
    y en una mascara binaria 255 es el cromosoma. Reusar rotar() aqui pinta de
    primer plano todo el lienzo nuevo y la 'mascara' pasa a ser el rectangulo
    entero. Medido: con rotar() la precision (px de mascara que caen sobre
    tinta de la metafase) es 49 %; con esta, 99 %.
    """
    h, w = mascara.shape
    centro = (w / 2.0, h / 2.0)
    m = cv2.getRotationMatrix2D(centro, grados, 1.0)
    cos, sin = abs(m[0, 0]), abs(m[0, 1])
    nw, nh = int(h * sin + w * cos), int(h * cos + w * sin)
    m[0, 2] += nw / 2.0 - centro[0]
    m[1, 2] += nh / 2.0 - centro[1]
    r = cv2.warpAffine(mascara, m, (nw, nh), flags=cv2.INTER_NEAREST,
                       borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    return (r > 127).astype(np.uint8) * 255


def mascara_de(recorte):
    """Silueta del cromosoma dentro de su recorte.

    El recorte del cariograma es un cromosoma solo sobre fondo claro, asi que
    Otsu lo separa sin ayuda. Se rellena el contorno exterior mayor: las bandas
    claras del propio cromosoma abren huecos que NO son fondo.
    """
    _, m = cv2.threshold(recorte, 0, 255,
                         cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    contornos, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not contornos:
        return m
    salida = np.zeros_like(m)
    cv2.drawContours(salida, [max(contornos, key=cv2.contourArea)], -1, 255,
                     cv2.FILLED)
    return salida


def poligono_en_metafase(ruta_recorte, bbox, grados):
    """Contorno de la instancia en coordenadas de la METAFASE.

    Es lo que convierte este guion de «cajas» en «mascaras de instancia», que
    es lo que pide el trigger D4.1 de ADR-0035. Se devuelve como poligono
    [[x, y], ...] y no como RLE para que el fichero siga siendo legible.
    """
    m = mascara_de(gris(ruta_recorte))
    if grados:
        m = rotar_mascara(m, grados)
    x, y, w, h = bbox
    if m.shape != (h, w):
        m = cv2.resize(m, (w, h), interpolation=cv2.INTER_NEAREST)
    contornos, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contornos:
        return [], 0
    c = max(contornos, key=cv2.contourArea)
    return [[int(px) + x, int(py) + y] for px, py in c[:, 0, :]], int((m > 0).sum())


def iou(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    x1, y1 = max(ax, bx), max(ay, by)
    x2, y2 = min(ax + aw, bx + bw), min(ay + ah, by + bh)
    if x2 <= x1 or y2 <= y1:
        return 0.0
    inter = (x2 - x1) * (y2 - y1)
    return inter / float(aw * ah + bw * bh - inter)


def _mejor_a(metafase, plantilla, grados):
    """(score, bbox, grados) de la mejor posicion a un angulo dado, o None."""
    plt = plantilla if grados == 0 else rotar(plantilla, grados)
    if plt.shape[0] > metafase.shape[0] or plt.shape[1] > metafase.shape[1]:
        return None
    res = cv2.matchTemplate(metafase, plt, cv2.TM_CCOEFF_NORMED)
    _, score, _, loc = cv2.minMaxLoc(res)
    h, w = plt.shape
    return (float(score), (loc[0], loc[1], w, h), grados)


#: Cuantos angulos gruesos se refinan a 1 grado. Con 3 se cubren el mejor sitio
#: y dos alternativas, que es lo que el reparto necesita.
REFINAR = 3


def candidatos_de(metafase, plantilla, angulos, cuantos=CANDIDATOS,
                  umbral=UMBRAL, paso_fino=None):
    """Las `cuantos` mejores posiciones ESPACIALMENTE DISTINTAS del recorte.

    Guardar varias es lo que permite que el reparto funcione: cuando el mejor
    sitio de un recorte se lo queda otro con mas score, este puede caer en su
    segunda opcion en vez de quedarse sin caja.

    ## Grueso-a-fino (`paso_fino`)

    Probar los 360 grados de uno en uno cuesta ~16 s por recorte (medido:
    0,046 s por matchTemplate en 4 nucleos sin GPU), o sea ~18 min por metafase
    y casi seis dias para las 453. Con `paso_fino=1` se barren solo los
    `angulos` gruesos (p. ej. cada 10 grados) y se refinan a 1 grado, en
    +-(paso-1), los REFINAR mejores.

    **Validado contra el barrido completo antes de adoptarlo**, caso 1:

        360 grados de uno en uno   31 de 47 cajas
        --rotaciones 36 --fino     30 de 47 cajas, en 4 min 12 s

    De los 30 que coloca, los 30 caen en la MISMA caja que el barrido completo
    (IoU > 0,7; ninguno en sitio distinto) y el score medio no baja: 0,9635
    frente a 0,9616. Se pierde un recorte de 31. Ese es el precio exacto del
    atajo, y esta medido, no estimado.
    """
    bruto = [c for c in (_mejor_a(metafase, plantilla, g) for g in angulos) if c]
    if paso_fino and len(angulos) > 1:
        paso = angulos[1] - angulos[0]
        bruto.sort(key=lambda c: -c[0])
        finos = []
        for _s, _b, centro in bruto[:REFINAR]:
            for g in range(centro - paso + 1, centro + paso):
                if g % paso == 0:
                    continue          # ya medido en la pasada gruesa
                c = _mejor_a(metafase, plantilla, g % 360)
                if c:
                    finos.append(c)
        bruto.extend(finos)

    bruto.sort(key=lambda c: -c[0])
    elegidos = []
    for score, bbox, grados in bruto:
        if score < umbral:
            break
        if all(iou(bbox, e[1]) <= IOU_MAX for e in elegidos):
            elegidos.append((score, bbox, grados))
        if len(elegidos) >= cuantos:
            break
    return elegidos


def repartir_cajas(propuestas):
    """Pasada codiciosa con veto de solape.

    `propuestas` es {indice_recorte: [(score, bbox, grados), ...]}. Se ordenan
    TODOS los candidatos de TODOS los recortes por score y se acepta uno si:
    su recorte sigue sin caja, y su caja no pisa ninguna ya aceptada.

    Codicioso y no Hungarian a proposito: la restriccion es el solape entre
    cajas, no un cupo por fila, y el orden por score da un resultado
    determinista y explicable — el candidato con 0,99 manda sobre el de 0,91.
    """
    todos = []
    for idx, lista in propuestas.items():
        for score, bbox, grados in lista:
            todos.append((score, idx, bbox, grados))
    todos.sort(key=lambda c: -c[0])

    asignadas = {}
    ocupadas = []
    for score, idx, bbox, grados in todos:
        if idx in asignadas:
            continue
        if any(iou(bbox, o) > IOU_MAX for o in ocupadas):
            continue
        asignadas[idx] = (score, bbox, grados)
        ocupadas.append(bbox)
    return asignadas


def procesar(id_analisis, angulos, verboso=True, umbral=UMBRAL, paso_fino=None,
             con_mascara=False):
    ruta_meta = METAFASES / ('metafase_%s.bmp' % id_analisis)
    if not ruta_meta.exists():
        return None
    metafase = gris(ruta_meta)
    trozos = [(r, c) for r, c in recortes_de(id_analisis) if r.exists()]
    if not trozos:
        return None

    propuestas = {}
    for i, (ruta, _clase) in enumerate(trozos):
        propuestas[i] = candidatos_de(metafase, gris(ruta), angulos,
                                      umbral=umbral, paso_fino=paso_fino)

    asignadas = repartir_cajas(propuestas)

    # Cuantos tenian AL MENOS un candidato: es el techo de lo que el reparto
    # podria haber colocado. La diferencia con lo colocado son los que perdieron
    # todos sus sitios frente a otros recortes.
    con_candidato = sum(1 for v in propuestas.values() if v)

    filas = []
    for i, (ruta, clase) in enumerate(trozos):
        if i not in asignadas:
            continue
        score, bbox, grados = asignadas[i]
        # Ruta RELATIVA a crops/, no el nombre pelado: los recortes viven en
        # crops/<clase>/ y con solo el basename el registro no permite volver a
        # abrir su propio fichero.
        fila = {'caso': id_analisis,
                'recorte': ruta.relative_to(CROPS).as_posix(),
                'clase': clase,
                'bbox': list(bbox), 'grados': grados,
                'score': round(score, 4)}
        if con_mascara:
            poly, area = poligono_en_metafase(ruta, bbox, grados)
            fila['poligono'] = poly
            fila['area'] = area
        filas.append(fila)

    if verboso:
        print('caso %-6s recortes %-4d con candidato %-4d CON CAJA UNICA %-4d (%.0f%%)'
              % (id_analisis, len(trozos), con_candidato, len(filas),
                 100.0 * len(filas) / len(trozos)))
    return {'caso': id_analisis, 'recortes': len(trozos),
            'con_candidato': con_candidato, 'colocadas': len(filas),
            'filas': filas}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--caso', default=None, help='un IdAnalisis concreto')
    ap.add_argument('--casos', type=int, default=1, help='cuantos casos procesar')
    ap.add_argument('--rotaciones', type=int, default=360)
    ap.add_argument('--salida', default=None, help='fichero JSONL con las cajas')
    ap.add_argument('--umbral', type=float, default=UMBRAL,
                    help='score minimo para aceptar un candidato')
    ap.add_argument('--fino', action='store_true',
                    help='grueso-a-fino: barrer --rotaciones y refinar a 1 grado')
    ap.add_argument('--mascaras', action='store_true',
                    help='emitir tambien el poligono de cada instancia (D4.1 de ADR-0035)')
    opts = ap.parse_args()

    paso = max(1, 360 // max(1, opts.rotaciones))
    angulos = [0] + [g for g in range(paso, 360, paso)]

    if opts.caso:
        ids = [opts.caso]
    else:
        disponibles = sorted(
            {p.stem.replace('metafase_', '') for p in METAFASES.glob('*.bmp')},
            key=int)
        ids = disponibles[:opts.casos]

    print('paso angular: %d grados | casos: %d\n' % (paso, len(ids)))
    resultados, todas = [], []
    for ident in ids:
        r = procesar(ident, angulos, umbral=opts.umbral,
                     paso_fino=1 if opts.fino else None,
                     con_mascara=opts.mascaras)
        if r:
            resultados.append(r)
            todas.extend(r['filas'])

    if not resultados:
        print('sin resultados')
        return 1

    tot_r = sum(r['recortes'] for r in resultados)
    tot_cand = sum(r['con_candidato'] for r in resultados)
    tot_col = sum(r['colocadas'] for r in resultados)
    print()
    print('=' * 68)
    print('  casos procesados                  : %d' % len(resultados))
    print('  recortes                          : %d' % tot_r)
    print('  con al menos un candidato >= %.2f  : %d (%.0f%%)'
          % (opts.umbral, tot_cand, 100.0 * tot_cand / tot_r))
    print('  CON CAJA UNICA tras el reparto    : %d (%.0f%%)'
          % (tot_col, 100.0 * tot_col / tot_r))
    print('=' * 68)

    # Comprobacion del propio instrumento: despues del reparto NO puede quedar
    # ni un solape. Si queda, el veto esta mal y la cifra de arriba no vale.
    colisiones = 0
    for r in resultados:
        cajas = [f['bbox'] for f in r['filas']]
        for i in range(len(cajas)):
            for j in range(i + 1, len(cajas)):
                if iou(cajas[i], cajas[j]) > IOU_MAX:
                    colisiones += 1
    print('  solapes residuales (deben ser 0)  : %d' % colisiones)
    if colisiones:
        print('  *** el veto de solape no esta funcionando ***')
        return 1

    if opts.salida:
        destino = Path(opts.salida)
        with io.open(destino, 'w', encoding='utf-8', newline='\n') as fh:
            for fila in todas:
                fh.write(json.dumps(fila, ensure_ascii=False) + '\n')
        print('\n  escritas %d cajas en %s' % (len(todas), destino))
    return 0


if __name__ == '__main__':
    sys.exit(main())
