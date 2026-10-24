import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { LIENZO_MAX, MetafaseEditor } from '../../src/clinic/components/MetafaseEditor';
import type { Chromosome, UltimaEdicion } from '../../src/clinic/types/karyotype';

/**
 * Separar trazando una línea y deshacer, en el editor (DD-KARYO-007 T6).
 *
 * Se comprueba lo que decide el cliente: que la línea se ENVÍA en píxeles de
 * la metafase, que solo se envía si atraviesa el objeto (si no, se avisa), y
 * que «Deshacer» enseña qué desharía y solo deja deshacer lo propio.
 */
const METAFASE = { width: 1520, height: 1140, naturalWidth: 1520, naturalHeight: 1140 } as HTMLImageElement;
const AJUSTE = Math.min(LIENZO_MAX.w / 1520, LIENZO_MAX.h / 1140);

const A: Chromosome = {
  id: 'a', predicted_class: '1', position_index: 0, confidence_score: '0.950', semaphore: 'green',
  resolution_status: 'AUTO', xai_viewed: false, is_anomaly: false, is_active: true, measures: {},
  bbox: { x: 100, y: 100, w: 40, h: 90 },
  contour: [[100, 100], [140, 100], [140, 190], [100, 190]],
  order: 0,
};
const PROPIA: UltimaEdicion = { evento: 'e1', tipo: 'SPLIT', propia: true, actor_name: 'dra_garcia', created_at: '' };

const puntero = (x: number, y: number) => {
  (globalThis as unknown as { __konvaPointer?: { x: number; y: number } }).__konvaPointer = { x, y };
};
const stage = () => screen.getByTestId('metafase-editor-stage');
/** De píxeles de la metafase a píxeles del Stage (sin zoom). */
const enPantalla = (x: number, y: number): [number, number] => [x * AJUSTE, y * AJUSTE];

function pintar(extra: Partial<Parameters<typeof MetafaseEditor>[0]> = {}) {
  const onSeparar = vi.fn();
  const onDeshacer = vi.fn();
  const utils = render(
    <MetafaseEditor metafase={METAFASE} chromosomes={[A]} selectedId="a" onSelect={() => {}}
      onSeparar={onSeparar} onDeshacer={onDeshacer} ultima={null} {...extra} />,
  );
  return { onSeparar, onDeshacer, ...utils };
}

/** Traza una línea en píxeles de la metafase, pasando por `puntos`. */
function trazar(puntos: [number, number][], soltar: 'mouseUp' | 'mouseLeave' = 'mouseUp') {
  puntero(...enPantalla(...puntos[0]));
  fireEvent.mouseDown(stage());
  for (const p of puntos.slice(1)) {
    puntero(...enPantalla(...p));
    fireEvent.mouseMove(stage());
  }
  fireEvent[soltar](stage());
}

const cortar = () => fireEvent.click(screen.getByTestId('metafase-herramienta-cortar'));

