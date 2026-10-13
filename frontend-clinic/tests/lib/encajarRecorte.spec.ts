import { describe, expect, it } from 'vitest';
import { encajarRecorte, recorteValido } from '../../src/clinic/lib/encajarRecorte';

const CUERPO = { x: 2, y: 10, w: 22, h: 100 };

describe('encajarRecorte (DD-KARYO-006)', () => {
  it('un cromosoma vertical llena el alto y se centra en el ancho', () => {
    const c = encajarRecorte({ w: 11, h: 100 }, CUERPO)!;
    expect(c).toEqual({ x: 7.5, y: 10, w: 11, h: 100 });
  });

  it('un cromosoma ancho llena el ancho y se centra en el alto', () => {
    const c = encajarRecorte({ w: 44, h: 20 }, CUERPO)!;
    expect(c.w).toBe(22);
    expect(c.h).toBe(10);
    expect(c.y).toBe(10 + (100 - 10) / 2);
  });

  it('conserva la relación de aspecto: no estira ni aplasta el cromosoma', () => {
    for (const r of [{ w: 37, h: 81 }, { w: 90, h: 31 }, { w: 22, h: 100 }, { w: 5, h: 5 }]) {
      const c = encajarRecorte(r, CUERPO)!;
      expect(c.w / c.h).toBeCloseTo(r.w / r.h, 10);
      expect(c.w).toBeLessThanOrEqual(CUERPO.w + 1e-9);
      expect(c.h).toBeLessThanOrEqual(CUERPO.h + 1e-9);
    }
  });

  it('un recorte o un destino sin área no se pinta', () => {
    expect(encajarRecorte({ w: 0, h: 10 }, CUERPO)).toBeNull();
    expect(encajarRecorte({ w: 10, h: -1 }, CUERPO)).toBeNull();
    expect(encajarRecorte({ w: NaN, h: 10 }, CUERPO)).toBeNull();
    expect(encajarRecorte({ w: 10, h: 10 }, { ...CUERPO, w: 0 })).toBeNull();
  });
});

describe('recorteValido', () => {
  const IMG = { w: 1024, h: 768 };

  it('acepta un bbox dentro de la imagen, incluido el que toca el borde', () => {
    expect(recorteValido({ x: 10, y: 20, w: 30, h: 40 }, IMG)).toBe(true);
    expect(recorteValido({ x: 994, y: 728, w: 30, h: 40 }, IMG)).toBe(true);
  });

  it('rechaza el que se sale de la metafase: recortaría píxeles que no existen', () => {
    expect(recorteValido({ x: 1000, y: 0, w: 30, h: 40 }, IMG)).toBe(false);
    expect(recorteValido({ x: 0, y: 740, w: 30, h: 40 }, IMG)).toBe(false);
    expect(recorteValido({ x: -1, y: 0, w: 30, h: 40 }, IMG)).toBe(false);
  });

  it('rechaza el bbox vacío de los casos anteriores a P3 y los incompletos', () => {
    expect(recorteValido({}, IMG)).toBe(false);
    expect(recorteValido(null, IMG)).toBe(false);
    expect(recorteValido(undefined, IMG)).toBe(false);
    expect(recorteValido({ x: 0, y: 0, w: 30 }, IMG)).toBe(false);
    expect(recorteValido({ x: 0, y: 0, w: 0, h: 40 }, IMG)).toBe(false);
    expect(recorteValido({ x: 0, y: 0, w: Infinity, h: 40 }, IMG)).toBe(false);
  });
});
