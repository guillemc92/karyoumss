import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { MetafasePanel } from '../../src/clinic/components/MetafasePanel';
import { aPanel, escalaPanel, regionDeRecorte } from '../../src/clinic/lib/recorteMetafase';

/**
 * Panel donde se dibuja el recorte, sobre la metafase real (DD-KARYO-006 D7).
 *
 * El mock de react-konva (tests/setup.ts) devuelve el puntero que fije el test,
 * en píxeles del panel. Lo que se comprueba es lo que se ENVÍA: píxeles de la
 * metafase, que es lo que el servidor guarda en `Chromosome.bbox`.
 */
const METAFASE = { width: 1024, height: 768, naturalWidth: 1024, naturalHeight: 768 } as HTMLImageElement;
// El cromosoma con el que se reprodujo el defecto el 13/10.
const CUMULO = { x: 448, y: 35, w: 175, h: 73 };
const REGION = regionDeRecorte(CUMULO, { w: 1024, h: 768 });
const ESCALA = escalaPanel(REGION);
const EN_PANEL = aPanel(CUMULO, REGION, ESCALA);

function setPointer(x: number, y: number) {
  (globalThis as unknown as { __konvaPointer?: { x: number; y: number } }).__konvaPointer = { x, y };
}

function arrastrar(desde: [number, number], hasta: [number, number], soltar: 'mouseUp' | 'mouseLeave' = 'mouseUp') {
  const stage = screen.getByTestId('metafase-stage');
  setPointer(...desde);
  fireEvent.mouseDown(stage);
  setPointer(...hasta);
  fireEvent.mouseMove(stage);
  fireEvent[soltar](stage);
}

function pintar(bbox = CUMULO) {
  const onCropDone = vi.fn();
  const onCancelar = vi.fn();
  render(<MetafasePanel metafase={METAFASE} bbox={bbox} onCropDone={onCropDone} onCancelar={onCancelar} />);
  return { onCropDone, onCancelar };
}

describe('MetafasePanel (DD-KARYO-006 D7)', () => {
  it('muestra la región de la metafase alrededor del cromosoma, no la imagen entera', () => {
    pintar();
    const crop = JSON.parse(screen.getByTestId('metafase-imagen').getAttribute('data-crop')!);
    expect(crop).toEqual({ x: REGION.x, y: REGION.y, width: REGION.w, height: REGION.h });
    expect(REGION.w).toBeLessThan(1024);
  });

  it('el recuadro discontinuo cae donde está el cromosoma', () => {
    pintar();
    const caja = JSON.parse(screen.getByTestId('metafase-recorte-actual').getAttribute('data-caja')!);
    expect(caja).toEqual(EN_PANEL);
  });

  it('dibujar sobre el recuadro actual envía la caja del cromosoma en la metafase', () => {
    // El defecto del 13/10: se enviaba {x: 9, y: 18, w: 22, h: 100}.
    const { onCropDone } = pintar();
    arrastrar([EN_PANEL.x, EN_PANEL.y], [EN_PANEL.x + EN_PANEL.w, EN_PANEL.y + EN_PANEL.h]);
    expect(onCropDone).toHaveBeenCalledTimes(1);
    const enviado = onCropDone.mock.calls[0][0];
    for (const k of ['x', 'y', 'w', 'h'] as const) {
      expect(Math.abs(enviado[k] - CUMULO[k])).toBeLessThanOrEqual(1);
    }
  });

  it('arrastrar hacia atrás da el mismo recorte', () => {
    const { onCropDone } = pintar();
    arrastrar([EN_PANEL.x + EN_PANEL.w / 2, EN_PANEL.y + EN_PANEL.h], [EN_PANEL.x, EN_PANEL.y]);
    const enviado = onCropDone.mock.calls[0][0];
    expect(enviado.x).toBe(448);
    expect(Math.abs(enviado.w - 175 / 2)).toBeLessThanOrEqual(1);
  });

  it('un clic suelto no envía nada', () => {
    const { onCropDone } = pintar();
    arrastrar([100, 100], [102, 103]);
    expect(onCropDone).not.toHaveBeenCalled();
  });

  it('el rectángulo en curso se ve mientras se arrastra y desaparece al soltar', () => {
    pintar();
    const stage = screen.getByTestId('metafase-stage');
    const rects = () => stage.querySelectorAll('[data-konva="rect"]').length;
    expect(rects()).toBe(1);
    setPointer(10, 10);
    fireEvent.mouseDown(stage);
    setPointer(80, 90);
    fireEvent.mouseMove(stage);
    expect(rects()).toBe(2);
    fireEvent.mouseUp(stage);
    expect(rects()).toBe(1);
  });

  it('salir del panel suelta el arrastre', () => {
    const { onCropDone } = pintar();
    arrastrar([10, 10], [80, 90], 'mouseLeave');
    expect(onCropDone).toHaveBeenCalledTimes(1);
  });

  it('mover sin haber pulsado no hace nada', () => {
    const { onCropDone } = pintar();
    const stage = screen.getByTestId('metafase-stage');
    fireEvent.mouseMove(stage);
    fireEvent.mouseUp(stage);
    expect(onCropDone).not.toHaveBeenCalled();
  });

  it('un rectángulo que no toca la imagen no se envía', () => {
    // Cromosoma en la esquina inferior derecha: la región acaba en el borde de
    // la imagen y el panel no tiene píxeles más allá.
    const { onCropDone } = pintar({ x: 1000, y: 740, w: 24, h: 28 });
    arrastrar([5000, 5000], [5100, 5100]);
    expect(onCropDone).not.toHaveBeenCalled();
  });

  it('Cancelar cierra sin enviar', () => {
    const { onCropDone, onCancelar } = pintar();
    fireEvent.click(screen.getByTestId('metafase-cancelar'));
    expect(onCancelar).toHaveBeenCalledTimes(1);
    expect(onCropDone).not.toHaveBeenCalled();
  });
});
