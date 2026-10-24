/**
 * Tests de la geometría del recorte manual.
 *
 * Lo que se fija aquí es lo que rompe en cuanto alguien arrastra «al revés»:
 * que el rectángulo salga normalizado sin importar la dirección del arrastre, y
 * que un clic suelto no se cuele como recorte. Ambas cosas terminan en un POST
 * al servidor —que reclasifica— así que un bbox degenerado no es un detalle
 * cosmético.
 */
import { describe, expect, it } from 'vitest';

import { RECORTE_MIN, esRecorteUtil, rectanguloDeRecorte } from '../../src/clinic/lib/recorte';

describe('rectanguloDeRecorte', () => {
  it('arrastrando hacia abajo y a la derecha', () => {
    expect(rectanguloDeRecorte({ x: 10, y: 20 }, { x: 50, y: 90 }))
      .toEqual({ x: 10, y: 20, w: 40, h: 70 });
  });

  it('arrastrando hacia arriba y a la izquierda da el MISMO rectángulo', () => {
    // El analista arrastra en cualquier dirección; el servidor exige ancho y
    // alto positivos. Sin normalizar, este caso mandaría w y h negativos.
    expect(rectanguloDeRecorte({ x: 50, y: 90 }, { x: 10, y: 20 }))
      .toEqual({ x: 10, y: 20, w: 40, h: 70 });
  });

  it('mezclando direcciones (arriba-derecha)', () => {
    expect(rectanguloDeRecorte({ x: 10, y: 90 }, { x: 50, y: 20 }))
      .toEqual({ x: 10, y: 20, w: 40, h: 70 });
  });

  it('redondea: el bbox se mide en píxeles enteros', () => {
    // Con zoom, deshacer la transformación da coordenadas fraccionarias.
    expect(rectanguloDeRecorte({ x: 10.4, y: 20.6 }, { x: 50.5, y: 90.2 }))
      .toEqual({ x: 10, y: 21, w: 40, h: 70 });
  });
});

describe('esRecorteUtil', () => {
  it('un clic sin arrastre no es un recorte', () => {
    const rect = rectanguloDeRecorte({ x: 30, y: 40 }, { x: 30, y: 40 });

    expect(esRecorteUtil(rect)).toBe(false);
  });

  it('una franja finísima tampoco: no cabe un cromosoma', () => {
    expect(esRecorteUtil({ x: 0, y: 0, w: 200, h: RECORTE_MIN - 1 })).toBe(false);
  });

  it('un rectángulo del tamaño mínimo sí vale', () => {
    expect(esRecorteUtil({ x: 0, y: 0, w: RECORTE_MIN, h: RECORTE_MIN })).toBe(true);
  });
});
