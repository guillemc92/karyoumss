import { describe, expect, it } from 'vitest';
import {
  LADO_PANEL, MARGEN, aMetafase, aPanel, escalaPanel, regionDeRecorte,
} from '../../src/clinic/lib/recorteMetafase';

const IMG = { w: 1024, h: 768 };
// El cromosoma con el que se reprodujo el defecto el 13/10.
const CUMULO = { x: 448, y: 35, w: 175, h: 73 };

describe('regionDeRecorte', () => {
  it('añade el margen por los cuatro lados, proporcional al lado mayor', () => {
    const r = regionDeRecorte({ x: 500, y: 300, w: 30, h: 60 }, IMG);
    const extra = 60 * MARGEN;
    expect(r).toEqual({ x: 500 - extra, y: 300 - extra, w: 30 + 2 * extra, h: 60 + 2 * extra });
  });

  it('no sale de la imagen: junto al borde se recorta', () => {
    const r = regionDeRecorte(CUMULO, IMG);   // y = 35, el margen de 105 se saldría por arriba
    expect(r.y).toBe(0);
    expect(r.x).toBeGreaterThanOrEqual(0);
    expect(r.x + r.w).toBeLessThanOrEqual(IMG.w);
    expect(r.y + r.h).toBeLessThanOrEqual(IMG.h);
  });

  it('siempre contiene la caja entera', () => {
    for (const b of [CUMULO, { x: 0, y: 0, w: 40, h: 40 }, { x: 1000, y: 740, w: 24, h: 28 }]) {
      const r = regionDeRecorte(b, IMG);
      expect(r.x).toBeLessThanOrEqual(b.x);
      expect(r.y).toBeLessThanOrEqual(b.y);
      expect(r.x + r.w).toBeGreaterThanOrEqual(b.x + b.w);
      expect(r.y + r.h).toBeGreaterThanOrEqual(b.y + b.h);
    }
  });
});

describe('escalaPanel', () => {
  it('la región cabe entera en el panel por su lado mayor', () => {
    const e = escalaPanel({ x: 0, y: 0, w: 180, h: 90 });
    expect(e).toBe(LADO_PANEL / 180);
  });

  it('un cromosoma pequeño se AMPLÍA para poder recortarlo con precisión', () => {
    expect(escalaPanel(regionDeRecorte({ x: 500, y: 300, w: 30, h: 60 }, IMG))).toBeGreaterThan(2);
  });
});

describe('aMetafase / aPanel', () => {
  const region = regionDeRecorte(CUMULO, IMG);
  const escala = escalaPanel(region);

  it('ida y vuelta: la caja actual vuelve a ser ella misma', () => {
    expect(aMetafase(aPanel(CUMULO, region, escala), region, escala, IMG)).toEqual(CUMULO);
  });

  it('dibujar justo encima del cromosoma envía SU caja, no la del hueco del cariograma', () => {
    // El defecto del 13/10, convertido en regresión.
    const enviado = aMetafase(aPanel(CUMULO, region, escala), region, escala, IMG);
    expect(enviado).not.toEqual({ x: 9, y: 18, w: 22, h: 100 });
    expect(enviado.x).toBe(448);
  });

  it('dibujar la mitad izquierda recorta la mitad izquierda del cúmulo', () => {
    const p = aPanel(CUMULO, region, escala);
    const mitad = aMetafase({ ...p, w: p.w / 2 }, region, escala, IMG);
    expect(mitad.x).toBe(448);
    // 87,5 px redondeados a píxel entero: la precisión del recorte es de 1 px.
    expect(Math.abs(mitad.w - 175 / 2)).toBeLessThanOrEqual(1);
  });

  it('se puede AGRANDAR un recorte que se quedó corto: más allá de la caja actual', () => {
    const p = aPanel(CUMULO, region, escala);
    const mayor = aMetafase({ x: p.x - 20, y: p.y, w: p.w + 40, h: p.h }, region, escala, IMG);
    expect(mayor.x).toBeLessThan(448);
    expect(mayor.w).toBeGreaterThan(175);
  });

  it('se redondea a píxeles enteros y nunca sale de la imagen', () => {
    const r = aMetafase({ x: -50, y: -50, w: 10000, h: 10000 }, { x: 900, y: 700, w: 124, h: 68 }, 1.7, IMG);
    expect(Number.isInteger(r.x) && Number.isInteger(r.w)).toBe(true);
    expect(r.x).toBeGreaterThanOrEqual(0);
    expect(r.x + r.w).toBeLessThanOrEqual(IMG.w);
    expect(r.y + r.h).toBeLessThanOrEqual(IMG.h);
  });

  it('un rectángulo totalmente fuera de la imagen da un bbox sin área', () => {
    const r = aMetafase({ x: 5000, y: 5000, w: 10, h: 10 }, region, escala, IMG);
    expect(r.w === 0 || r.h === 0).toBe(true);
  });
});
