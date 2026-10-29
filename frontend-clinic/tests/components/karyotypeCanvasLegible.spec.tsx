import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen } from '@testing-library/react';
import { KaryotypeCanvas } from '../../src/clinic/components/KaryotypeCanvas';
import { ChromosomePropertiesPanel } from '../../src/clinic/components/ChromosomePropertiesPanel';
import { STAGE_WIDTH } from '../../src/clinic/lib/karyoLayout';
import type { Chromosome } from '../../src/clinic/types/karyotype';

/**
 * Cariograma legible (DD-KARYO-007 T7): escala común, línea base, orientación
 * y ajuste al ancho. El mock de react-konva expone la caja de cada imagen
 * (`data-caja`) y la vista del Stage (`data-vista`).
 */
const METAFASE = { width: 1024, height: 768, naturalWidth: 1024, naturalHeight: 768 } as HTMLImageElement;
const LINEA_BASE = 10 + 100;   // CUERPO.y + CUERPO.h

function cromosoma(id: string, bbox: Chromosome['bbox'], extra: Partial<Chromosome> = {}): Chromosome {
  return {
    id, predicted_class: '1', position_index: 0, confidence_score: '0.950', semaphore: 'green',
    resolution_status: 'AUTO', xai_viewed: false, is_anomaly: false, is_active: true, measures: {},
    bbox, order: 0, ...extra,
  };
}

// Nueve cromosomas «normales» de 100 px de largo, un 1 de 160 y un 21 de 45.
const NORMALES = Array.from({ length: 9 }, (_, i) => cromosoma(`n${i}`, { x: 10 + i * 30, y: 10, w: 20, h: 100 }, { predicted_class: '7', position_index: i % 2 }));
const UNO = cromosoma('uno', { x: 400, y: 10, w: 25, h: 160 });
const VEINTIUNO = cromosoma('veintiuno', { x: 500, y: 10, w: 18, h: 45 }, { predicted_class: '21' });

const caja = (id: string) => JSON.parse(screen.getByTestId(`chromosome-img-${id}`).getAttribute('data-caja')!);
/** Alto visible y borde inferior de la imagen (de pie: sin girar 90°). */
const borde = (id: string) => { const c = caja(id); return { alto: c.h, abajo: c.y + c.h / 2 }; };

