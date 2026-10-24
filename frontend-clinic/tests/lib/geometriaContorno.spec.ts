import { describe, expect, it } from 'vitest';
import {
  PASO_TRAZO,
  anadirAlTrazo,
  cortaElObjeto,
  cruces,
  puntoDentro,
  segmentosSeCortan,
} from '../../src/clinic/lib/geometriaContorno';

/** Geometría del corte en el cliente (DD-KARYO-007 T4). */
const CUADRADO = [[0, 0], [10, 0], [10, 10], [0, 10]];
// Una «L»: la línea que la atraviesa por el codo la cruza más veces.
const ELE = [[0, 0], [4, 0], [4, 6], [10, 6], [10, 10], [0, 10]];
const p = (x: number, y: number) => ({ x, y });

describe('puntoDentro', () => {
  it('dentro y fuera', () => {
    expect(puntoDentro(p(5, 5), CUADRADO)).toBe(true);
    expect(puntoDentro(p(15, 5), CUADRADO)).toBe(false);
    expect(puntoDentro(p(-1, -1), CUADRADO)).toBe(false);
  });
  it('en un polígono cóncavo, el hueco de la L está fuera', () => {
    expect(puntoDentro(p(7, 3), ELE)).toBe(false);
    expect(puntoDentro(p(2, 3), ELE)).toBe(true);
  });
});

describe('segmentosSeCortan', () => {
  it('dos segmentos en cruz se cortan', () => {
    expect(segmentosSeCortan(p(0, 5), p(10, 5), p(5, 0), p(5, 10))).toBe(true);
  });
  it('paralelos, separados o tocándose en un extremo, no', () => {
    expect(segmentosSeCortan(p(0, 0), p(10, 0), p(0, 1), p(10, 1))).toBe(false);
    expect(segmentosSeCortan(p(0, 0), p(4, 0), p(5, -1), p(5, 1))).toBe(false);
    expect(segmentosSeCortan(p(0, 0), p(5, 0), p(5, 0), p(5, 5))).toBe(false);
  });
});

describe('cruces y cortaElObjeto', () => {
  it('una línea de borde a borde cruza dos veces y corta', () => {
    const linea = [p(-2, 5), p(12, 5)];
    expect(cruces(linea, CUADRADO)).toBe(2);
    expect(cortaElObjeto(linea, CUADRADO)).toBe(true);
  });
  it('una diagonal también', () => {
    expect(cortaElObjeto([p(-1, 1), p(11, 8)], CUADRADO)).toBe(true);
  });
  it('una línea que se queda a medias no corta', () => {
    const linea = [p(-2, 5), p(5, 5)];
    expect(cruces(linea, CUADRADO)).toBe(1);
    expect(cortaElObjeto(linea, CUADRADO)).toBe(false);
  });
  it('una línea fuera del objeto no corta', () => {
    expect(cortaElObjeto([p(20, 0), p(20, 10)], CUADRADO)).toBe(false);
  });
  it('una polilínea en zigzag cuenta todos sus cruces', () => {
    expect(cruces([p(3, -1), p(3, 11), p(7, 11), p(7, -1)], CUADRADO)).toBe(4);
  });
  it('sin dos puntos o sin polígono no hay corte', () => {
    expect(cortaElObjeto([p(1, 1)], CUADRADO)).toBe(false);
    expect(cortaElObjeto([p(-2, 5), p(12, 5)], [[0, 0], [1, 1]])).toBe(false);
  });
});

describe('anadirAlTrazo', () => {
  it('ignora los movimientos que no se alejan del último punto', () => {
    let t = anadirAlTrazo([], p(0, 0));
    t = anadirAlTrazo(t, p(1, 1));
    expect(t).toHaveLength(1);
    t = anadirAlTrazo(t, p(PASO_TRAZO, 0));
    expect(t).toHaveLength(2);
  });
});
