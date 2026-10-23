import { describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen } from '@testing-library/react';
import { LIENZO_MAX, MetafaseEditor } from '../../src/clinic/components/MetafaseEditor';
import type { Chromosome } from '../../src/clinic/types/karyotype';

/**
 * Editor de metafase (DD-KARYO-007 T2).
 *
 * El mock de react-konva (tests/setup.ts) expone los puntos de cada Line y la
 * vista del Stage. Lo que se comprueba es lo que decide el componente: qué
 * objetos pinta, con qué color, cuál está seleccionado y a qué escala. La
 * geometría real de Konva sobre una metafase se ve en el E2E.
 */
const METAFASE = { width: 1520, height: 1140, naturalWidth: 1520, naturalHeight: 1140 } as HTMLImageElement;
const AJUSTE = Math.min(LIENZO_MAX.w / 1520, LIENZO_MAX.h / 1140);

function cromosoma(id: string, extra: Partial<Chromosome> = {}): Chromosome {
  return {
    id,
    predicted_class: '7',
    position_index: 0,
    confidence_score: '0.950',
    semaphore: 'green',
    resolution_status: 'AUTO',
    xai_viewed: false,
    is_anomaly: false,
    is_active: true,
    measures: {},
    bbox: { x: 100, y: 100, w: 40, h: 90 },
    contour: [[105, 100], [140, 110], [135, 190], [100, 180]],
    order: 0,
    ...extra,
  };
}

const VERDE = cromosoma('a');
const NARANJA = cromosoma('b', { semaphore: 'orange', confidence_score: '0.610', contour: null, bbox: { x: 400, y: 300, w: 30, h: 60 } });
const ABSORBIDO = cromosoma('c', { is_active: false });
const SIN_NADA = cromosoma('d', { contour: null, bbox: {} });

function pintar(selectedId: string | null = null, chromosomes = [VERDE, NARANJA, ABSORBIDO, SIN_NADA]) {
  const onSelect = vi.fn();
  const utils = render(
    <MetafaseEditor metafase={METAFASE} chromosomes={chromosomes} selectedId={selectedId} onSelect={onSelect} />,
  );
  return { onSelect, ...utils };
}

const vista = () => JSON.parse(screen.getByTestId('metafase-editor-stage').getAttribute('data-vista')!);
const puntos = (id: string) => JSON.parse(screen.getByTestId(`metafase-objeto-${id}`).getAttribute('data-puntos')!);

