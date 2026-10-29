/**
 * El eje de un cromosoma a partir de su silueta (DD-KARYO-008 D2, T1).
 *
 * Para enderezarlo en el cariograma hace falta saber hacia dónde apunta: el
 * eje MAYOR de la silueta, calculado con los momentos de área del polígono
 * (fórmula de Green). Con él salen también el largo y el ancho a lo largo de
 * sus ejes, que son los que valen para la escala común: la caja de un
 * cromosoma en diagonal es más corta que el cromosoma.
 *
 * La trampa (DD-KARYO-008 §1.2): las siluetas de backend-ml vienen en sentido
 * HORARIO. Así el área sale negativa y todos los momentos cambian de signo;
 * sin corregirlo, el ángulo cae en el eje menor. Las pruebas recorren cada
 * caso en los dos sentidos.
 *
 * Coordenadas de pantalla (y hacia abajo), como la metafase y Konva: un ángulo
 * positivo gira en el sentido de las agujas del reloj.
 *
 * Puro y sin dependencias: todo se prueba aquí.
 */
import type { Punto } from './medicion';
import type { Poligono } from './contornoMetafase';

/** Por debajo de este área (px²) la silueta no tiene eje: es un punto o una raya. */
export const AREA_MINIMA = 1;

/**
 * Un cromosoma cuyo largo no llega a 1,2 veces su ancho es casi redondo: su eje
 * cambiaría con un píxel de silueta, y enderezarlo lo giraría al azar (D2).
 */
export const UMBRAL_ALARGADO = 1.2;

export interface Eje {
  /** Del eje mayor respecto al eje x, en grados dentro de [0, 180). */
  angulo: number;
  /** Extensión de la silueta a lo largo del eje mayor, en px. */
  largo: number;
  /** Extensión a lo largo del eje menor, en px. */
  ancho: number;
  centro: Punto;
}

/** El eje mayor de la silueta, o `null` si tiene menos de 3 puntos o no tiene área. */
export function ejeDe(poligono: Poligono | null | undefined): Eje | null {
  if (!poligono || poligono.length < 3) return null;
  const n = poligono.length;
  let area = 0;
  let cx = 0;
  let cy = 0;
  for (let i = 0; i < n; i++) {
    const [x0, y0] = poligono[i];
    const [x1, y1] = poligono[(i + 1) % n];
    const k = x0 * y1 - x1 * y0;
    area += k;
    cx += (x0 + x1) * k;
    cy += (y0 + y1) * k;
  }
  area /= 2;
  if (!(Math.abs(area) >= AREA_MINIMA)) return null;
  cx /= 6 * area;
  cy /= 6 * area;

  let mxx = 0;
  let myy = 0;
  let mxy = 0;
  for (let i = 0; i < n; i++) {
    const x0 = poligono[i][0] - cx;
    const y0 = poligono[i][1] - cy;
    const x1 = poligono[(i + 1) % n][0] - cx;
    const y1 = poligono[(i + 1) % n][1] - cy;
    const k = x0 * y1 - x1 * y0;
    mxx += ((x0 * x0 + x0 * x1 + x1 * x1) * k) / 12;
    myy += ((y0 * y0 + y0 * y1 + y1 * y1) * k) / 12;
    mxy += ((x0 * y1 + 2 * x0 * y0 + 2 * x1 * y1 + x1 * y0) * k) / 24;
  }
  // Recorrido horario: área negativa y momentos negados. Se devuelven a su signo.
  const signo = area > 0 ? 1 : -1;
  const theta = 0.5 * Math.atan2(2 * mxy * signo, (mxx - myy) * signo);

  const ux = Math.cos(theta);
  const uy = Math.sin(theta);
  let minL = Infinity;
  let maxL = -Infinity;
  let minA = Infinity;
  let maxA = -Infinity;
  for (const [x, y] of poligono) {
    const l = (x - cx) * ux + (y - cy) * uy;
    const a = -(x - cx) * uy + (y - cy) * ux;
    minL = Math.min(minL, l);
    maxL = Math.max(maxL, l);
    minA = Math.min(minA, a);
    maxA = Math.max(maxA, a);
  }
  const angulo = (((theta * 180) / Math.PI) % 180 + 180) % 180;
  return { angulo, largo: maxL - minL, ancho: maxA - minA, centro: { x: cx, y: cy } };
}

/**
 * Los grados que hay que girar la imagen para dejar el eje mayor vertical, en
 * (−90, 90]: el giro más corto. `null` si no hay eje o el cromosoma es casi
 * redondo (D2): entonces manda la regla de siempre, de pie si la caja está tumbada.
 */
export function giroParaEnderezar(eje: Eje | null): number | null {
  if (!eje || !(eje.largo >= UMBRAL_ALARGADO * eje.ancho)) return null;
  // `angulo` está en [0, 180), así que el giro cae ya en (−90, 90].
  return 90 - eje.angulo;
}
