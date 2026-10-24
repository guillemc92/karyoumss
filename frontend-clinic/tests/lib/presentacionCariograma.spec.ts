import { describe, expect, it } from 'vitest';
import {
  SIN_ORIENTAR,
  colocarEnLineaBase,
  escalaComun,
  factorAjuste,
  girar,
  marcoVisible,
  orientacionDe,
  percentil,
  transformacionImagen,
  visibleDe,
  voltear,
} from '../../src/clinic/lib/presentacionCariograma';

/** Presentación legible del cariograma (DD-KARYO-007 T7). */
const CUERPO = { x: 2, y: 10, w: 22, h: 100 };

describe('escala común', () => {
  it('conserva el tamaño relativo: el 1 sale más largo que el 21', () => {
    // Recortes de pie, en px de la metafase: un «1» de 200 de largo y un «21» de 60.
    const recortes = [{ w: 30, h: 200 }, { w: 25, h: 60 }, ...Array(8).fill({ w: 20, h: 100 })];
    const s = escalaComun(recortes, CUERPO)!;
    const uno = colocarEnLineaBase({ w: 30, h: 200 }, CUERPO, s)!;
    const veintiuno = colocarEnLineaBase({ w: 25, h: 60 }, CUERPO, s)!;
    expect(uno.h).toBeGreaterThan(veintiuno.h);
    // Antes de T7 el 21 se ampliaba hasta llenar el hueco (100 px); ahora no.
    expect(veintiuno.h).toBeLessThan(0.6 * CUERPO.h);
  });

  it('un racimo sin separar no encoge a los demás', () => {
    // Nueve normales de 100 y un racimo de 400: la escala la marcan los normales.
    const recortes = [...Array(9).fill({ w: 20, h: 100 }), { w: 60, h: 400 }];
    const s = escalaComun(recortes, CUERPO)!;
    expect(colocarEnLineaBase({ w: 20, h: 100 }, CUERPO, s)!.h).toBeGreaterThan(80);
    // El racimo se reduce solo él, hasta caber.
    const racimo = colocarEnLineaBase({ w: 60, h: 400 }, CUERPO, s)!;
    expect(racimo.h).toBeLessThanOrEqual(CUERPO.h + 1e-9);
    expect(racimo.w).toBeLessThanOrEqual(CUERPO.w + 1e-9);
  });

  it('los tumbados cuentan por su lado largo', () => {
    expect(visibleDe({ w: 200, h: 30 })).toEqual({ w: 30, h: 200 });
    expect(escalaComun([{ w: 200, h: 30 }], CUERPO)).toBeCloseTo(escalaComun([{ w: 30, h: 200 }], CUERPO)!);
  });

  it('el ancho también limita la escala', () => {
    // Recortes muy anchos: el que manda es el ancho del hueco (22), no el alto.
    expect(escalaComun([{ w: 44, h: 50 }], CUERPO)).toBeCloseTo(0.5);
  });

  it('sin recortes no hay escala', () => {
    expect(escalaComun([], CUERPO)).toBeNull();
    expect(escalaComun([{ w: 0, h: 0 }], CUERPO)).toBeNull();
  });

  it('percentil', () => {
    const diez = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
    expect(percentil(diez, 0.9)).toBe(9);
    expect(percentil(diez, 1)).toBe(10);
    expect(percentil(diez, 0)).toBe(1);
    expect(percentil([5, NaN, -1], 0.9)).toBe(5);
  });
});

describe('línea base', () => {
  it('todos apoyados en el borde inferior del hueco, centrados a lo ancho', () => {
    for (const r of [{ w: 20, h: 50 }, { w: 10, h: 90 }, { w: 80, h: 15 }]) {
      const c = colocarEnLineaBase(r, CUERPO, 1)!;
      const alto = c.rotacion === 90 ? c.w : c.h;
      expect(c.cy + alto / 2).toBeCloseTo(CUERPO.y + CUERPO.h);
      expect(c.cx).toBe(CUERPO.x + CUERPO.w / 2);
    }
  });

  it('un tumbado se pone de pie (D8) y conserva su aspecto', () => {
    const c = colocarEnLineaBase({ w: 80, h: 15 }, CUERPO, 1)!;
    expect(c.rotacion).toBe(90);
    expect(c.w / c.h).toBeCloseTo(80 / 15);
  });

  it('un recorte o una escala degenerados no se colocan', () => {
    expect(colocarEnLineaBase({ w: 0, h: 10 }, CUERPO, 1)).toBeNull();
    expect(colocarEnLineaBase({ w: 10, h: 10 }, CUERPO, 0)).toBeNull();
  });
});

