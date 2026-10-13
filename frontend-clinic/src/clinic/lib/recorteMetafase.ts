/**
 * Geometría del recorte sobre la metafase real (DD-KARYO-006 D7).
 *
 * El panel «Metafase» muestra una REGIÓN de la imagen —la caja del cromosoma
 * más un margen— ampliada a un tamaño fijo. El analista dibuja el recorte en
 * píxeles del panel; el servidor lo necesita en píxeles de la metafase, que es
 * lo que significa `Chromosome.bbox`.
 *
 * Esta conversión es justo lo que faltaba (§2): el recorte se dibujaba sobre el
 * cariograma y se enviaba en coordenadas de su hueco, `{x: 9, y: 18, w: 22,
 * h: 100}`, para un cromosoma que estaba en `{x: 448, y: 35, w: 175, h: 73}`.
 *
 * Puro: cada transformación se prueba aquí, ida y vuelta.
 */
import type { Caja, Dimensiones } from './encajarRecorte';

/** Margen alrededor de la caja, en proporción a su lado mayor. Deja ver a los
 * vecinos —para saber dónde termina este cromosoma— y deja sitio para AGRANDAR
 * un recorte que se quedó corto, cosa imposible dibujando dentro de la caja. */
export const MARGEN = 0.6;

/** Lado máximo del panel, en píxeles de pantalla. */
export const LADO_PANEL = 360;

/** La región de la metafase que se muestra: la caja con su margen, sin salir
 * de la imagen. */
export function regionDeRecorte(bbox: Caja, imagen: Dimensiones, margen = MARGEN): Caja {
  const extra = Math.max(bbox.w, bbox.h) * margen;
  const x = Math.max(0, bbox.x - extra);
  const y = Math.max(0, bbox.y - extra);
  const derecha = Math.min(imagen.w, bbox.x + bbox.w + extra);
  const abajo = Math.min(imagen.h, bbox.y + bbox.h + extra);
  return { x, y, w: derecha - x, h: abajo - y };
}

/** Píxeles de pantalla por píxel de metafase, para que la región quepa en el panel. */
export function escalaPanel(region: Caja, lado = LADO_PANEL): number {
  return Math.min(lado / region.w, lado / region.h);
}

/** Un rectángulo del panel, en píxeles de la metafase: lo que se envía. Se
 * redondea a píxeles enteros y se recorta a la imagen, porque el servidor
 * rechaza un bbox que se sale. */
export function aMetafase(rect: Caja, region: Caja, escala: number, imagen: Dimensiones): Caja {
  const x0 = Math.max(0, Math.round(region.x + rect.x / escala));
  const y0 = Math.max(0, Math.round(region.y + rect.y / escala));
  const x1 = Math.min(imagen.w, Math.round(region.x + (rect.x + rect.w) / escala));
  const y1 = Math.min(imagen.h, Math.round(region.y + (rect.y + rect.h) / escala));
  return { x: x0, y: y0, w: Math.max(0, x1 - x0), h: Math.max(0, y1 - y0) };
}

/** Una caja de la metafase, en píxeles del panel: para dibujar el recorte
 * actual y que el analista vea qué está corrigiendo. */
export function aPanel(bbox: Caja, region: Caja, escala: number): Caja {
  return {
    x: (bbox.x - region.x) * escala,
    y: (bbox.y - region.y) * escala,
    w: bbox.w * escala,
    h: bbox.h * escala,
  };
}