describe('MetafaseEditor (DD-KARYO-007 T2)', () => {
  it('pinta la silueta real del cromosoma, en píxeles de la metafase', () => {
    pintar();
    expect(puntos('a')).toEqual([105, 100, 140, 110, 135, 190, 100, 180]);
    expect(screen.getByTestId('metafase-objeto-a')).toHaveAttribute('data-silueta', 'true');
  });

  it('sin silueta pinta la caja, para que el objeto se pueda tocar igual (RN-07)', () => {
    pintar();
    expect(puntos('b')).toEqual([400, 300, 430, 300, 430, 360, 400, 360]);
    expect(screen.getByTestId('metafase-objeto-b')).toHaveAttribute('data-silueta', 'false');
  });

  it('no pinta los absorbidos por un JOIN ni los que no tienen caja ni silueta', () => {
    pintar();
    expect(screen.queryByTestId('metafase-objeto-c')).toBeNull();
    expect(screen.queryByTestId('metafase-objeto-d')).toBeNull();
    expect(screen.getByTestId('metafase-cuenta')).toHaveTextContent('2 objeto(s)');
  });

  it('cada objeto lleva el semáforo de su cromosoma', () => {
    pintar();
    expect(screen.getByTestId('metafase-objeto-a')).toHaveAttribute('data-semaphore', 'green');
    expect(screen.getByTestId('metafase-objeto-b')).toHaveAttribute('data-semaphore', 'orange');
  });

  it('pulsar un objeto lo selecciona', () => {
    const { onSelect } = pintar();
    fireEvent.click(screen.getByTestId('metafase-objeto-b'));
    expect(onSelect).toHaveBeenCalledWith(NARANJA);
  });

  it('la selección que viene del cariograma se marca aquí', () => {
    pintar('b');
    expect(screen.getByTestId('metafase-objeto-b')).toHaveAttribute('data-seleccionado', 'true');
    expect(screen.getByTestId('metafase-objeto-a')).toHaveAttribute('data-seleccionado', 'false');
  });

  it('la metafase entera cabe en el lienzo y se pinta a su tamaño natural', () => {
    pintar();
    expect(vista()).toEqual({ escala: AJUSTE, x: 0, y: 0 });
    const imagen = JSON.parse(screen.getByTestId('metafase-editor-imagen').getAttribute('data-caja')!);
    expect([imagen.w, imagen.h]).toEqual([1520, 1140]);
    // Sin zoom no hay nada que arrastrar.
    expect(screen.getByTestId('metafase-editor-stage')).toHaveAttribute('data-arrastrable', 'false');
  });

  it('acercar, alejar y ajustar', () => {
    pintar();
    expect(screen.getByTestId('metafase-alejar')).toBeDisabled();
    fireEvent.click(screen.getByTestId('metafase-acercar'));
    expect(screen.getByTestId('metafase-zoom')).toHaveTextContent('150%');
    expect(vista().escala).toBeCloseTo(AJUSTE * 1.5);
    expect(screen.getByTestId('metafase-editor-stage')).toHaveAttribute('data-arrastrable', 'true');
    // Con los botones el ancla es el centro: la vista se desplaza hacia dentro.
    expect(vista().x).toBeLessThan(0);
    fireEvent.click(screen.getByTestId('metafase-alejar'));
    expect(screen.getByTestId('metafase-zoom')).toHaveTextContent('100%');
    fireEvent.click(screen.getByTestId('metafase-acercar'));
    fireEvent.click(screen.getByTestId('metafase-acercar'));
    fireEvent.click(screen.getByTestId('metafase-ajustar'));
    expect(vista()).toEqual({ escala: AJUSTE, x: 0, y: 0 });
  });

  it('el zoom no pasa del máximo', () => {
    pintar();
    for (let i = 0; i < 12; i += 1) fireEvent.click(screen.getByTestId('metafase-acercar'));
    expect(screen.getByTestId('metafase-zoom')).toHaveTextContent('800%');
    expect(screen.getByTestId('metafase-acercar')).toBeDisabled();
  });

  it('la rueda acerca hacia el cursor y aleja', () => {
    pintar();
    (globalThis as unknown as { __konvaPointer?: { x: number; y: number } }).__konvaPointer = { x: 0, y: 0 };
    fireEvent.wheel(screen.getByTestId('metafase-editor-stage'), { deltaY: -100 });
    // Ancla en la esquina: la esquina no se mueve.
    expect(vista()).toEqual({ escala: AJUSTE * 1.5, x: 0, y: 0 });
    fireEvent.wheel(screen.getByTestId('metafase-editor-stage'), { deltaY: 100 });
    expect(screen.getByTestId('metafase-zoom')).toHaveTextContent('100%');
  });

  it('arrastrar con zoom mueve la vista, sin salirse de la imagen', () => {
    pintar();
    fireEvent.click(screen.getByTestId('metafase-acercar'));
    const stage = screen.getByTestId('metafase-editor-stage');
    (globalThis as unknown as { __konvaDrop?: { x: number; y: number } }).__konvaDrop = { x: -5000, y: 50 };
    act(() => { stage.dispatchEvent(new CustomEvent('konvadragend')); });
    const lienzo = { w: Math.round(1520 * AJUSTE), h: Math.round(1140 * AJUSTE) };
    expect(vista().x).toBeCloseTo(lienzo.w * (1 - 1.5));
    expect(vista().y).toBe(0);
  });

  it('con zoom, seleccionar en el cariograma trae el cromosoma a la vista', () => {
    const { rerender } = pintar(null);
    fireEvent.click(screen.getByTestId('metafase-acercar'));
    fireEvent.click(screen.getByTestId('metafase-acercar'));
    rerender(
      <MetafaseEditor metafase={METAFASE} chromosomes={[VERDE, NARANJA]} selectedId="b" onSelect={() => {}} />,
    );
    const { escala, x, y } = vista();
    const lienzo = { w: Math.round(1520 * AJUSTE), h: Math.round(1140 * AJUSTE) };
    // El centro de la caja de NARANJA (415, 330) queda en el centro del lienzo.
    expect(415 * escala + x).toBeCloseTo(lienzo.w / 2);
    expect(330 * escala + y).toBeCloseTo(lienzo.h / 2);
  });

  it('sin zoom, seleccionar no mueve la vista', () => {
    const { rerender } = pintar(null);
    rerender(
      <MetafaseEditor metafase={METAFASE} chromosomes={[VERDE, NARANJA]} selectedId="b" onSelect={() => {}} />,
    );
    expect(vista()).toEqual({ escala: AJUSTE, x: 0, y: 0 });
  });
});
