import { describe, expect, it } from 'vitest';
import {
  MIN_LADO_OBJETO,
  ZOOM_MAX,
  ZOOM_MIN,
  aImagen,
  cajaEntre,
  centrarEn,
  centroDe,
  escalaAjuste,
  faltanContornos,
  limitarDesplazamiento,
  limitarZoom,
  poligonoDe,
  puntosPlanos,
  zoomEnPunto,
} from '../../src/clinic/lib/contornoMetafase';

/** Geometría del editor de metafase (DD-KARYO-007 T2). */
const IMAGEN = { w: 1024, h: 768 };
const LIENZO = { w: 760, h: 570 };
const CAJA = { x: 448, y: 35, w: 175, h: 73 };
const SILUETA = [[450, 40], [600, 50], [610, 100], [460, 90]];

describe('escalaAjuste', () => {
  it('reduce la metafase para que quepa, por el lado que más sobra', () => {
    expect(escalaAjuste(IMAGEN, { w: 512, h: 768 })).toBe(0.5);
    expect(escalaAjuste(IMAGEN, { w: 1024, h: 384 })).toBe(0.5);
  });
  it('no amplía una metafase pequeña', () => {
    expect(escalaAjuste({ w: 300, h: 200 }, { w: 760, h: 560 })).toBe(1);
  });
  it('una imagen sin tamaño no rompe la cuenta', () => {
    expect(escalaAjuste({ w: 0, h: 0 }, { w: 760, h: 560 })).toBe(1);
  });
});

describe('poligonoDe', () => {
  it('usa la silueta si la hay', () => {
    expect(poligonoDe({ contour: SILUETA, bbox: CAJA }, IMAGEN)).toBe(SILUETA);
  });
  it('sin silueta, las cuatro esquinas de la caja (RN-07)', () => {
    expect(poligonoDe({ contour: null, bbox: CAJA }, IMAGEN)).toEqual([
      [448, 35], [623, 35], [623, 108], [448, 108],
    ]);
  });
  it('una silueta de menos de 3 puntos no es un polígono: cae a la caja', () => {
    expect(poligonoDe({ contour: [[1, 1], [2, 2]], bbox: CAJA }, IMAGEN)).toHaveLength(4);
  });
  it('sin silueta y con la caja fuera de la imagen no hay nada que pintar', () => {
    expect(poligonoDe({ contour: undefined, bbox: { x: 1000, y: 0, w: 100, h: 10 } }, IMAGEN)).toBeNull();
    expect(poligonoDe({ contour: null, bbox: {} }, IMAGEN)).toBeNull();
  });
});

describe('puntosPlanos y centroDe', () => {
  it('aplana al formato de Konva', () => {
    expect(puntosPlanos([[1, 2], [3, 4], [5, 6]])).toEqual([1, 2, 3, 4, 5, 6]);
  });
  it('el centro es la media de los vértices', () => {
    expect(centroDe([[0, 0], [10, 0], [10, 20], [0, 20]])).toEqual({ x: 5, y: 10 });
  });
});

describe('faltanContornos', () => {
  const con = { contour: SILUETA, bbox: CAJA, is_active: true };
  const sin = { contour: null, bbox: CAJA, is_active: true };
  it('un caso antiguo (caja sin silueta) los necesita', () => {
    expect(faltanContornos([con, sin])).toBe(true);
  });
  it('si todos tienen silueta, no', () => {
    expect(faltanContornos([con, con])).toBe(false);
  });
  it('los inactivos (absorbidos por JOIN) no cuentan', () => {
    expect(faltanContornos([con, { ...sin, is_active: false }])).toBe(false);
  });
  it('sin caja no hay de dónde sacar la silueta', () => {
    expect(faltanContornos([{ contour: null, bbox: {}, is_active: true }])).toBe(false);
    expect(faltanContornos([{ contour: null, bbox: { x: 0, y: 0, w: 0, h: 5 }, is_active: true }])).toBe(false);
  });
});

