"""Dos metafases del MISMO paciente, ¿dan el mismo cariotipo?

    python training/eval_multimetafase.py [--muestras 6] [--tope 8]

## Por que hace falta esta medicion

El sistema sube tres metafases por caso y **segmenta solo la primera**
(`services._first_image_bytes`); las otras dos se guardan y no se miran. Antes
de decidir que hacer con ellas hay que saber una cosa que nadie ha medido:
**cuanto se parecen entre si los cariotipos que produce el pipeline sobre
metafases distintas del mismo paciente**.

De la respuesta dependen dos disenos opuestos:

  - Si coinciden casi siempre -> las otras metafases son confirmacion barata, y
    el consenso es un voto que sube la confianza.
  - Si no coinciden casi nunca -> el consenso por formula ISCN no se puede
    construir hoy, y decirlo es la decision correcta.

## Lo que dice el dato real del laboratorio

`datasets/metaclass/labels.csv` tiene `IdMuestra`: las 460 metafases anotadas
pertenecen a solo **28 muestras**, y 17 de ellas tienen exactamente **20**
metafases. Veinte es el recuento estandar de la citogenetica clinica, y existe
precisamente para detectar mosaicismo. O sea: el laboratorio real trabaja con
20 y el sistema mira 1.

## Que se mide, y que NO

Se mide el acuerdo entre metafases sobre:

  1. el numero de cromosomas detectados (deberian ser 46)
  2. el conteo por clase
  3. el string ISCN que sale de ese conteo

**No se mide acierto**: no hay ISCN anotado en el dataset (la columna esta
vacia en las 460 filas), asi que no hay verdad contra la que comparar. Lo que
se mide es *consistencia*, que es justo lo que un consenso necesita.

Salida en ASCII puro: la consola de Windows rompe con Unicode.
"""
import argparse
import collections
import csv
import io
import statistics
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / 'backend-ml'))
sys.path.insert(0, str(RAIZ / 'backend-clinic'))

METAFASES = RAIZ / 'datasets' / 'metaclass' / 'metafases'
LABELS = RAIZ / 'datasets' / 'metaclass' / 'labels.csv'
COPIAS_NORMALES = 2


def muestras_multimetafase(minimo=2):
    """IdMuestra -> [ids de metafase], solo las que existen en disco."""
    por_muestra = collections.defaultdict(list)
    for fila in csv.DictReader(io.open(LABELS, encoding='utf-8')):
        ident = Path(fila['file']).stem.replace('metafase_', '')
        if (METAFASES / ('metafase_%s.bmp' % ident)).exists():
            por_muestra[fila['IdMuestra']].append(ident)
    return {m: sorted(v, key=int) for m, v in por_muestra.items() if len(v) >= minimo}


def clasificar_metafase(clf, torch, letterbox, reference_height, segment,
                        load_gray, ident):
    """Segmenta y clasifica una metafase. Devuelve las clases predichas."""
    gray = load_gray((METAFASES / ('metafase_%s.bmp' % ident)).read_bytes())
    det = segment(gray)
    if not det:
        return None
    ref_h = reference_height([d.bbox[3] for d in det])
    lote = torch.stack([
        clf._tf(letterbox(gray[y:y + h, x:x + w], ref_h, canvas=clf._img_size))
        for (x, y, w, h) in (d.bbox for d in det)])
    with torch.no_grad():
        probs = torch.softmax(clf._model(lote), dim=1).cpu().numpy()
    return [clf.classes[i] for i in probs.argmax(axis=1)]


def iscn_de(clases):
    """El ISCN que saldria de ese conteo, o el motivo por el que no sale."""
    from apps.samples.iscn import IscnError, generate_iscn
    conteo = collections.Counter(clases)
    try:
        return generate_iscn(dict(conteo))
    except IscnError as exc:
        return '<rechazado: %s>' % exc


