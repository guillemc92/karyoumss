/**
 * Dónde y a qué tamaño se pinta el recorte de un cromosoma dentro de su caja
 * del cariograma (DD-KARYO-006 T3 y D8).
 *
 * El recorte es el `bbox` del cromosoma en píxeles de la metafase; la caja es
 * el hueco fijo que el cromosoma ocupa en su par (22 × 100). Se escala para
 * caber entero conservando la relación de aspecto —un cromosoma estirado o
 * aplastado se mediría mal y cambiaría su morfología aparente— y se centra.
 *
 * Puro y sin Konva: la geometría se prueba entera aquí y el lienzo solo la usa.
 */
export interface Caja {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface Dimensiones {
  w: number;
  h: number;
}

/** Cómo pintar el recorte con Konva: centro, tamaño de la imagen ANTES de girar
 * y giro. Konva gira alrededor del origen del nodo; con el desplazamiento a la
 * mitad, gira alrededor de su centro y el centro queda donde se pide. */
export interface Colocacion {
  cx: number;
  cy: number;
  w: number;
  h: number;
  rotacion: 0 | 90;
}

/** La caja dentro de `destino` que ocupa el recorte, o `null` si el recorte
 * no tiene área (un bbox degenerado no se puede pintar: se pinta el rectángulo). */
export function encajarRecorte(recorte: Dimensiones, destino: Caja): Caja | null {
  if (!(recorte.w > 0) || !(recorte.h > 0) || !(destino.w > 0) || !(destino.h > 0)) return null;
  const escala = Math.min(destino.w / recorte.w, destino.h / recorte.h);
  const w = recorte.w * escala;
  const h = recorte.h * escala;
  return { x: destino.x + (destino.w - w) / 2, y: destino.y + (destino.h - h) / 2, w, h };
}

/**
 * D8: un cromosoma tumbado (más ancho que alto) se gira 90° para mostrarlo de
 * pie. Medido el 13/10: el 61 % de los reales están tumbados y, sin girar,
 * ocupaban una mediana de 18 px de los 100 del hueco.
 *
 * El giro es solo de presentación: el recorte de la metafase es el mismo y el
 * `bbox` no cambia. Tampoco decide cuál de los extremos es el brazo p —eso es
 * orientar según ISCN, otra especificación—, así que puede quedar cabeza abajo.
 */
export function colocarRecorte(recorte: Dimensiones, destino: Caja): Colocacion | null {
  const tumbado = recorte.w > recorte.h;
  // Lo que se ve tras girar tiene las dimensiones intercambiadas.
  const visible = tumbado ? { w: recorte.h, h: recorte.w } : recorte;
  const caja = encajarRecorte(visible, destino);
  if (!caja) return null;
  const escala = caja.w / visible.w;
  return {
    cx: caja.x + caja.w / 2,
    cy: caja.y + caja.h / 2,
    w: recorte.w * escala,
    h: recorte.h * escala,
    rotacion: tumbado ? 90 : 0,
  };
}

/** ¿Tiene este cromosoma un recorte utilizable dentro de la imagen? Un bbox
 * que se sale de la metafase recortaría píxeles inexistentes. */
export function recorteValido(
  bbox: Partial<Caja> | null | undefined,
  imagen: Dimensiones,
): bbox is Caja {
  if (!bbox) return false;
  const { x, y, w, h } = bbox;
  if ([x, y, w, h].some((v) => typeof v !== 'number' || !Number.isFinite(v))) return false;
  return (w as number) > 0 && (h as number) > 0 && (x as number) >= 0 && (y as number) >= 0
    && (x as number) + (w as number) <= imagen.w && (y as number) + (h as number) <= imagen.h;
}