function pintar(chromosomes: Chromosome[]) {
  return render(
    <KaryotypeCanvas chromosomes={chromosomes} selectedId={null} onSelect={() => {}} metafase={METAFASE} />,
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('KaryotypeCanvas legible (DD-KARYO-007 T7)', () => {
  it('a escala común: el 21 se ve más corto que el 1, ya no llena el hueco', () => {
    pintar([...NORMALES, UNO, VEINTIUNO]);
    expect(borde('veintiuno').alto).toBeLessThan(borde('uno').alto);
    expect(borde('veintiuno').alto).toBeLessThan(60);   // antes de T7: 100, como todos
    expect(borde('n0').alto).toBeGreaterThan(90);
  });

  it('todos apoyados en la línea base', () => {
    pintar([...NORMALES, UNO, VEINTIUNO]);
    for (const id of ['n0', 'uno', 'veintiuno']) expect(borde(id).abajo).toBeCloseTo(LINEA_BASE);
  });

  it('girado y volteado según measures.orientacion', () => {
    pintar([...NORMALES, cromosoma('g', { x: 10, y: 10, w: 20, h: 90 }, { measures: { orientacion: { giro: 180, volteo: true } } })]);
    const img = screen.getByTestId('chromosome-img-g');
    expect(img).toHaveAttribute('data-orientacion', '180-v');
    expect(caja('g').rotacion).toBe(180);
    expect(screen.getByTestId('chromosome-img-n0')).toHaveAttribute('data-orientacion', '0');
  });

  it('un tumbado girado 180° suma los dos giros', () => {
    pintar([...NORMALES, cromosoma('t', { x: 10, y: 10, w: 90, h: 20 }, { measures: { orientacion: { giro: 180, volteo: false } } })]);
    expect(caja('t').rotacion).toBe(270);
  });

  it('el lienzo crece hasta el ancho del panel', () => {
    let avisar: (e: { contentRect: { width: number } }[]) => void = () => {};
    vi.stubGlobal('ResizeObserver', class {
      constructor(cb: typeof avisar) { avisar = cb; }
      observe() {}
      disconnect() {}
    });
    pintar(NORMALES);
    const escala = () => JSON.parse(screen.getByTestId('karyo-stage').getAttribute('data-vista')!).escala;
    expect(escala()).toBe(1);
    act(() => avisar([{ contentRect: { width: STAGE_WIDTH * 1.5 } }]));
    expect(escala()).toBeCloseTo(1.5);
  });
});

describe('ChromosomePropertiesPanel — girar y voltear (D7)', () => {
  it('cada botón alterna su parte de la orientación', () => {
    const onOrient = vi.fn();
    const c = cromosoma('x', { x: 1, y: 1, w: 10, h: 10 }, { measures: { orientacion: { giro: 180, volteo: false } } });
    render(<ChromosomePropertiesPanel chromosome={c} onOrient={onOrient} />);
    expect(screen.getByTestId('action-girar')).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByTestId('action-voltear')).toHaveAttribute('aria-pressed', 'false');
    fireEvent.click(screen.getByTestId('action-girar'));
    expect(onOrient).toHaveBeenLastCalledWith(c, { giro: 0, volteo: false, ajuste: 0 });
    fireEvent.click(screen.getByTestId('action-voltear'));
    expect(onOrient).toHaveBeenLastCalledWith(c, { giro: 180, volteo: true, ajuste: 0 });
  });

  it('sin onOrient no hay botones (caso validado o sin metafase)', () => {
    render(<ChromosomePropertiesPanel chromosome={cromosoma('x', {})} onViewXai={() => {}} />);
    expect(screen.queryByTestId('action-girar')).toBeNull();
  });
});

/** Silueta de un rectángulo w × h girado `grados`, centrado en (cx, cy), con su caja. */
function conSilueta(id: string, w: number, h: number, grados: number, cx = 600, cy = 400, extra: Partial<Chromosome> = {}) {
  const a = (grados * Math.PI) / 180;
  const contour = [[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2], [-w / 2, h / 2]].map(([x, y]) => [
    cx + x * Math.cos(a) - y * Math.sin(a),
    cy + x * Math.sin(a) + y * Math.cos(a),
  ]);
  const xs = contour.map(([x]) => x);
  const ys = contour.map(([, y]) => y);
  const bbox = {
    x: Math.floor(Math.min(...xs)), y: Math.floor(Math.min(...ys)),
    w: Math.ceil(Math.max(...xs)) - Math.floor(Math.min(...xs)),
    h: Math.ceil(Math.max(...ys)) - Math.floor(Math.min(...ys)),
  };
  return cromosoma(id, bbox, { contour, ...extra });
}
const transformacion = (id: string) =>
  JSON.parse(screen.getByTestId(`chromosome-silueta-${id}`).getAttribute('data-transformacion')!);

describe('KaryotypeCanvas — recortado por la silueta y enderezado (DD-KARYO-008 T2)', () => {
  it('uno en diagonal se pinta dentro de un grupo que lo pone de pie', () => {
    pintar([...NORMALES, conSilueta('d', 10, 100, 30)]);
    const grupo = screen.getByTestId('chromosome-silueta-d');
    expect(grupo).toHaveAttribute('data-enderezado', 'true');
    // Su eje está a 120°: girarlo −30° lo deja vertical (330 en [0, 360)).
    expect(grupo).toHaveAttribute('data-giro-final', '330');
    expect(transformacion('d').rotation).toBeCloseTo(-30, 6);
  });

  it('se recorta por la silueta, cerrada y relativa a su centro (D1)', () => {
    const d = conSilueta('d', 10, 100, 30);
    pintar([...NORMALES, d]);
    const { puntos, cerrado } = JSON.parse(screen.getByTestId('chromosome-silueta-d').getAttribute('data-silueta')!);
    expect(cerrado).toBe(true);
    expect(puntos).toHaveLength(4);
    (d.contour as number[][]).forEach(([x, y], i) => {
      expect(puntos[i][0]).toBeCloseTo(x - 600, 6);
      expect(puntos[i][1]).toBeCloseTo(y - 400, 6);
    });
  });

  it('la imagen sigue siendo el recorte de su caja, colocada respecto al centro', () => {
    const d = conSilueta('d', 10, 100, 30);
    pintar([...NORMALES, d]);
    const img = screen.getByTestId('chromosome-img-d');
    const b = d.bbox as { x: number; y: number; w: number; h: number };
    expect(JSON.parse(img.getAttribute('data-crop')!)).toEqual({ x: b.x, y: b.y, width: b.w, height: b.h });
    const c = JSON.parse(img.getAttribute('data-caja')!);
    expect(c.x).toBeCloseTo(b.x - 600, 6);
    expect(c.y).toBeCloseTo(b.y - 400, 6);
    expect(c.rotacion).toBe(0); // gira el grupo, no la imagen
  });

  it('de pie mide lo mismo que uno de su largo que ya estaba vertical', () => {
    // A 45° la caja de un 10 × 100 mide ~78 × 78; de pie mide 100, como los normales.
    pintar([...NORMALES, conSilueta('d', 10, 100, 45)]);
    expect(transformacion('d').scaleY * 100).toBeCloseTo(borde('n0').alto, 6);
  });

  it('la escala común sale de lo que miden de pie, no de sus cajas', () => {
    // Todos en diagonal, así que son ellos los que marcan el percentil 90. Con
    // sus cajas (~78 × 78, más anchas que el hueco de 22) la escala sería 0,28
    // y se verían diminutos; de pie (10 × 100) caben a escala 1.
    pintar(Array.from({ length: 10 }, (_, i) => conSilueta(`d${i}`, 10, 100, 45, 100 + i * 90, 400)));
    expect(transformacion('d0').scaleY).toBeCloseTo(1, 6);
  });

  it('la orientación de D7 se suma al enderezado', () => {
    pintar([...NORMALES, conSilueta('d', 10, 100, 30, 600, 400, { measures: { orientacion: { giro: 180, volteo: true } } })]);
    expect(screen.getByTestId('chromosome-silueta-d')).toHaveAttribute('data-giro-final', '150');
    expect(transformacion('d').scaleX).toBeLessThan(0);
    expect(screen.getByTestId('chromosome-img-d')).toHaveAttribute('data-orientacion', '180-v');
  });

  it('un casi redondo se recorta por su silueta pero no se endereza', () => {
    pintar([...NORMALES, conSilueta('r', 50, 55, 30)]);
    expect(screen.getByTestId('chromosome-silueta-r')).toHaveAttribute('data-enderezado', 'false');
  });

  it('sin silueta se pinta el recorte de su caja, como siempre (RN-07)', () => {
    pintar([...NORMALES, UNO]);
    expect(screen.queryByTestId('chromosome-silueta-uno')).toBeNull();
    expect(screen.getByTestId('chromosome-img-uno')).toBeInTheDocument();
  });

  it('se sigue seleccionando con un clic en su hueco', () => {
    const onSelect = vi.fn();
    const d = conSilueta('d', 10, 100, 30);
    render(<KaryotypeCanvas chromosomes={[...NORMALES, d]} selectedId={null} onSelect={onSelect} metafase={METAFASE} />);
    fireEvent.click(screen.getByTestId('chromosome-d'));
    expect(onSelect).toHaveBeenCalledWith(d);
  });

  it('el marco abraza al cromosoma de pie', () => {
    pintar([...NORMALES, conSilueta('d', 10, 100, 30)]);
    const marco = JSON.parse(screen.getByTestId('chromosome-frame-d').getAttribute('data-caja')!);
    expect(marco.y + marco.h).toBeCloseTo(LINEA_BASE + 2, 6);
    expect(marco.w).toBeLessThan(20); // de pie es estrecho; en diagonal su caja mediría ~60
  });
});

describe('ChromosomePropertiesPanel — ajuste fino del giro (DD-KARYO-008 T4)', () => {
  const conAjuste = (ajuste: number) =>
    conSilueta('a', 10, 100, 30, 600, 400, { measures: { orientacion: { giro: 180, volteo: true, ajuste } } });

  it('−5° y +5° envían el ajuste movido, sin tocar giro ni volteo', () => {
    const onOrient = vi.fn();
    const c = conAjuste(10);
    render(<ChromosomePropertiesPanel chromosome={c} onOrient={onOrient} />);
    expect(screen.getByTestId('ajuste-valor')).toHaveTextContent('Ajuste +10°');
    fireEvent.click(screen.getByTestId('action-ajuste-mas'));
    expect(onOrient).toHaveBeenLastCalledWith(c, { giro: 180, volteo: true, ajuste: 15 });
    fireEvent.click(screen.getByTestId('action-ajuste-menos'));
    expect(onOrient).toHaveBeenLastCalledWith(c, { giro: 180, volteo: true, ajuste: 5 });
  });

  it('Restablecer envía 0 y está apagado si ya es 0', () => {
    const onOrient = vi.fn();
    const { unmount } = render(<ChromosomePropertiesPanel chromosome={conAjuste(-15)} onOrient={onOrient} />);
    expect(screen.getByTestId('ajuste-valor')).toHaveTextContent('Ajuste −15°');
    fireEvent.click(screen.getByTestId('action-ajuste-restablecer'));
    expect(onOrient).toHaveBeenLastCalledWith(expect.anything(), { giro: 180, volteo: true, ajuste: 0 });
    unmount();
    render(<ChromosomePropertiesPanel chromosome={conAjuste(0)} onOrient={onOrient} />);
    expect(screen.getByTestId('ajuste-valor')).toHaveTextContent('Ajuste 0°');
    expect(screen.getByTestId('action-ajuste-restablecer')).toBeDisabled();
  });

  it('en los topes, el botón que lo pasaría se apaga', () => {
    const { unmount } = render(<ChromosomePropertiesPanel chromosome={conAjuste(90)} onOrient={() => {}} />);
    expect(screen.getByTestId('action-ajuste-mas')).toBeDisabled();
    expect(screen.getByTestId('action-ajuste-menos')).toBeEnabled();
    unmount();
    render(<ChromosomePropertiesPanel chromosome={conAjuste(-90)} onOrient={() => {}} />);
    expect(screen.getByTestId('action-ajuste-menos')).toBeDisabled();
    expect(screen.getByTestId('action-ajuste-mas')).toBeEnabled();
  });

  it('sin silueta no hay ajuste fino; girar y voltear siguen', () => {
    render(<ChromosomePropertiesPanel chromosome={cromosoma('x', { x: 1, y: 1, w: 10, h: 10 })} onOrient={() => {}} />);
    expect(screen.queryByTestId('ajuste-giro')).toBeNull();
    expect(screen.getByTestId('action-girar')).toBeInTheDocument();
  });

  it('sin onOrient (caso validado o sin metafase) tampoco', () => {
    render(<ChromosomePropertiesPanel chromosome={conAjuste(5)} onViewXai={() => {}} />);
    expect(screen.queryByTestId('ajuste-giro')).toBeNull();
  });

  it('en el cariograma, el ajuste guardado se suma al enderezado', () => {
    pintar([...NORMALES, conAjuste(20)]);
    // −30 del enderezado + 20 del ajuste + 180 del giro = 170.
    expect(screen.getByTestId('chromosome-silueta-a')).toHaveAttribute('data-giro-final', '170');
  });
});

describe('KaryotypeCanvas — marco ajustado (T7)', () => {
  it('el marco del semáforo abraza al cromosoma, no al hueco entero', () => {
    pintar([...NORMALES, UNO, VEINTIUNO]);
    const marco = JSON.parse(screen.getByTestId('chromosome-frame-veintiuno').getAttribute('data-caja')!);
    expect(marco.h).toBeLessThan(65);
    expect(marco.y + marco.h).toBeCloseTo(LINEA_BASE + 2);
  });
});