def exceso(clases):
    return sum(max(0, n - COPIAS_NORMALES)
               for n in collections.Counter(clases).values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--muestras', type=int, default=6,
                    help='cuantas muestras medir')
    ap.add_argument('--tope', type=int, default=8,
                    help='cuantas metafases por muestra como maximo')
    opts = ap.parse_args()

    from app.efficientnet import EfficientNetClassifier
    from app.main import load_gray
    from app.preprocess import letterbox, reference_height
    from app.segmentation import segment

    clf = EfficientNetClassifier()
    if not clf.is_trained:
        print('no hay modelo entrenado', file=sys.stderr)
        return 1
    torch = clf._torch
    print('modelo:', clf.name)

    todas = muestras_multimetafase()
    elegidas = sorted(todas, key=lambda m: (-len(todas[m]), int(m)))[:opts.muestras]
    print('muestras con >=2 metafases en disco: %d (se miden %d)\n'
          % (len(todas), len(elegidas)))

    resumen = []
    for muestra in elegidas:
        ids = todas[muestra][:opts.tope]
        print('== muestra %s  (%d de %d metafases)'
              % (muestra, len(ids), len(todas[muestra])))
        print('   %-10s %-6s %-8s %s' % ('metafase', 'detec', 'exceso', 'ISCN derivado'))

        iscns, detectados = [], []
        for ident in ids:
            clases = clasificar_metafase(clf, torch, letterbox, reference_height,
                                         segment, load_gray, ident)
            if clases is None:
                print('   %-10s %s' % (ident, 'sin deteccion'))
                continue
            cadena = iscn_de(clases)
            iscns.append(cadena)
            detectados.append(len(clases))
            print('   %-10s %-6d %-8d %s'
                  % (ident, len(clases), exceso(clases), cadena[:58]))

        if len(iscns) < 2:
            print()
            continue

        # OJO: un rechazo NO es un acuerdo. La primera version de este guion
        # contaba «5 de 5 metafases coinciden» cuando las cinco habian sido
        # rechazadas por el motor ISCN — el acuerdo era sobre el mensaje de
        # error, no sobre un cariotipo. Sexta vez en este proyecto que la
        # primera medicion falla por el medidor.
        validos = [c for c in iscns if not c.startswith('<rechazado')]
        distintos = collections.Counter(validos)
        veces = distintos.most_common(1)[0][1] if distintos else 0
        resumen.append({
            'muestra': muestra,
            'n': len(iscns),
            'validos': len(validos),
            'distintos': len(distintos),
            'acuerdo': veces,
            'detec_min': min(detectados),
            'detec_max': max(detectados),
            'detec_media': statistics.mean(detectados),
        })
        print('   -> %d de %d metafases producen un ISCN; el resto las rechaza el motor'
              % (len(validos), len(iscns)))
        if validos:
            print('   -> %d ISCN distintos entre esos %d; el mas repetido sale %d vez/veces'
                  % (len(distintos), len(validos), veces))
        print('   -> cromosomas detectados: %d..%d (media %.1f, esperado 46)'
              % (min(detectados), max(detectados), statistics.mean(detectados)))
        print()

    if not resumen:
        print('sin datos suficientes')
        return 1

    print('=' * 72)
    print('AGREGADO')
    print('=' * 72)
    tot_m = sum(r['n'] for r in resumen)
    tot_v = sum(r['validos'] for r in resumen)
    # Solo tiene sentido hablar de acuerdo donde hay al menos dos ISCN validos.
    comparables = [r for r in resumen if r['validos'] >= 2]
    coinciden = sum(1 for r in comparables if r['distintos'] == 1)
    print('  muestras medidas                 : %d' % len(resumen))
    print('  metafases clasificadas           : %d' % tot_m)
    print('  ...que producen un ISCN          : %d de %d (%.0f%%)'
          % (tot_v, tot_m, 100.0 * tot_v / max(1, tot_m)))
    print('  ...rechazadas por el motor       : %d de %d (%.0f%%)'
          % (tot_m - tot_v, tot_m, 100.0 * (tot_m - tot_v) / max(1, tot_m)))
    print('  muestras con >=2 ISCN comparables: %d de %d'
          % (len(comparables), len(resumen)))
    if comparables:
        print('  ...donde TODAS coinciden         : %d de %d'
              % (coinciden, len(comparables)))
    todos_det = [r['detec_media'] for r in resumen]
    print('  cromosomas detectados (media)    : %.1f  (esperado 46)'
          % statistics.mean(todos_det))
    print()
    if tot_v == 0:
        print('  LECTURA: NINGUNA metafase produce un ISCN. No hay nada sobre lo')
        print('  que votar: el cuello de botella esta aguas arriba, en la')
        print('  segmentacion, no en como combinar metafases.')
    elif not comparables:
        print('  LECTURA: ninguna muestra llega a tener DOS ISCN validos que')
        print('  comparar. El consenso no se puede medir todavia, y menos aun')
        print('  construir.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
