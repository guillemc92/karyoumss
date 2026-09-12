/**
 * recorte — geometría del rectángulo de recorte manual (RECROP).
 *
 * ## Por qué existe esta herramienta
 *
 * La segmentación por watershed sub-segmenta: dos cromosomas solapados salen
 * como una sola detección. Ese recorte malo es el origen medido de las falsas
 * «clase 1» —un cúmulo es más grande que cualquier cromosoma, y la clase 1 es
 * la más grande—. Corregir el recorte y volver a clasificar es la vía manual
 * para arreglar justamente esos casos, sin esperar a un segmentador mejor.
 *
 * ## Por qué se normaliza
 *
 * Un analista arrastra en las cuatro direcciones; hacia arriba y a la izquierda
 * el punto final tiene coordenadas menores que el inicial y la resta sale
 * negativa. El servidor exige ancho y alto positivos, así que el rectángulo se
 * normaliza aquí: el origen es siempre la esquina superior izquierda.
 *
 * Las coordenadas son **píxeles de la metafase**, no de pantalla. La conversión
 * la hace el lienzo deshaciendo zoom, rotación y desplazamiento antes de
 * llamar a estas funciones; si no, recortar con la vista ampliada guardaría una
 * región distinta de la que el analista ve.
 */
import type { Punto } from './medicion';

export interface Rectangulo {
  x: number;
  y: number;
  w: number;
  h: number;
}

/**
 * Lado mínimo, en píxeles de imagen, para tomar el arrastre por un recorte.
 *
 * Distingue un recorte de un clic accidental: por debajo de esto no hay
 * cromosoma que clasificar, solo ruido.
 */
export const RECORTE_MIN = 8;

/** Rectángulo normalizado entre dos esquinas, en cualquier orden. */
export function rectanguloDeRecorte(inicio: Punto, fin: Punto): Rectangulo {
  return {
    x: Math.round(Math.min(inicio.x, fin.x)),
    y: Math.round(Math.min(inicio.y, fin.y)),
    w: Math.round(Math.abs(fin.x - inicio.x)),
    h: Math.round(Math.abs(fin.y - inicio.y)),
  };
}

/** ¿El arrastre da un recorte utilizable, o fue un clic suelto? */
export function esRecorteUtil(rect: Rectangulo): boolean {
  return rect.w >= RECORTE_MIN && rect.h >= RECORTE_MIN;
}
