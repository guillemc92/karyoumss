import { describe, expect, it } from 'vitest';
import { AREA_MINIMA, UMBRAL_ALARGADO, ejeDe, giroParaEnderezar } from '../../src/clinic/lib/ejeCromosoma';

/** El eje de un cromosoma a partir de su silueta (DD-KARYO-008 T1). */

/** Rectángulo w × h centrado en (cx, cy) y girado `grados` (y hacia abajo), antihorario en pantalla. */
function rectangulo(w: number, h: number, grados: number, cx = 0, cy = 0): number[][] {
  const a = (grados * Math.PI) / 180;
  return [[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2], [-w / 2, h / 2]].map(([x, y]) => [
    cx + x * Math.cos(a) - y * Math.sin(a),
    cy + x * Math.sin(a) + y * Math.cos(a),
  ]);
}

const SENTIDOS = [
  ['tal cual', (p: number[][]) => p],
  // Las siluetas de backend-ml vienen así: la trampa de §1.2.
  ['al revés', (p: number[][]) => [...p].reverse()],
] as const;

/** Igualdad de ángulos de eje: 0° y 180° son el mismo eje. */
function mismoEje(a: number, b: number) {
  const d = Math.abs(((a - b) % 180 + 180) % 180);
  return Math.min(d, 180 - d);
}

describe('ejeDe', () => {
  describe.each(SENTIDOS)('recorrido %s', (_, sentido) => {
    it.each([0, 30, 90, -45, 120])('un rectángulo 10 × 100 girado %s° tiene su eje mayor a 90° + el giro', (giro) => {
      const eje = ejeDe(sentido(rectangulo(10, 100, giro, 300, 200)));
      expect(eje).not.toBeNull();
      expect(mismoEje(eje!.angulo, 90 + giro)).toBeLessThan(1e-6);
    });

    it('largo y ancho son los del rectángulo, no los de su caja', () => {
      // A 45° la caja de un 10 × 100 mide ~78 × 78: el largo real es 100.
      const eje = ejeDe(sentido(rectangulo(10, 100, 45)))!;
      expect(eje.largo).toBeCloseTo(100, 6);
      expect(eje.ancho).toBeCloseTo(10, 6);
    });

    it('el centro es el centroide del área', () => {
      const eje = ejeDe(sentido(rectangulo(10, 100, 30, 300, 200)))!;
      expect(eje.centro.x).toBeCloseTo(300, 6);
      expect(eje.centro.y).toBeCloseTo(200, 6);
    });
  });

  it('el ángulo queda siempre en [0, 180)', () => {
    for (const giro of [-170, -90, -1, 0, 1, 89, 90, 179, 270]) {
      const { angulo } = ejeDe(rectangulo(10, 100, giro))!;
      expect(angulo).toBeGreaterThanOrEqual(0);
      expect(angulo).toBeLessThan(180);
    }
  });

  it('una silueta con forma de cromosoma (no rectangular) también da su eje', () => {
    // Un rombo alargado en diagonal: puntas en (0,0) y (60,60), cintura estrecha.
    const rombo = [[0, 0], [34, 26], [60, 60], [26, 34]];
    expect(mismoEje(ejeDe(rombo)!.angulo, 45)).toBeLessThan(1e-6);
  });

  it('sin silueta, con menos de 3 puntos o sin área, no hay eje', () => {
    expect(ejeDe(null)).toBeNull();
    expect(ejeDe(undefined)).toBeNull();
    expect(ejeDe([])).toBeNull();
    expect(ejeDe([[0, 0], [10, 10]])).toBeNull();
    expect(ejeDe([[0, 0], [10, 10], [20, 20]])).toBeNull(); // colineales
    expect(ejeDe([[0, 0], [0.5, 0], [0, 0.5]])).toBeNull(); // área 0,125 < AREA_MINIMA
    expect(AREA_MINIMA).toBe(1);
  });

  it('con coordenadas no numéricas no hay eje', () => {
    expect(ejeDe([[0, 0], [10, Number.NaN], [0, 10]])).toBeNull();
  });
});

describe('giroParaEnderezar', () => {
  it.each([
    [0, 0], // ya de pie
    [90, 90], // tumbado: −90 y +90 dejan el mismo eje; el intervalo elige +90
    [30, -30],
    [-30, 30],
    [45, -45],
    [-45, 45],
  ])('un 10 × 100 girado %s° se endereza girando la imagen %s°', (giro, esperado) => {
    const g = giroParaEnderezar(ejeDe(rectangulo(10, 100, giro)));
    expect(g).toBeCloseTo(esperado, 6);
  });

  it('el giro es el más corto: siempre en (−90, 90]', () => {
    for (let giro = -179; giro <= 180; giro += 7) {
      for (const [, sentido] of SENTIDOS) {
        const g = giroParaEnderezar(ejeDe(sentido(rectangulo(10, 100, giro))))!;
        expect(g).toBeGreaterThan(-90);
        expect(g).toBeLessThanOrEqual(90);
        expect(mismoEje(90 + giro + g, 90)).toBeLessThan(1e-6);
      }
    }
  });

  it('un casi redondo no se endereza (D2)', () => {
    // 50 × 59: largo 1,18 veces el ancho, por debajo del umbral.
    expect(giroParaEnderezar(ejeDe(rectangulo(50, 59, 30)))).toBeNull();
    // 50 × 61: 1,22 veces, por encima, sí.
    expect(giroParaEnderezar(ejeDe(rectangulo(50, 61, 30)))).not.toBeNull();
    expect(UMBRAL_ALARGADO).toBe(1.2);
  });

  it('sin eje, no hay giro', () => {
    expect(giroParaEnderezar(null)).toBeNull();
  });
});
