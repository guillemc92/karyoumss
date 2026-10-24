import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { LIENZO_MAX, MetafaseEditor } from '../../src/clinic/components/MetafaseEditor';
import type { Chromosome } from '../../src/clinic/types/karyotype';

/**
 * Añadir y descartar objetos en el editor de metafase (DD-KARYO-007 T3).
 *
 * El mock de react-konva devuelve el puntero que fije el test, en píxeles del
 * Stage. Lo que se comprueba es lo que se ENVÍA: la caja en píxeles de la
 * metafase (lo que el servidor guarda en `bbox`), y que descartar pide motivo.
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
const A = cromosoma('a');
const B = cromosoma('b', { predicted_class: '18', bbox: { x: 400, y: 300, w: 30, h: 60 }, contour: null });

const puntero = (x: number, y: number) => {
  (globalThis as unknown as { __konvaPointer?: { x: number; y: number } }).__konvaPointer = { x, y };
};
const vista = () => JSON.parse(screen.getByTestId('metafase-editor-stage').getAttribute('data-vista')!);
const stage = () => screen.getByTestId('metafase-editor-stage');

function editable(selectedId: string | null = null, busy = false) {
  const onAnadir = vi.fn();
  const onDescartar = vi.fn();
  const onSelect = vi.fn();
  const utils = render(
    <MetafaseEditor metafase={METAFASE} chromosomes={[A, B]} selectedId={selectedId} busy={busy}
      onSelect={onSelect} onAnadir={onAnadir} onDescartar={onDescartar} />,
  );
  return { onAnadir, onDescartar, onSelect, ...utils };
}

/** Arrastra en píxeles del Stage (pantalla). */
function dibujar(desde: [number, number], hasta: [number, number]) {
  puntero(...desde);
  fireEvent.mouseDown(stage());
  puntero(...hasta);
  fireEvent.mouseMove(stage());
  fireEvent.mouseUp(stage());
}

const anadir = () => fireEvent.click(screen.getByTestId('metafase-herramienta-anadir'));

describe('MetafaseEditor — añadir (DD-KARYO-007 T3)', () => {
  it('sin onAnadir ni onDescartar no hay herramientas (caso validado)', () => {
    render(<MetafaseEditor metafase={METAFASE} chromosomes={[A]} selectedId="a" onSelect={() => {}} />);
    expect(screen.queryByTestId('metafase-herramientas')).toBeNull();
    fireEvent.keyDown(window, { key: 'Delete' });
    expect(screen.queryByTestId('metafase-confirmar-descarte')).toBeNull();
  });

  it('la caja se envía en píxeles de la metafase, no de la pantalla', () => {
    const { onAnadir } = editable();
    anadir();
    expect(screen.getByTestId('metafase-herramienta-anadir')).toHaveAttribute('aria-pressed', 'true');
    dibujar([100, 50], [150, 100]);
    expect(onAnadir).toHaveBeenCalledTimes(1);
    const [caja, clase] = onAnadir.mock.calls[0];
    expect(caja.x).toBe(Math.floor(100 / AJUSTE));
    expect(caja.y).toBe(Math.floor(50 / AJUSTE));
    expect(Math.abs(caja.w - 50 / AJUSTE)).toBeLessThanOrEqual(2);
    expect(Math.abs(caja.h - 50 / AJUSTE)).toBeLessThanOrEqual(2);
    expect(clase).toBe('');   // la decide el modelo
  });

  it('con zoom y desplazamiento la caja sigue cayendo donde se dibujó', () => {
    const { onAnadir } = editable();
    fireEvent.click(screen.getByTestId('metafase-acercar'));
    anadir();
    const { escala, x, y } = vista();
    expect(x).toBeLessThan(0);   // hay desplazamiento de verdad
    dibujar([200, 200], [260, 280]);
    const [caja] = onAnadir.mock.calls[0];
    expect(caja.x).toBe(Math.floor((200 - x) / escala));
    expect(caja.y).toBe(Math.floor((200 - y) / escala));
  });

  it('envía la clase elegida y la herramienta sigue activa para el siguiente', () => {
    const { onAnadir } = editable();
    anadir();
    fireEvent.change(screen.getByTestId('metafase-anadir-clase'), { target: { value: '21' } });
    dibujar([10, 10], [40, 60]);
    dibujar([300, 300], [330, 350]);
    expect(onAnadir).toHaveBeenCalledTimes(2);
    expect(onAnadir.mock.calls[1][1]).toBe('21');
    expect(stage()).toHaveAttribute('data-herramienta', 'anadir');
  });

  it('un clic suelto no añade nada', () => {
    const { onAnadir } = editable();
    anadir();
    dibujar([100, 100], [101, 102]);
    expect(onAnadir).not.toHaveBeenCalled();
  });

  it('la caja en curso se ve mientras se arrastra y soltar fuera la cierra', () => {
    const { onAnadir } = editable();
    anadir();
    puntero(100, 100);
    fireEvent.mouseDown(stage());
    puntero(160, 180);
    fireEvent.mouseMove(stage());
    expect(screen.getByTestId('metafase-caja-nueva')).toBeInTheDocument();
    fireEvent.mouseLeave(stage());
    expect(screen.queryByTestId('metafase-caja-nueva')).toBeNull();
    expect(onAnadir).toHaveBeenCalledTimes(1);
  });

  it('añadiendo, pulsar un objeto no lo selecciona y la vista no se arrastra', () => {
    const { onSelect } = editable();
    fireEvent.click(screen.getByTestId('metafase-acercar'));
    anadir();
    fireEvent.click(screen.getByTestId('metafase-objeto-a'));
    expect(onSelect).not.toHaveBeenCalled();
    expect(stage()).toHaveAttribute('data-arrastrable', 'false');
  });

  it('en modo seleccionar, arrastrar no dibuja cajas', () => {
    const { onAnadir } = editable();
    dibujar([10, 10], [80, 90]);
    expect(onAnadir).not.toHaveBeenCalled();
  });

  it('Esc vuelve a seleccionar', () => {
    editable();
    anadir();
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(stage()).toHaveAttribute('data-herramienta', 'seleccionar');
    expect(screen.getByTestId('metafase-anadir-clase')).not.toBeVisible();
    expect(screen.getByTestId('metafase-anadir-clase')).toBeDisabled();
  });

  it('el selector de clase solo se ve (y se usa) añadiendo', () => {
    editable();
    expect(screen.getByTestId('metafase-anadir-clase')).not.toBeVisible();
    anadir();
    expect(screen.getByTestId('metafase-anadir-clase')).toBeVisible();
    expect(screen.getByTestId('metafase-anadir-clase')).toBeEnabled();
  });

  it('el botón Seleccionar también sale de añadir', () => {
    editable();
    anadir();
    fireEvent.click(screen.getByTestId('metafase-herramienta-seleccionar'));
    expect(stage()).toHaveAttribute('data-herramienta', 'seleccionar');
  });

  it('con una corrección en curso no se dibuja', () => {
    const { onAnadir } = editable(null, true);
    anadir();
    dibujar([10, 10], [80, 90]);
    expect(onAnadir).not.toHaveBeenCalled();
  });
});

