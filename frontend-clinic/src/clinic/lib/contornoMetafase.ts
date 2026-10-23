/**
 * Geometría del editor de metafase (DD-KARYO-007 F1, T2).
 *
 * El editor pinta la metafase entera, ajustada al ancho del visor, y encima el
 * contorno de cada cromosoma en PÍXELES DE LA METAFASE (`Chromosome.contour`,
 * calculado por backend-ml en T1). El Stage de Konva lleva la escala total
 * —ajuste × zoom— y el desplazamiento, así que los contornos se pintan tal cual
 * llegan del servidor, sin convertir punto a punto.
 *
 * Puro: todo lo que decide qué se ve y dónde se prueba aquí.
 */
import type { Chromosome } from '../types/karyotype';
import { recorteValido, type Dimensiones } from './encajarRecorte';
import type { Punto } from './medicion';

export const ZOOM_MIN = 1;
export const ZOOM_MAX = 8;
/** Cada paso de zoom multiplica (o divide) por este factor. */
export const PASO_ZOOM = 1.5;

/** Polígono `[[x, y], …]` en píxeles de la metafase. */
export type Poligono = number[][];

/** Escala de ajuste: la metafase cabe en `max` sin ampliarse nunca. */
export function escalaAjuste(imagen: Dimensiones, max: Dimensiones): number {
  if (!(imagen.w > 0) || !(imagen.h > 0)) return 1;
  return Math.min(1, max.w / imagen.w, max.h / imagen.h);
}

/**
 * El polígono que se pinta para un cromosoma.
 *
 * El contorno real si lo hay; si no, las cuatro esquinas de su caja. La caja es
 * lo que se veía antes de T1 y sigue siendo lo que se ve si backend-ml no pudo
 * calcular la silueta (RN-07): el analista nunca se queda sin objeto que tocar.
 * `null` si tampoco hay una caja dentro de la imagen.
 */
export function poligonoDe(c: Pick<Chromosome, 'contour' | 'bbox'>, imagen: Dimensiones): Poligono | null {
  if (Array.isArray(c.contour) && c.contour.length >= 3) return c.contour;
  if (!recorteValido(c.bbox as Record<string, number>, imagen)) return null;
  const { x, y, w, h } = c.bbox as { x: number; y: number; w: number; h: number };
  return [[x, y], [x + w, y], [x + w, y + h], [x, y + h]];
}

/** `[[x, y], …]` → `[x, y, x, y, …]`, el formato de `points` de Konva. */
export function puntosPlanos(poligono: Poligono): number[] {
  return poligono.flatMap(([x, y]) => [x, y]);
}

/** Centro de masas de los vértices: donde va la etiqueta de la clase. */
export function centroDe(poligono: Poligono): Punto {
  const n = poligono.length;
  const sx = poligono.reduce((s, [x]) => s + x, 0);
  const sy = poligono.reduce((s, [, y]) => s + y, 0);
  return { x: sx / n, y: sy / n };
}

/**
 * ¿Hay que pedirle al servidor los contornos que faltan?
 *
 * Solo los casos segmentados antes de T1 tienen cromosomas activos con caja y
 * sin contorno. Los inactivos (absorbidos por un JOIN) no se pintan y no cuentan.
 */
export function faltanContornos(chromosomes: Pick<Chromosome, 'contour' | 'bbox' | 'is_active'>[]): boolean {
  return chromosomes.some((c) => {
    if (!c.is_active || (Array.isArray(c.contour) && c.contour.length >= 3)) return false;
    const b = c.bbox as Partial<Record<'w' | 'h', number>> | null;
    return Boolean(b && Number(b.w) > 0 && Number(b.h) > 0);
  });
}

export function limitarZoom(zoom: number): number {
  return Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, zoom));
}

/**
 * El desplazamiento del Stage, sin dejar ver fuera de la metafase.
 *
 * Con zoom 1 la imagen ocupa el Stage entero y el único valor posible es 0.
 * Con zoom z, la imagen mide z veces el Stage y puede moverse hasta que su
 * borde coincida con el del Stage: x ∈ [lienzo.w · (1 − z), 0].
 */
export function limitarDesplazamiento(pos: Punto, lienzo: Dimensiones, zoom: number): Punto {
  const minX = lienzo.w * (1 - zoom);
  const minY = lienzo.h * (1 - zoom);
  return {
    x: Math.min(0, Math.max(minX, pos.x)),
    y: Math.min(0, Math.max(minY, pos.y)),
  };
}

/**
 * Cambiar el zoom sin que se mueva el punto `ancla` (en píxeles del Stage).
 *
 * Es lo que se espera de la rueda: lo que está bajo el cursor se queda bajo el
 * cursor. Con los botones el ancla es el centro del lienzo.
 */
export function zoomEnPunto(
  pos: Punto,
  zoomPrevio: number,
  zoomNuevo: number,
  ancla: Punto,
  lienzo: Dimensiones,
): Punto {
  const z = limitarZoom(zoomNuevo);
  const factor = z / zoomPrevio;
  return limitarDesplazamiento(
    { x: ancla.x - (ancla.x - pos.x) * factor, y: ancla.y - (ancla.y - pos.y) * factor },
    lienzo,
    z,
  );
}

/**
 * Desplazamiento que pone `punto` (en píxeles de la metafase) en el centro del
 * lienzo. Al seleccionar un cromosoma en el cariograma con zoom puesto, el
 * editor lo trae a la vista: si no, la selección ocurre fuera de pantalla.
 */
export function centrarEn(punto: Punto, escalaTotal: number, lienzo: Dimensiones, zoom: number): Punto {
  return limitarDesplazamiento(
    { x: lienzo.w / 2 - punto.x * escalaTotal, y: lienzo.h / 2 - punto.y * escalaTotal },
    lienzo,
    zoom,
  );
}
