/**
 * Geometría del corte en el cliente (DD-KARYO-007 T4).
 *
 * El corte de verdad lo calcula backend-ml en ráster (§10.1). Aquí solo hace
 * falta lo que la interfaz decide ANTES de enviar:
 *
 * - si un punto cae dentro de una silueta;
 * - cuántas veces cruza la línea trazada el borde del objeto. Para separarlo,
 *   la línea tiene que entrar y salir: al menos dos cruces. Con menos, el
 *   servidor respondería 422; avisarlo mientras se traza ahorra el viaje y
 *   enseña al analista qué falta («trácela de borde a borde»).
 *
 * Puro y sin dependencias: todo se prueba aquí.
 */
import type { Punto } from './medicion';
import type { Poligono } from './contornoMetafase';

/** Distancia mínima, en px de la metafase, entre dos puntos de la línea trazada. */
export const PASO_TRAZO = 3;

/** Par-impar (ray casting). Un punto sobre el borde puede caer a cualquier lado. */
export function puntoDentro(p: Punto, poligono: Poligono): boolean {
  let dentro = false;
  for (let i = 0, j = poligono.length - 1; i < poligono.length; j = i++) {
    const [xi, yi] = poligono[i];
    const [xj, yj] = poligono[j];
    if ((yi > p.y) !== (yj > p.y) && p.x < ((xj - xi) * (p.y - yi)) / (yj - yi) + xi) dentro = !dentro;
  }
  return dentro;
}

/** ¿Se cortan los segmentos ab y cd? Los colineales y los que solo se tocan
 * en un extremo no cuentan: no separan nada. */
export function segmentosSeCortan(a: Punto, b: Punto, c: Punto, d: Punto): boolean {
  const orient = (p: Punto, q: Punto, r: Punto) => (q.x - p.x) * (r.y - p.y) - (q.y - p.y) * (r.x - p.x);
  const d1 = orient(c, d, a);
  const d2 = orient(c, d, b);
  const d3 = orient(a, b, c);
  const d4 = orient(a, b, d);
  return ((d1 > 0 && d2 < 0) || (d1 < 0 && d2 > 0)) && ((d3 > 0 && d4 < 0) || (d3 < 0 && d4 > 0));
}

/** Cuántas veces cruza la polilínea el borde del polígono. */
export function cruces(linea: Punto[], poligono: Poligono): number {
  let n = 0;
  for (let i = 1; i < linea.length; i += 1) {
    for (let k = 0, j = poligono.length - 1; k < poligono.length; j = k++) {
      const c = { x: poligono[j][0], y: poligono[j][1] };
      const d = { x: poligono[k][0], y: poligono[k][1] };
      if (segmentosSeCortan(linea[i - 1], linea[i], c, d)) n += 1;
    }
  }
  return n;
}

/** ¿Puede esta línea separar el objeto? Tiene que entrar y salir. */
export function cortaElObjeto(linea: Punto[], poligono: Poligono): boolean {
  return linea.length >= 2 && poligono.length >= 3 && cruces(linea, poligono) >= 2;
}

/**
 * Añade un punto al trazo si se alejó lo bastante del último: un arrastre
 * emite decenas de movimientos por segundo y casi todos repiten píxel.
 */
export function anadirAlTrazo(trazo: Punto[], p: Punto, paso = PASO_TRAZO): Punto[] {
  const ultimo = trazo[trazo.length - 1];
  if (ultimo && Math.hypot(p.x - ultimo.x, p.y - ultimo.y) < paso) return trazo;
  return [...trazo, p];
}