describe('MetafaseEditor — descartar (DD-KARYO-007 T3)', () => {
  it('pide motivo antes de enviar', () => {
    const { onDescartar } = editable('b');
    fireEvent.click(screen.getByTestId('metafase-descartar'));
    expect(screen.getByTestId('metafase-confirmar-descarte')).toHaveTextContent('marcado como 18');
    expect(screen.getByTestId('metafase-confirmar')).toBeDisabled();
    fireEvent.change(screen.getByTestId('metafase-motivo'), { target: { value: 'nucleo' } });
    fireEvent.click(screen.getByTestId('metafase-confirmar'));
    expect(onDescartar).toHaveBeenCalledWith(B, 'nucleo');
    expect(screen.queryByTestId('metafase-confirmar-descarte')).toBeNull();
  });

  it('sin selección no se puede descartar', () => {
    editable(null);
    expect(screen.getByTestId('metafase-descartar')).toBeDisabled();
    fireEvent.keyDown(window, { key: 'Delete' });
    expect(screen.queryByTestId('metafase-confirmar-descarte')).toBeNull();
  });

  it('Supr abre el descarte del seleccionado y Cancelar lo cierra sin enviar', () => {
    const { onDescartar } = editable('a');
    fireEvent.keyDown(window, { key: 'Delete' });
    expect(screen.getByTestId('metafase-confirmar-descarte')).toHaveTextContent('marcado como 7');
    fireEvent.click(screen.getByTestId('metafase-cancelar-descarte'));
    expect(screen.queryByTestId('metafase-confirmar-descarte')).toBeNull();
    expect(onDescartar).not.toHaveBeenCalled();
  });

  it('Esc también cierra el descarte', () => {
    editable('a');
    fireEvent.keyDown(window, { key: 'Delete' });
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(screen.queryByTestId('metafase-confirmar-descarte')).toBeNull();
  });

  it('Supr mientras se escribe en un campo no abre el descarte', () => {
    editable('a');
    anadir();
    fireEvent.keyDown(screen.getByTestId('metafase-anadir-clase'), { key: 'Delete' });
    expect(screen.queryByTestId('metafase-confirmar-descarte')).toBeNull();
  });

  it('cambiar de cromosoma cierra el descarte a medias', () => {
    const { rerender } = editable('a');
    fireEvent.click(screen.getByTestId('metafase-descartar'));
    rerender(
      <MetafaseEditor metafase={METAFASE} chromosomes={[A, B]} selectedId="b"
        onSelect={() => {}} onAnadir={() => {}} onDescartar={() => {}} />,
    );
    expect(screen.queryByTestId('metafase-confirmar-descarte')).toBeNull();
  });

  it('con una corrección en curso no se puede descartar', () => {
    editable('a', true);
    expect(screen.getByTestId('metafase-descartar')).toBeDisabled();
    fireEvent.keyDown(window, { key: 'Delete' });
    expect(screen.queryByTestId('metafase-confirmar-descarte')).toBeNull();
  });
});
