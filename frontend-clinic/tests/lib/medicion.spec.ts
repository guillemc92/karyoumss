/**
 * Tests de la medición citogenética.
 *
 * Los casos no son inventados: son las morfologías reales de cromosomas humanos
 * concretos, con las proporciones que da la literatura. Si estos pasan, la
 * herramienta mide lo que un citogenetista espera medir.
 */
import { describe, expect, it } from 'vitest';

import {
  distancia,
  longitudRelativa,
  medirCromosoma,
  morfologiaPorIndice,
  resumenMedida,
} from '../../src/clinic/lib/medicion';

describe('distancia', () => {
  it('mide la hipotenusa entre dos puntos', () => {
    expect(distancia({ x: 0, y: 0 }, { x: 3, y: 4 })).toBe(5);
  });

  it('es cero entre un punto y sí mismo', () => {
    expect(distancia({ x: 7, y: 7 }, { x: 7, y: 7 })).toBe(0);
  });
});

describe('medirCromosoma — morfologías reales', () => {
  it('brazos iguales dan metacéntrico (como el cromosoma 1)', () => {
    // p = q = 50 px: el centrómero justo en el medio.
    const m = medirCromosoma({ x: 0, y: 0 }, { x: 0, y: 50 }, { x: 0, y: 100 });

    expect(m.brazoP).toBe(50);
    expect(m.brazoQ).toBe(50);
    expect(m.indiceCentromerico).toBe(50);
    expect(m.razonBrazos).toBe(1);
    expect(m.morfologia).toBe('metacéntrico');
  });

  it('centrómero desplazado da submetacéntrico (como el 4 o el 5)', () => {
    // p = 30, q = 70 → IC = 30%
    const m = medirCromosoma({ x: 0, y: 0 }, { x: 0, y: 30 }, { x: 0, y: 100 });

    expect(m.indiceCentromerico).toBe(30);
    expect(m.morfologia).toBe('submetacéntrico');
  });

  it('centrómero muy cerca del extremo da acrocéntrico (como el 13, 14, 15, 21, 22)', () => {
    // p = 15, q = 85 → IC = 15%
    const m = medirCromosoma({ x: 0, y: 0 }, { x: 0, y: 15 }, { x: 0, y: 100 });

    expect(m.indiceCentromerico).toBe(15);
    expect(m.morfologia).toBe('acrocéntrico');
  });

  it('sin brazo corto apreciable da telocéntrico', () => {
    const m = medirCromosoma({ x: 0, y: 0 }, { x: 0, y: 5 }, { x: 0, y: 100 });

    expect(m.morfologia).toBe('telocéntrico');
  });
});

describe('medirCromosoma — invariantes', () => {
  it('p es el brazo corto aunque el analista marque los extremos al revés', () => {
    // Marcando primero el brazo LARGO: 80 arriba, 20 abajo.
    const alReves = medirCromosoma({ x: 0, y: 0 }, { x: 0, y: 80 }, { x: 0, y: 100 });

    expect(alReves.brazoP).toBe(20);
    expect(alReves.brazoQ).toBe(80);
    expect(alReves.indiceCentromerico).toBe(20);
  });

  it('el índice centromérico nunca supera 50', () => {
    // Cualquier reparto: p es el corto por definición, así que p/(p+q) <= 0.5
    for (const corte of [1, 10, 25, 49, 50, 75, 99]) {
      const m = medirCromosoma({ x: 0, y: 0 }, { x: 0, y: corte }, { x: 0, y: 100 });
      expect(m.indiceCentromerico).toBeLessThanOrEqual(50);
    }
  });

  it('mide en diagonal igual que en vertical', () => {
    // Un cromosoma inclinado no cambia de morfología por estar inclinado.
    const vertical = medirCromosoma({ x: 0, y: 0 }, { x: 0, y: 30 }, { x: 0, y: 100 });
    const diagonal = medirCromosoma(
      { x: 0, y: 0 },
      { x: 18, y: 24 }, // 30 px en diagonal 3-4-5
      { x: 60, y: 80 }, // 100 px total en la misma recta
    );

    expect(diagonal.indiceCentromerico).toBeCloseTo(vertical.indiceCentromerico, 1);
    expect(diagonal.morfologia).toBe(vertical.morfologia);
  });

  it('un cromosoma sin longitud no revienta ni inventa morfología', () => {
    const m = medirCromosoma({ x: 5, y: 5 }, { x: 5, y: 5 }, { x: 5, y: 5 });

    expect(m.longitudTotal).toBe(0);
    expect(m.indiceCentromerico).toBe(0);
    expect(m.razonBrazos).toBe(Infinity);
  });
});

describe('morfologiaPorIndice — los cortes de Levan', () => {
  it.each([
    [50, 'metacéntrico'],
    [37.5, 'metacéntrico'],
    [37.4, 'submetacéntrico'],
    [25, 'submetacéntrico'],
    [24.9, 'acrocéntrico'],
    [12.5, 'acrocéntrico'],
    [12.4, 'telocéntrico'],
    [0, 'telocéntrico'],
  ])('IC %s%% → %s', (indice, esperada) => {
    expect(morfologiaPorIndice(indice as number)).toBe(esperada);
  });
});

describe('longitudRelativa', () => {
  it('expresa el tamaño como porcentaje del total medido', () => {
    expect(longitudRelativa(150, 3000)).toBe(5);
  });

  it('sin total no divide por cero', () => {
    expect(longitudRelativa(150, 0)).toBe(0);
  });
});

describe('resumenMedida', () => {
  it('da las tres cifras en el orden en que se leen', () => {
    const m = medirCromosoma({ x: 0, y: 0 }, { x: 0, y: 30 }, { x: 0, y: 100 });

    const texto = resumenMedida(m);

    expect(texto).toContain('L 100');
    expect(texto).toContain('IC 30%');
    expect(texto).toContain('submetacéntrico');
  });

  it('muestra ∞ en vez de romperse cuando no hay brazo corto', () => {
    const m = medirCromosoma({ x: 0, y: 0 }, { x: 0, y: 0 }, { x: 0, y: 100 });

    expect(resumenMedida(m)).toContain('∞');
  });
});
