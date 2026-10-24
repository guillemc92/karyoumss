/**
 * Presentación legible del cariograma (DD-KARYO-007 F3, T7).
 *
 * Hasta T7 cada recorte se ampliaba por separado hasta llenar su hueco: un 21
 * se veía tan alto como un 1, y el tamaño —el primer dato que mira un
 * citogenetista para ordenar los pares— se perdía. Aquí:
 *
 * - **Escala común**: todos los cromosomas a la misma escala, así que el 1
 *   sigue siendo más largo que el 21. Se calcula con el percentil 90 del
 *   largo, no con el máximo: un racimo sin separar (dos cromosomas en una
 *   caja) encogería a todos los demás. El que no quepa a esa escala se reduce
 *   solo él, hasta caber.
 * - **Línea base**: cada cromosoma se apoya en el borde inferior de su hueco,
 *   como en un cariograma impreso; los pares se comparan de un vistazo.
 * - **Orientación (D7)**: girar 180° y voltear, de presentación. El recorte, el
 *   `bbox` y el `contour` siguen en píxeles de la metafase.
 *
 * Puro y sin Konva: se prueba entero aquí.
 */
import type { Caja, Colocacion, Dimensiones } from './encajarRecorte';

export const PERCENTIL_ESCALA = 0.9;

/** Orientación de presentación de un cromosoma (D7). */
export interface Orientacion {
  giro: 0 | 180;
  volteo: boolean;
}

export const SIN_ORIENTAR: Orientacion = { giro: 0, volteo: false };

/** Lo que se ve tras el giro D8 (tumbado → de pie): el lado largo, vertical. */
export function visibleDe(recorte: Dimensiones): Dimensiones {
  return recorte.w > recorte.h ? { w: recorte.h, h: recorte.w } : recorte;
}

/** El valor del percentil `p` (0..1) de una lista; `null` si está vacía. */
export function percentil(valores: number[], p: number): number | null {
  const v = valores.filter((x) => Number.isFinite(x) && x > 0).sort((a, b) => a - b);
  if (v.length === 0) return null;
  const i = Math.min(v.length - 1, Math.max(0, Math.ceil(p * v.length) - 1));
  return v[i];
}

/**
 * Píxeles del cariograma por píxel de metafase, la misma para todos.
 *
 * La que hace caber, a lo alto y a lo ancho, al cromosoma del percentil 90.
 * `null` si no hay recortes (el lienzo pinta las cajas de color).
 */
export function escalaComun(recortes: Dimensiones[], cuerpo: Dimensiones, p = PERCENTIL_ESCALA): number | null {
  const visibles = recortes.map(visibleDe);
  const largo = percentil(visibles.map((r) => r.h), p);
  const ancho = percentil(visibles.map((r) => r.w), p);
  if (largo === null || ancho === null) return null;
  return Math.min(cuerpo.h / largo, cuerpo.w / ancho);
}

/**
 * Dónde se pinta un recorte: a la escala común (o menor, si no cabe), centrado
 * a lo ancho y apoyado en la línea base del hueco.
 */
export function colocarEnLineaBase(recorte: Dimensiones, cuerpo: Caja, escala: number): Colocacion | null {
  if (!(recorte.w > 0) || !(recorte.h > 0) || !(escala > 0)) return null;
  const tumbado = recorte.w > recorte.h;
  const visible = visibleDe(recorte);
  const s = Math.min(escala, cuerpo.w / visible.w, cuerpo.h / visible.h);
  const alto = visible.h * s;
  return {
    cx: cuerpo.x + cuerpo.w / 2,
    cy: cuerpo.y + cuerpo.h - alto / 2,
    w: recorte.w * s,
    h: recorte.h * s,
    rotacion: tumbado ? 90 : 0,
  };
}

/** La orientación guardada en `measures.orientacion`, o la neutra. */
export function orientacionDe(measures: unknown): Orientacion {
  const o = (measures as { orientacion?: Partial<Orientacion> } | null)?.orientacion;
  return { giro: o?.giro === 180 ? 180 : 0, volteo: o?.volteo === true };
}

export const girar = (o: Orientacion): Orientacion => ({ ...o, giro: o.giro === 180 ? 0 : 180 });
export const voltear = (o: Orientacion): Orientacion => ({ ...o, volteo: !o.volteo });

/**
 * Giro y espejo con los que Konva pinta la imagen. El giro D8 (tumbado → de
 * pie) se suma al de D7. El volteo es horizontal EN PANTALLA: con la imagen
 * girada 90° eso es su eje vertical, así que se aplica a `scaleY`.
 */
export function transformacionImagen(colocacion: Colocacion, o: Orientacion): {
  rotation: number; scaleX: number; scaleY: number;
} {
  const espejo = o.volteo ? -1 : 1;
  return {
    rotation: (colocacion.rotacion + o.giro) % 360,
    scaleX: colocacion.rotacion === 90 ? 1 : espejo,
    scaleY: colocacion.rotacion === 90 ? espejo : 1,
  };
}

/** Factor para que el cariograma ocupe el ancho disponible, sin pasar de `max`. */
export function factorAjuste(anchoDisponible: number, anchoLienzo: number, max = 2): number {
  if (!(anchoDisponible > 0) || !(anchoLienzo > 0)) return 1;
  return Math.max(1, Math.min(max, anchoDisponible / anchoLienzo));
}

/**
 * El marco del semáforo, ajustado a lo que se ve del cromosoma (T7).
 *
 * Con la escala común, un 21 ocupa una parte pequeña del hueco: un marco del
 * hueco entero lo haría parecer una caja vacía con algo en el fondo. El marco
 * abraza la imagen con `margen` px y nunca se sale del hueco.
 */
export function marcoVisible(colocacion: Colocacion, cuerpo: Caja, margen = 2): Caja {
  const vw = colocacion.rotacion === 90 ? colocacion.h : colocacion.w;
  const vh = colocacion.rotacion === 90 ? colocacion.w : colocacion.h;
  const x = Math.max(cuerpo.x - margen, colocacion.cx - vw / 2 - margen);
  const y = Math.max(cuerpo.y - margen, colocacion.cy - vh / 2 - margen);
  const derecha = Math.min(cuerpo.x + cuerpo.w + margen, colocacion.cx + vw / 2 + margen);
  const abajo = Math.min(cuerpo.y + cuerpo.h + margen, colocacion.cy + vh / 2 + margen);
  return { x, y, w: derecha - x, h: abajo - y };
}
