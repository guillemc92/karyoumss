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
    expect(onOrient).toHaveBeenLastCalledWith(c, { giro: 0, volteo: false });
    fireEvent.click(screen.getByTestId('action-voltear'));
    expect(onOrient).toHaveBeenLastCalledWith(c, { giro: 180, volteo: true });
  });

  it('sin onOrient no hay botones (caso validado o sin metafase)', () => {
    render(<ChromosomePropertiesPanel chromosome={cromosoma('x', {})} onViewXai={() => {}} />);
    expect(screen.queryByTestId('action-girar')).toBeNull();
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
