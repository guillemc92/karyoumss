"""Fase C1 — extracción de etiquetas de los cariogramas ORDENADOS (ADR-0007).

El cariograma (SCAAnalisisCariotipos.ImagenCariotipo) es la disposición estándar
del experto: 4 filas, la POSICIÓN en la grilla = la clase. Se parsea la grilla
(segmentar → 4 filas → celdas por gaps en X → clase por orden estándar) y se
recorta cada cromosoma etiquetado con su clase.

QC: se descarta la imagen si no tiene 4 filas o si las filas 1-3 (clases 1-18,
conteo fijo 5/7/6) no cuadran — así las etiquetas 1-18 quedan limpias. La fila 4
(19-22/X/Y, variable por sexo/trisomías) es best-effort.

Uso:
  python extract_labels.py            # procesa datasets/metaclass/cariogramas/*
  python extract_labels.py --viz N    # dibuja el etiquetado de cario_N.bmp
"""
from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

DATASET = Path(__file__).resolve().parents[2] / 'datasets' / 'metaclass'
CARIO_DIR = DATASET / 'cariogramas'
CROPS_DIR = DATASET / 'crops'

ROW_CLASSES = [
    ['1', '2', '3', '4', '5'],
    ['6', '7', '8', '9', '10', '11', '12'],
    ['13', '14', '15', '16', '17', '18'],
    ['19', '20', '21', '22', 'X', 'Y'],
]


def segment_chromosomes(gray: np.ndarray) -> list[tuple[int, int, int, int]]:
    _, bw = cv2.threshold(cv2.medianBlur(gray, 3), 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    bw = cv2.morphologyEx(bw, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
    n, _, st, _ = cv2.connectedComponentsWithStats(bw, 8)
    boxes = []
    for i in range(1, n):
        x, y, w, h, a = st[i]
        if a < 350 or h < 22:          # descarta texto/specks
            continue
        if h <= 5 and w > 20:          # descarta subrayados
            continue
        boxes.append((int(x), int(y), int(w), int(h)))
    return boxes


def _cluster_by(vals_boxes, key, gap):
    """Agrupa boxes ordenados por `key` cuando el salto supera `gap`."""
    items = sorted(vals_boxes, key=key)
    groups, cur = [], [items[0]]
    for b in items[1:]:
        if key(b) - key(cur[-1]) > gap:
            groups.append(cur)
            cur = [b]
        else:
            cur.append(b)
    groups.append(cur)
    return groups


def _split_into_n_cells(row_boxes, n):
    """Corta la fila en EXACTAMENTE n celdas por los (n-1) gaps más grandes
    entre centros-x (robusto: usa el conteo conocido de la grilla estándar)."""
    items = sorted(row_boxes, key=lambda b: b[0] + b[2] / 2)
    if len(items) < n:
        return None
    cx = [b[0] + b[2] / 2 for b in items]
    gaps = sorted(((cx[i + 1] - cx[i], i) for i in range(len(cx) - 1)), reverse=True)
    boundaries = sorted(i for _, i in gaps[:n - 1])
    cells, start = [], 0
    for b in boundaries:
        cells.append(items[start:b + 1])
        start = b + 1
    cells.append(items[start:])
    return cells


def parse_karyogram(gray: np.ndarray):
    boxes = segment_chromosomes(gray)
    if len(boxes) < 30:
        return None
    med_h = int(np.median([b[3] for b in boxes]))
    med_w = int(np.median([b[2] for b in boxes]))
    rows = _cluster_by(boxes, key=lambda b: b[1] + b[3] / 2, gap=med_h * 0.9)
    if len(rows) != 4:
        return None

    labeled: list[tuple[str, tuple[int, int, int, int]]] = []
    for ri, row in enumerate(rows):
        expected = ROW_CLASSES[ri]
        if ri < 3:
            # Clases 1-18: conteo fijo (5/7/6) → corte por top-K gaps (robusto).
            cells = _split_into_n_cells(row, len(expected))
            if cells is None:
                return None  # QC: no hay suficientes cromosomas para las celdas
        else:
            # Fila 4 (19-22/X/Y): variable por sexo/trisomía → gap-threshold, best-effort.
            cells = _cluster_by(row, key=lambda b: b[0] + b[2] / 2, gap=med_w * 1.6)
        for ci, cell in enumerate(cells):
            if ci >= len(expected):
                break
            cls = expected[ci]
            for box in cell:
                labeled.append((cls, box))
    return labeled


def run_extract():
    CROPS_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(CARIO_DIR.glob('*.bmp'))
    manifest = []
    ok = fail = 0
    counts: Counter = Counter()
    for f in files:
        gray = cv2.imread(str(f), cv2.IMREAD_GRAYSCALE)
        if gray is None:
            continue
        parsed = parse_karyogram(gray)
        if parsed is None:
            fail += 1
            continue
        ok += 1
        cid = f.stem.replace('cario_', '')
        for idx, (cls, (x, y, w, h)) in enumerate(parsed):
            crop = gray[y:y + h, x:x + w]
            (CROPS_DIR / cls).mkdir(parents=True, exist_ok=True)
            name = f'{cls}/cario{cid}_{idx}.png'
            cv2.imwrite(str(CROPS_DIR / name), crop)
            manifest.append({'file': name, 'class': cls, 'source': f.name})
            counts[cls] += 1
    with open(DATASET / 'crops_manifest.csv', 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=['file', 'class', 'source'])
        w.writeheader()
        w.writerows(manifest)
    print(f'cariogramas OK={ok} descartados(QC)={fail} de {len(files)}')
    print(f'crops etiquetados: {sum(counts.values())}')
    order = [str(n) for n in range(1, 23)] + ['X', 'Y']
    print('por clase:', {c: counts.get(c, 0) for c in order})


def run_viz(cid: int):
    f = CARIO_DIR / f'cario_{cid}.bmp'
    gray = cv2.imread(str(f), cv2.IMREAD_GRAYSCALE)
    parsed = parse_karyogram(gray)
    vis = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    if parsed is None:
        print('QC FALLÓ para', cid)
    else:
        for cls, (x, y, w, h) in parsed:
            cv2.rectangle(vis, (x, y), (x + w, y + h), (0, 140, 255), 2)
            cv2.putText(vis, cls, (x, y - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
        print(f'cario {cid}: {len(parsed)} cromosomas etiquetados')
    out = Path.cwd() / f'viz_cario_{cid}.png'
    cv2.imwrite(str(out), vis)
    print('viz ->', out)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--viz', type=int, default=None)
    args = ap.parse_args()
    if args.viz is not None:
        run_viz(args.viz)
    else:
        run_extract()
