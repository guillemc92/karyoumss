import { describe, expect, it } from 'vitest';
import {
  AJUSTE_MAX,
  PASO_AJUSTE,
  SIN_ORIENTAR,
  ajustar,
  restablecer,
  tieneSilueta,
  cajaGirada,
  colocarEnLineaBase,
  colocarSilueta,
  dimensionesDePie,
  siluetaDe,
  trazarSilueta,
  type ColocacionSilueta,
  type Silueta,
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
    expect(orientacionDe({ orientacion: { giro: 180, volteo: true } })).toEqual({ giro: 180, volteo: true, ajuste: 0 });
  });

  it('girar y voltear se alternan', () => {
    expect(girar(girar(SIN_ORIENTAR))).toEqual(SIN_ORIENTAR);
    expect(voltear(SIN_ORIENTAR)).toEqual({ giro: 0, volteo: true, ajuste: 0 });
    expect(girar(voltear(SIN_ORIENTAR))).toEqual({ giro: 180, volteo: true, ajuste: 0 });
  });

  it('de pie: el giro se suma y el volteo es scaleX', () => {
    const dePie = colocarEnLineaBase({ w: 20, h: 90 }, CUERPO, 1)!;
    expect(transformacionImagen(dePie, SIN_ORIENTAR)).toEqual({ rotation: 0, scaleX: 1, scaleY: 1 });
    expect(transformacionImagen(dePie, { giro: 180, volteo: true, ajuste: 0 })).toEqual({ rotation: 180, scaleX: -1, scaleY: 1 });
  });

  it('tumbado: el volteo horizontal en pantalla es el scaleY de la imagen girada', () => {
    const tumbado = colocarEnLineaBase({ w: 90, h: 20 }, CUERPO, 1)!;
    expect(transformacionImagen(tumbado, { giro: 0, volteo: true, ajuste: 0 })).toEqual({ rotation: 90, scaleX: 1, scaleY: -1 });
    expect(transformacionImagen(tumbado, { giro: 180, volteo: false, ajuste: 0 })).toEqual({ rotation: 270, scaleX: 1, scaleY: 1 });
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

// ============================================================================
// DD-KARYO-008 T2 — recortar por la silueta y enderezar
// ============================================================================

/** Rectángulo w × h centrado en (cx, cy) y girado `grados` (y hacia abajo). */
function rect(w: number, h: number, grados: number, cx = 300, cy = 200): number[][] {
  const a = (grados * Math.PI) / 180;
  return [[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2], [-w / 2, h / 2]].map(([x, y]) => [
    cx + x * Math.cos(a) - y * Math.sin(a),
    cy + x * Math.sin(a) + y * Math.cos(a),
  ]);
}
const cajaDe = (p: number[][]) => {
  const xs = p.map(([x]) => x);
  const ys = p.map(([, y]) => y);
  return { x: Math.min(...xs), y: Math.min(...ys), w: Math.max(...xs) - Math.min(...xs), h: Math.max(...ys) - Math.min(...ys) };
};

/**
 * Lo que Konva pinta: cada punto de la silueta, relativo a su centro, escalado,
 * girado y trasladado (T·R·S). Probar esto y no los números sueltos es lo que
 * caza un volteo con el signo del giro mal.
 */
function enPantalla(s: Silueta, c: ColocacionSilueta): number[][] {
  const a = (c.rotation * Math.PI) / 180;
  return s.poligono.map(([px, py]) => {
    const x = (px - s.eje.centro.x) * c.scaleX;
    const y = (py - s.eje.centro.y) * c.scaleY;
    return [c.x + x * Math.cos(a) - y * Math.sin(a), c.y + x * Math.sin(a) + y * Math.cos(a)];
  });
}

// Un triángulo inclinado: asimétrico, así que un giro o un volteo mal hechos se notan.
const TRIANGULO = [[300, 200], [330, 210], [310, 320]];

describe('siluetaDe', () => {
  it('uno en diagonal se endereza por su eje', () => {
    const s = siluetaDe(rect(10, 100, 30), { w: 60, h: 90 })!;
    expect(s.enderezado).toBe(true);
    expect(s.giroAuto).toBeCloseTo(-30, 6);
  });

  it('uno casi redondo no se endereza: manda la regla de la caja (D8)', () => {
    const redondo = rect(50, 55, 30);
    expect(siluetaDe(redondo, { w: 60, h: 40 })).toMatchObject({ enderezado: false, giroAuto: 90 });
    expect(siluetaDe(redondo, { w: 40, h: 60 })).toMatchObject({ enderezado: false, giroAuto: 0 });
  });

  it('sin silueta utilizable no hay silueta: se pinta la caja', () => {
    expect(siluetaDe(null, { w: 10, h: 10 })).toBeNull();
    expect(siluetaDe(undefined, { w: 10, h: 10 })).toBeNull();
    expect(siluetaDe([[0, 0], [1, 1]], { w: 10, h: 10 })).toBeNull();
  });
});

describe('cajaGirada y dimensionesDePie', () => {
  it('de pie mide su largo real, no el de la caja', () => {
    // A 45° la caja de un 10 × 100 mide ~78 × 78.
    const d = dimensionesDePie(siluetaDe(rect(10, 100, 45), { w: 78, h: 78 })!);
    expect(d.w).toBeCloseTo(10, 6);
    expect(d.h).toBeCloseTo(100, 6);
  });

  it('el espejo refleja la caja sobre el centro', () => {
    const s = siluetaDe(TRIANGULO, { w: 30, h: 120 })!;
    const sin = cajaGirada(s, 0, false);
    const con = cajaGirada(s, 0, true);
    expect(con.w).toBeCloseTo(sin.w, 6);
    expect(con.x).toBeCloseTo(-(sin.x + sin.w), 6);
  });
});

describe('colocarSilueta', () => {
  const s = siluetaDe(rect(10, 100, 30), { w: 60, h: 90 })!;

  it.each([
    ['sin orientar', SIN_ORIENTAR],
    ['girado 180°', { giro: 180, volteo: false, ajuste: 0 } as const],
    ['volteado', { giro: 0, volteo: true, ajuste: 0 } as const],
    ['girado y volteado', { giro: 180, volteo: true, ajuste: 0 } as const],
  ])('%s: de pie, centrado y apoyado en la línea base', (_, o) => {
    const vista = cajaDe(enPantalla(s, colocarSilueta(s, o, CUERPO, 0.9)!));
    // De pie: 10 de ancho y 100 de largo, a escala 0,9.
    expect(vista.w).toBeCloseTo(9, 6);
    expect(vista.h).toBeCloseTo(90, 6);
    expect(vista.y + vista.h).toBeCloseTo(CUERPO.y + CUERPO.h, 6);
    expect(vista.x + vista.w / 2).toBeCloseTo(CUERPO.x + CUERPO.w / 2, 6);
  });

  it('voltear es el espejo en pantalla de lo que se ve sin voltear', () => {
    const t = siluetaDe(TRIANGULO, { w: 30, h: 120 })!;
    const eje = CUERPO.x + CUERPO.w / 2;
    for (const giro of [0, 180] as const) {
      const sinV = enPantalla(t, colocarSilueta(t, { giro, volteo: false, ajuste: 0 }, CUERPO, 0.5)!);
      const conV = enPantalla(t, colocarSilueta(t, { giro, volteo: true, ajuste: 0 }, CUERPO, 0.5)!);
      sinV.forEach(([x, y], i) => {
        expect(conV[i][0]).toBeCloseTo(2 * eje - x, 6);
        expect(conV[i][1]).toBeCloseTo(y, 6);
      });
    }
  });

  it('girar 180° invierte arriba y abajo', () => {
    const t = siluetaDe(TRIANGULO, { w: 30, h: 120 })!;
    const sinG = enPantalla(t, colocarSilueta(t, SIN_ORIENTAR, CUERPO, 0.5)!);
    const conG = enPantalla(t, colocarSilueta(t, { giro: 180, volteo: false, ajuste: 0 }, CUERPO, 0.5)!);
    const { y: arriba, h } = cajaDe(sinG);
    sinG.forEach(([, y], i) => expect(conG[i][1] - arriba).toBeCloseTo(arriba + h - y, 6));
  });

  it('giroFinal suma lo automático y el de D7, en [0, 360)', () => {
    expect(colocarSilueta(s, SIN_ORIENTAR, CUERPO, 1)!.giroFinal).toBeCloseTo(330, 6);
    expect(colocarSilueta(s, { giro: 180, volteo: false, ajuste: 0 }, CUERPO, 1)!.giroFinal).toBeCloseTo(150, 6);
  });

  it('el que no cabe a la escala común se reduce solo él', () => {
    const vista = cajaDe(enPantalla(s, colocarSilueta(s, SIN_ORIENTAR, CUERPO, 5)!));
    expect(vista.h).toBeLessThanOrEqual(CUERPO.h + 1e-9);
    expect(vista.w).toBeLessThanOrEqual(CUERPO.w + 1e-9);
  });

  it('el marco abraza lo que se ve, con margen y dentro del hueco', () => {
    const c = colocarSilueta(s, SIN_ORIENTAR, CUERPO, 0.5)!;
    const vista = cajaDe(enPantalla(s, c));
    expect(c.marco.h).toBeCloseTo(vista.h + 4, 6);
    expect(c.marco.y + c.marco.h).toBeCloseTo(CUERPO.y + CUERPO.h + 2, 6);
    expect(c.marco.x).toBeCloseTo(vista.x - 2, 6);
  });

  it('con escala degenerada no se coloca', () => {
    expect(colocarSilueta(s, SIN_ORIENTAR, CUERPO, 0)).toBeNull();
    expect(colocarSilueta(s, SIN_ORIENTAR, CUERPO, Number.NaN)).toBeNull();
  });

  it('una silueta sin extensión no se coloca', () => {
    const plana: Silueta = {
      poligono: [[1, 1], [1, 1], [1, 1]], eje: { angulo: 0, largo: 0, ancho: 0, centro: { x: 1, y: 1 } },
      giroAuto: 0, enderezado: false,
    };
    expect(colocarSilueta(plana, SIN_ORIENTAR, CUERPO, 1)).toBeNull();
  });
});

describe('trazarSilueta', () => {
  it('traza el polígono relativo a su centro y lo cierra', () => {
    const s = siluetaDe(rect(10, 100, 0), { w: 10, h: 100 })!;
    const llamadas: string[] = [];
    trazarSilueta({
      beginPath: () => llamadas.push('begin'),
      moveTo: (x, y) => llamadas.push(`M${Math.round(x)},${Math.round(y)}`),
      lineTo: (x, y) => llamadas.push(`L${Math.round(x)},${Math.round(y)}`),
      closePath: () => llamadas.push('close'),
    }, s);
    expect(llamadas).toEqual(['begin', 'M-5,-50', 'L5,-50', 'L5,50', 'L-5,50', 'close']);
  });
});

// ============================================================================
// DD-KARYO-008 T4 — ajuste fino del giro (D3)
// ============================================================================

describe('ajuste fino (D3)', () => {
  it('se lee de lo guardado; lo antiguo o lo inválido es 0', () => {
    expect(orientacionDe({ orientacion: { giro: 0, volteo: false, ajuste: -15 } }).ajuste).toBe(-15);
    expect(orientacionDe({ orientacion: { giro: 0, volteo: false, ajuste: 90 } }).ajuste).toBe(90);
    for (const malo of [undefined, null, 2.5, 91, -91, '5', true, Number.NaN]) {
      expect(orientacionDe({ orientacion: { giro: 0, volteo: false, ajuste: malo } }).ajuste).toBe(0);
    }
  });

  it('ajustar suma y no pasa de ±90; restablecer lo deja en 0', () => {
    expect(ajustar(SIN_ORIENTAR, PASO_AJUSTE)).toEqual({ giro: 0, volteo: false, ajuste: 5 });
    expect(ajustar(ajustar(SIN_ORIENTAR, -PASO_AJUSTE), -PASO_AJUSTE).ajuste).toBe(-10);
    expect(ajustar({ ...SIN_ORIENTAR, ajuste: 88 }, PASO_AJUSTE).ajuste).toBe(AJUSTE_MAX);
    expect(ajustar({ ...SIN_ORIENTAR, ajuste: -88 }, -PASO_AJUSTE).ajuste).toBe(-AJUSTE_MAX);
    expect(restablecer({ giro: 180, volteo: true, ajuste: 25 })).toEqual({ giro: 180, volteo: true, ajuste: 0 });
  });

  it('girar y voltear conservan el ajuste', () => {
    const o = { giro: 0 as const, volteo: false, ajuste: 10 };
    expect(girar(o).ajuste).toBe(10);
    expect(voltear(o).ajuste).toBe(10);
  });

  it('el ajuste se suma al enderezado: lo que se ve gira exactamente esos grados', () => {
    // Un 10 × 100 en diagonal se endereza; con +20 queda inclinado 20° en pantalla.
    const s = siluetaDe(rect(10, 100, 30), { w: 60, h: 90 })!;
    const c = colocarSilueta(s, { ...SIN_ORIENTAR, ajuste: 20 }, CUERPO, 0.5)!;
    expect(c.giroFinal).toBeCloseTo(350, 6); // −30 del enderezado + 20
    // El eje de lo que se ve: 20° de la vertical, hacia la derecha arriba (y abajo es +).
    const p = enPantalla(s, c);
    const [a, b] = [p[0], p[3]]; // dos esquinas sobre el mismo lado largo
    const angulo = (Math.atan2(b[1] - a[1], b[0] - a[0]) * 180) / Math.PI;
    expect(Math.min(Math.abs(angulo - 110), Math.abs(angulo + 70))).toBeLessThan(1e-6);
    // Y sigue apoyado en la línea base y dentro del hueco.
    const vista = cajaDe(p);
    expect(vista.y + vista.h).toBeCloseTo(CUERPO.y + CUERPO.h, 6);
    expect(vista.h).toBeLessThanOrEqual(CUERPO.h + 1e-9);
  });

  it('tieneSilueta solo con un polígono con eje', () => {
    expect(tieneSilueta(rect(10, 100, 30))).toBe(true);
    expect(tieneSilueta(null)).toBe(false);
    expect(tieneSilueta([[0, 0], [1, 1]])).toBe(false);
  });
});