describe('zoom y desplazamiento', () => {
  it('el zoom se queda entre el mínimo y el máximo', () => {
    expect(limitarZoom(0.2)).toBe(ZOOM_MIN);
    expect(limitarZoom(100)).toBe(ZOOM_MAX);
    expect(limitarZoom(2)).toBe(2);
  });

  it('sin zoom el único desplazamiento posible es 0', () => {
    expect(limitarDesplazamiento({ x: -50, y: 30 }, LIENZO, 1)).toEqual({ x: 0, y: 0 });
  });

  it('con zoom, no se puede ver fuera de la metafase', () => {
    // A 2× la imagen mide 1520 × 1140: el borde derecho llega a x = −760.
    expect(limitarDesplazamiento({ x: -2000, y: 100 }, LIENZO, 2)).toEqual({ x: -760, y: 0 });
    expect(limitarDesplazamiento({ x: -300, y: -200 }, LIENZO, 2)).toEqual({ x: -300, y: -200 });
  });

  it('lo que está bajo el ancla se queda bajo el ancla', () => {
    const ancla = { x: 200, y: 150 };
    const pos = zoomEnPunto({ x: 0, y: 0 }, 1, 2, ancla, LIENZO);
    // El punto de la imagen bajo el ancla, antes y después.
    expect((ancla.x - 0) / 1).toBeCloseTo((ancla.x - pos.x) / 2);
    expect((ancla.y - 0) / 1).toBeCloseTo((ancla.y - pos.y) / 2);
  });

  it('volver al zoom mínimo devuelve la vista a su sitio', () => {
    expect(zoomEnPunto({ x: -300, y: -100 }, 2, 0.5, { x: 10, y: 10 }, LIENZO)).toEqual({ x: 0, y: 0 });
  });

  it('centrarEn pone el punto en el centro del lienzo', () => {
    const escala = 2;
    const pos = centrarEn({ x: 300, y: 200 }, escala, LIENZO, 2);
    expect(300 * escala + pos.x).toBe(LIENZO.w / 2);
    expect(200 * escala + pos.y).toBe(LIENZO.h / 2);
  });

  it('centrarEn no saca la vista de la imagen cerca del borde', () => {
    expect(centrarEn({ x: 0, y: 0 }, 2, LIENZO, 2)).toEqual({ x: 0, y: 0 });
  });
});

describe('aImagen y cajaEntre (T3, añadir objeto)', () => {
  it('aImagen deshace el desplazamiento y la escala del Stage', () => {
    expect(aImagen({ x: 150, y: 90 }, { x: -50, y: -10 }, 2)).toEqual({ x: 100, y: 50 });
  });
  it('la caja es la misma arrastrando en cualquier dirección', () => {
    const ida = cajaEntre({ x: 10.4, y: 20.6 }, { x: 40.2, y: 70.1 }, IMAGEN);
    expect(ida).toEqual({ x: 10, y: 20, w: 31, h: 51 });
    expect(cajaEntre({ x: 40.2, y: 70.1 }, { x: 10.4, y: 20.6 }, IMAGEN)).toEqual(ida);
  });
  it('se recorta a la imagen', () => {
    expect(cajaEntre({ x: -20, y: -5 }, { x: 30, y: 30 }, IMAGEN)).toEqual({ x: 0, y: 0, w: 30, h: 30 });
    expect(cajaEntre({ x: 1000, y: 700 }, { x: 1100, y: 900 }, IMAGEN)).toEqual({ x: 1000, y: 700, w: 24, h: 68 });
  });
  it('por debajo del lado mínimo no es un objeto', () => {
    expect(cajaEntre({ x: 0, y: 0 }, { x: MIN_LADO_OBJETO - 1, y: 50 }, IMAGEN)).toBeNull();
    expect(cajaEntre({ x: 0, y: 0 }, { x: 50, y: MIN_LADO_OBJETO - 1 }, IMAGEN)).toBeNull();
    expect(cajaEntre({ x: 0, y: 0 }, { x: MIN_LADO_OBJETO, y: MIN_LADO_OBJETO }, IMAGEN)).not.toBeNull();
  });
});