describe('MetafaseEditor — separar (DD-KARYO-007 T6)', () => {
  it('una línea de borde a borde se envía en píxeles de la metafase', () => {
    const { onSeparar } = pintar();
    cortar();
    trazar([[90, 145], [120, 146], [150, 147]]);
    expect(onSeparar).toHaveBeenCalledTimes(1);
    const [c, linea] = onSeparar.mock.calls[0];
    expect(c).toBe(A);
    expect(linea[0]).toEqual([90, 145]);
    expect(linea[linea.length - 1]).toEqual([150, 147]);
    // Separar es un acto puntual: vuelve a seleccionar.
    expect(stage()).toHaveAttribute('data-herramienta', 'seleccionar');
  });

  it('una línea que no atraviesa el objeto no se envía y se dice por qué', () => {
    const { onSeparar } = pintar();
    cortar();
    trazar([[90, 145], [120, 145]]);          // entra pero no sale
    expect(onSeparar).not.toHaveBeenCalled();
    expect(screen.getByTestId('metafase-aviso-corte')).toHaveTextContent('de borde a borde');
    expect(stage()).toHaveAttribute('data-herramienta', 'cortar');   // puede volver a intentarlo
  });

  it('mientras se traza, la línea dice si ya corta', () => {
    pintar();
    cortar();
    puntero(...enPantalla(90, 145));
    fireEvent.mouseDown(stage());
    puntero(...enPantalla(120, 145));
    fireEvent.mouseMove(stage());
    expect(screen.getByTestId('metafase-trazo')).toHaveAttribute('data-corta', 'false');
    puntero(...enPantalla(150, 145));
    fireEvent.mouseMove(stage());
    expect(screen.getByTestId('metafase-trazo')).toHaveAttribute('data-corta', 'true');
    fireEvent.mouseLeave(stage());
    expect(screen.queryByTestId('metafase-trazo')).toBeNull();
  });

  it('sin objeto seleccionado pide seleccionarlo primero', () => {
    const { onSeparar } = pintar({ selectedId: null });
    cortar();
    trazar([[90, 145], [150, 145]]);
    expect(onSeparar).not.toHaveBeenCalled();
    expect(screen.getByTestId('metafase-aviso-corte')).toHaveTextContent('Seleccione primero');
  });

  it('Alt+S entra y sale de separar; Esc cancela y quita el aviso', () => {
    pintar();
    fireEvent.keyDown(window, { key: 's', altKey: true });
    expect(stage()).toHaveAttribute('data-herramienta', 'cortar');
    trazar([[90, 145], [120, 145]]);
    expect(screen.getByTestId('metafase-aviso-corte')).toBeInTheDocument();
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(stage()).toHaveAttribute('data-herramienta', 'seleccionar');
    expect(screen.queryByTestId('metafase-aviso-corte')).toBeNull();
    fireEvent.keyDown(window, { key: 'S', altKey: true });
    fireEvent.keyDown(window, { key: 's', altKey: true });
    expect(stage()).toHaveAttribute('data-herramienta', 'seleccionar');
  });

  it('cortando, la vista no se arrastra ni se selecciona al pulsar', () => {
    const onSelect = vi.fn();
    pintar({ onSelect });
    fireEvent.click(screen.getByTestId('metafase-acercar'));
    cortar();
    expect(stage()).toHaveAttribute('data-arrastrable', 'false');
    fireEvent.click(screen.getByTestId('metafase-objeto-a'));
    expect(onSelect).not.toHaveBeenCalled();
  });

  it('con una corrección en curso no se puede separar', () => {
    const { onSeparar } = pintar({ busy: true });
    expect(screen.getByTestId('metafase-herramienta-cortar')).toBeDisabled();
    fireEvent.keyDown(window, { key: 's', altKey: true });
    trazar([[90, 145], [150, 145]]);
    expect(onSeparar).not.toHaveBeenCalled();
  });

  it('sin onSeparar no hay herramienta ni atajo', () => {
    pintar({ onSeparar: undefined });
    expect(screen.queryByTestId('metafase-herramienta-cortar')).toBeNull();
    fireEvent.keyDown(window, { key: 's', altKey: true });
    expect(stage()).toHaveAttribute('data-herramienta', 'seleccionar');
  });
});

describe('MetafaseEditor — deshacer (DD-KARYO-007 T6)', () => {
  it('sin nada que deshacer, el botón lo dice y está desactivado', () => {
    pintar();
    expect(screen.getByTestId('metafase-deshacer')).toHaveTextContent('Nada que deshacer');
    expect(screen.getByTestId('metafase-deshacer')).toBeDisabled();
  });

  it('enseña la última edición y la deshace', () => {
    const { onDeshacer } = pintar({ ultima: PROPIA });
    expect(screen.getByTestId('metafase-deshacer')).toHaveTextContent('Deshacer: Separó');
    fireEvent.click(screen.getByTestId('metafase-deshacer'));
    expect(onDeshacer).toHaveBeenCalledTimes(1);
  });

  it('no deja deshacer lo de otro, y dice de quién es', () => {
    pintar({ ultima: { ...PROPIA, tipo: 'ADD_OBJECT', propia: false, actor_name: 'sup_lopez' } });
    const boton = screen.getByTestId('metafase-deshacer');
    expect(boton).toBeDisabled();
    expect(boton).toHaveAttribute('title', expect.stringContaining('sup_lopez'));
  });

  it('un tipo sin etiqueta se enseña tal cual', () => {
    pintar({ ultima: { ...PROPIA, tipo: 'NUEVO' as UltimaEdicion['tipo'] } });
    expect(screen.getByTestId('metafase-deshacer')).toHaveTextContent('Deshacer: NUEVO');
  });
});
