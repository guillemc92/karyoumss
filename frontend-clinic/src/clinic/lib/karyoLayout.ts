/**
 * karyoLayout — geometría pura del cariograma para el canvas Konva (P3,
 * DD-KARYO-003 §3). Sin dependencias de React/Konva: 100% testeable en jsdom.
 *
 * Los 24 slots (1..22, X, Y) se disponen en una grilla de 12 columnas × 2 filas.
 * `slotAtPoint` es la inversa que resuelve el slot destino al soltar un
 * cromosoma arrastrado (reclasificación por drag & drop).
 */
import { CHROMOSOME_SLOTS } from '../types/karyotype';
import type { Chromosome } from '../types/karyotype';

export const COLS = 12;
export const ROWS = 2;
export const SLOT_W = 72;
export const SLOT_H = 132;
export const PAD = 8;
/** Desplazamiento horizontal por copia (position_index) dentro de un slot. */
export const CHROMO_W = 30;

export const STAGE_WIDTH = PAD * 2 + COLS * SLOT_W;
export const STAGE_HEIGHT = PAD * 2 + ROWS * SLOT_H;

export interface Point {
  x: number;
  y: number;
}

/** Esquina superior izquierda del slot (o null si el slot no existe). */
export function slotOrigin(slot: string): Point | null {
  const idx = CHROMOSOME_SLOTS.indexOf(slot);
  if (idx < 0) return null;
  const col = idx % COLS;
  const row = Math.floor(idx / COLS);
  return { x: PAD + col * SLOT_W, y: PAD + row * SLOT_H };
}

/** Posición de un cromosoma según su clase + copia (position_index). */
export function chromosomePosition(chromo: Pick<Chromosome, 'predicted_class' | 'position_index'>): Point {
  const origin = slotOrigin(chromo.predicted_class) ?? { x: PAD, y: PAD };
  return { x: origin.x + chromo.position_index * CHROMO_W, y: origin.y };
}

/** Ancho del cuerpo de un cromosoma en su hueco (ver KaryotypeCanvas). */
export const CUERPO_W = 26;

/**
 * Posición de cada cromosoma activo en el cariograma (DD-KARYO-007 T7).
 *
 * Las copias de un par se separan `CHROMO_W` mientras quepan en su hueco. Si
 * hay más copias de las que caben —la segmentación metió varios objetos en la
 * misma clase—, se comprimen DENTRO del hueco en vez de invadir el de al lado.
 * Medido el 23/10: con seis «3», las copias de más quedaban encima del par 5 y
 * un clic sobre el 5 seleccionaba un 3.
 *
 * El orden dentro del par es el de `position_index` (y `order` para desempatar),
 * no su valor: tras separar o descartar puede haber huecos en la numeración.
 */
export function posicionesCariograma(
  chromosomes: Pick<Chromosome, 'id' | 'predicted_class' | 'position_index' | 'order'>[],
): Map<string, Point> {
  const porClase = new Map<string, typeof chromosomes>();
  for (const c of chromosomes) {
    const lista = porClase.get(c.predicted_class) ?? [];
    lista.push(c);
    porClase.set(c.predicted_class, lista);
  }
  const posiciones = new Map<string, Point>();
  for (const [clase, lista] of porClase) {
    const origen = slotOrigin(clase) ?? { x: PAD, y: PAD };
    const orden = [...lista].sort((a, b) => a.position_index - b.position_index || a.order - b.order);
    const sitio = SLOT_W - CUERPO_W;   // lo que puede desplazarse la última copia
    const paso = orden.length > 1 ? Math.min(CHROMO_W, sitio / (orden.length - 1)) : 0;
    orden.forEach((c, i) => posiciones.set(c.id, { x: origen.x + i * paso, y: origen.y }));
  }
  return posiciones;
}

/** Slot bajo un punto del stage, o null si cae fuera de la grilla. */
export function slotAtPoint(x: number, y: number): string | null {
  const col = Math.floor((x - PAD) / SLOT_W);
  const row = Math.floor((y - PAD) / SLOT_H);
  if (col < 0 || col >= COLS || row < 0 || row >= ROWS) return null;
  const idx = row * COLS + col;
  return CHROMOSOME_SLOTS[idx] ?? null;
}

/**
 * Clase destino de un drop, o null si el punto cae fuera de la grilla o sobre
 * el mismo slot del cromosoma (drag sin cambio → no reclasifica).
 */
export function reclassifyTargetFromDrop(
  x: number,
  y: number,
  chromo: Pick<Chromosome, 'predicted_class'>,
): string | null {
  const target = slotAtPoint(x, y);
  if (target && target !== chromo.predicted_class) return target;
  return null;
}