describe('orientación (D7)', () => {
  it('por defecto, sin girar ni voltear', () => {
    expect(orientacionDe({})).toEqual(SIN_ORIENTAR);
    expect(orientacionDe(null)).toEqual(SIN_ORIENTAR);
    expect(orientacionDe({ orientacion: { giro: 90, volteo: 'si' } })).toEqual(SIN_ORIENTAR);
    expect(orientacionDe({ orientacion: { giro: 180, volteo: true } })).toEqual({ giro: 180, volteo: true });
  });

  it('girar y voltear se alternan', () => {
    expect(girar(girar(SIN_ORIENTAR))).toEqual(SIN_ORIENTAR);
    expect(voltear(SIN_ORIENTAR)).toEqual({ giro: 0, volteo: true });
    expect(girar(voltear(SIN_ORIENTAR))).toEqual({ giro: 180, volteo: true });
  });

  it('de pie: el giro se suma y el volteo es scaleX', () => {
    const dePie = colocarEnLineaBase({ w: 20, h: 90 }, CUERPO, 1)!;
    expect(transformacionImagen(dePie, SIN_ORIENTAR)).toEqual({ rotation: 0, scaleX: 1, scaleY: 1 });
    expect(transformacionImagen(dePie, { giro: 180, volteo: true })).toEqual({ rotation: 180, scaleX: -1, scaleY: 1 });
  });

  it('tumbado: el volteo horizontal en pantalla es el scaleY de la imagen girada', () => {
    const tumbado = colocarEnLineaBase({ w: 90, h: 20 }, CUERPO, 1)!;
    expect(transformacionImagen(tumbado, { giro: 0, volteo: true })).toEqual({ rotation: 90, scaleX: 1, scaleY: -1 });
    expect(transformacionImagen(tumbado, { giro: 180, volteo: false })).toEqual({ rotation: 270, scaleX: 1, scaleY: 1 });
  });
});

describe('factorAjuste', () => {
  it('crece hasta el ancho disponible, sin encoger y con tope', () => {
    expect(factorAjuste(1320, 880)).toBe(1.5);
    expect(factorAjuste(400, 880)).toBe(1);
    expect(factorAjuste(5000, 880)).toBe(2);
    expect(factorAjuste(0, 880)).toBe(1);
  });
});

describe('marcoVisible', () => {
  it('abraza lo que se ve, con margen, apoyado en la línea base', () => {
    const c = colocarEnLineaBase({ w: 10, h: 40 }, CUERPO, 1)!;
    const m = marcoVisible(c, CUERPO);
    expect(m.h).toBeCloseTo(40 + 4);
    expect(m.y + m.h).toBeCloseTo(CUERPO.y + CUERPO.h + 2);
    expect(m.w).toBeCloseTo(10 + 4);
  });
  it('en un tumbado usa los lados girados', () => {
    const c = colocarEnLineaBase({ w: 40, h: 10 }, CUERPO, 1)!;
    const m = marcoVisible(c, CUERPO, 0);
    expect([m.w, m.h]).toEqual([10, 40]);
  });
  it('nunca se sale del hueco más el margen', () => {
    const c = colocarEnLineaBase({ w: 22, h: 100 }, CUERPO, 5)!;
    const m = marcoVisible(c, CUERPO);
    expect(m.x).toBe(CUERPO.x - 2);
    expect(m.y).toBe(CUERPO.y - 2);
    expect(m.w).toBe(CUERPO.w + 4);
  });
});
