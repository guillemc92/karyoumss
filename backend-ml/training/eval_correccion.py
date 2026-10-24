"""¿Cuánto trabajo le ahorra la IA al analista? — coste de corrección por caso.

    python training/eval_correccion.py [--casos 30] [--json salida.json]

## Por qué esta métrica y no la precisión del modelo

`macro-F1 0.6958` no dice si el producto sirve. Lo que decide si esto es
**asistencia** o estorbo es cuántas acciones tiene que hacer el analista para
llevar la propuesta de la IA hasta un cariotipo correcto.

Y hay un punto de comparación honesto: ordenar a mano un cariograma ya
segmentado son **46 colocaciones**. Si corregir la salida de la IA cuesta más
que eso, la IA no está ayudando — está añadiendo trabajo.

## El modelo de coste

Se cuentan las acciones que la interfaz ofrece de verdad (ADR-0021 P3/P4 y
RECROP), no acciones inventadas:

    estructura      separar o unir para llegar al número correcto de objetos
    clase           reclasificar los que están en la pila equivocada
    resolución      ver XAI + aceptar, para los naranjas que nadie tocó (x2,
                    porque BR-004 obliga a mirar la explicabilidad antes)

Reclasificar ya deja el cromosoma resuelto, así que no se cobra dos veces.

## Ground truth

El cariograma `cario_N` y la metafase `metafase_N` son **el mismo caso**: el
cariograma es lo que el experto ordenó a partir de esa metafase. Los recortes
del cariograma llevan la clase que el experto les asignó, así que su reparto
por clase es la verdad de referencia de ese caso.

**Limitación declarada:** se comparan repartos por clase, no objeto a objeto —
no existe correspondencia entre cada detección y cada cromosoma del cariograma.
Por eso `clase` es una **cota inferior**: el número real de reclasificaciones
puede ser mayor, nunca menor. La conclusión que se saque tiene que aguantar
siendo el mejor caso posible para la IA.

## El ground truth también tiene ruido, y por eso se filtra

Medido sobre los 1.150 cariogramas: **solo el 43% suma entre 45 y 48
cromosomas**. La mediana es 44 y hay casos de 38. Un cariotipo humano no tiene
38 cromosomas: eso es extracción incompleta de recortes del cariograma, no
biología.

Si no se filtrara, un caso con 40 recortes extraídos y 47 detecciones reales
cobraría 7 acciones de estructura que no son culpa de la IA. Por eso se miden
por defecto solo los casos de total plausible (`--gt-min`/`--gt-max`). Es
medir contra la verdad que se puede defender, no contra toda la que hay.
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

DATASET = RAIZ / 'datasets' / 'metaclass'
MANIFEST = DATASET / 'crops_manifest.csv'
METAFASES = DATASET / 'metafases'

# El umbral de la semaforización (RN-02). Por debajo, el cromosoma es naranja y
# bloquea la emisión del informe hasta que un humano lo resuelva.
UMBRAL = 0.85
# Ordenar a mano un cariograma ya segmentado. Es la vara: por encima de esto la
# IA cuesta más que no tenerla.
COSTE_MANUAL = 46


def ground_truth() -> dict[int, Counter]:
    """Reparto por clase que el experto dejó en cada cariograma."""
    por_caso: dict[int, Counter] = {}
    with MANIFEST.open(encoding='utf-8') as fh:
        for fila in csv.DictReader(fh):
            fuente = fila['source']                       # cario_123.bmp
            if not fuente.startswith('cario_'):
                continue
            caso = int(fuente[len('cario_'):].split('.')[0])
            por_caso.setdefault(caso, Counter())[fila['class']] += 1
    return por_caso


def coste(gt: Counter, predichos: list[tuple[str, float]]) -> dict:
    """Acciones mínimas para llevar la propuesta de la IA al cariotipo correcto."""
    pred = Counter(c for c, _ in predichos)
    gt_total, pred_total = sum(gt.values()), sum(pred.values())

    # Separar los cúmulos que faltan, o unir los fragmentos que sobran.
    estructura = abs(pred_total - gt_total)

    # Cromosomas en la pila equivocada: lo que sobra en cada clase respecto de
    # lo que el experto puso ahí.
    clase = sum(max(0, pred[c] - gt[c]) for c in set(pred) | set(gt))

    naranjas = sum(1 for _, s in predichos if s < UMBRAL)
    # Reclasificar ya deja resuelto el cromosoma: solo se cobran aparte los
    # naranjas que nadie iba a tocar. x2 = ver XAI (BR-004) + aceptar.
    resolucion = 2 * max(0, naranjas - clase)

    return {
        'gt_total': gt_total, 'detectados': pred_total,
        'estructura': estructura, 'clase': clase,
        'naranjas': naranjas, 'resolucion': resolucion,
        'acciones': estructura + clase + resolucion,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--casos', type=int, default=30,
                    help='cuántos casos medir (0 = todos los pareados)')
    # Solo el 43% de los cariogramas suma un total plausible; el resto son
    # extracciones incompletas y falsearían el coste (ver docstring).
    ap.add_argument('--gt-min', type=int, default=45)
    ap.add_argument('--gt-max', type=int, default=48)
    ap.add_argument('--json', type=Path, help='volcar el detalle')
    opts = ap.parse_args()

    if not MANIFEST.exists():
        print(f'falta el manifiesto: {MANIFEST}', file=sys.stderr)
        return 1

    from app.pipeline import run_pipeline
    from app.segmentation import load_gray

    gts = ground_truth()
    # Solo los casos con las dos mitades: cariograma (verdad) y metafase (entrada).
    pareados = sorted(c for c in gts if (METAFASES / f'metafase_{c}.bmp').exists())
    plausibles = [c for c in pareados
                  if opts.gt_min <= sum(gts[c].values()) <= opts.gt_max]
    print(f'cariogramas pareados: {len(pareados)} | '
          f'con total plausible {opts.gt_min}-{opts.gt_max}: {len(plausibles)} '
          f'({100 * len(plausibles) / max(1, len(pareados)):.0f}%)')
    pareados = plausibles
    if opts.casos:
        pareados = pareados[:opts.casos]
    print(f'se miden: {len(pareados)}')
    print(f'vara de comparacion: ordenar a mano = {COSTE_MANUAL} acciones\n')

    filas, peor_que_manual = [], 0
    print(f"{'caso':>6} {'GT':>4} {'det':>4} {'estr':>5} {'clase':>6} "
          f"{'naran':>6} {'resol':>6} {'ACC':>5}  veredicto")
    print('-' * 72)
    for caso in pareados:
        ruta = METAFASES / f'metafase_{caso}.bmp'
        try:
            resultado = run_pipeline(load_gray(ruta.read_bytes()))
        except Exception as exc:                          # noqa: BLE001
            print(f'{caso:>6}  fallo: {exc}')
            continue
        predichos = [(c.predicted_class, float(c.confidence_score))
                     for c in resultado.chromosomes]
        m = coste(gts[caso], predichos)
        m['caso'] = caso
        filas.append(m)
        if m['acciones'] > COSTE_MANUAL:
            peor_que_manual += 1
        veredicto = 'PEOR que a mano' if m['acciones'] > COSTE_MANUAL else 'ayuda'
        print(f"{caso:>6} {m['gt_total']:>4} {m['detectados']:>4} "
              f"{m['estructura']:>5} {m['clase']:>6} {m['naranjas']:>6} "
              f"{m['resolucion']:>6} {m['acciones']:>5}  {veredicto}")

    if not filas:
        print('\nno se midio ningun caso', file=sys.stderr)
        return 1

    acciones = sorted(f['acciones'] for f in filas)
    print('-' * 72)
    print(f'\nAcciones por caso   mediana {statistics.median(acciones):.0f} | '
          f'min {acciones[0]} | max {acciones[-1]}')
    print(f'Casos que cuestan MAS que hacerlo a mano: '
          f'{peor_que_manual}/{len(filas)} ({100 * peor_que_manual / len(filas):.0f}%)')
    for campo in ('estructura', 'clase', 'resolucion'):
        v = [f[campo] for f in filas]
        print(f'  {campo:<12} mediana {statistics.median(v):.0f}')
    print('\nRecordatorio: `clase` es una COTA INFERIOR (se comparan repartos, '
          'no objeto a objeto).')

    if opts.json:
        opts.json.write_text(json.dumps(filas, indent=2), encoding='utf-8')
        print(f'detalle en {opts.json}')
    return 0


if __name__ == '__main__':
    inicio = time.time()
    codigo = main()
    print(f'({time.time() - inicio:.0f}s)')
    raise SystemExit(codigo)
