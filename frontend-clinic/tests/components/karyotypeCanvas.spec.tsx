import { describe, expect, it, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { KaryotypeCanvas } from '../../src/clinic/components/KaryotypeCanvas';
import type { Chromosome } from '../../src/clinic/types/karyotype';
import { PAD, SLOT_W } from '../../src/clinic/lib/karyoLayout';
import { INITIAL_VIEWPORT } from '../../src/clinic/lib/viewport';

/** react-konva está mockeado globalmente en tests/setup.ts: los cromosomas se
 * renderizan como <button data-testid="chromosome-{id}"> y el drag se dispara
 * con el CustomEvent 'konvadragend' + globalThis.__konvaDrop. */

function chromo(overrides: Partial<Chromosome> = {}): Chromosome {
  return {
    id: 'c1', predicted_class: '1', position_index: 0, confidence_score: '0.960',
    semaphore: 'green', resolution_status: 'AUTO', xai_viewed: false,
    is_anomaly: false, is_active: true, measures: {}, bbox: {}, order: 0, ...overrides,
  };
}

function setDrop(x: number, y: number) {
  (globalThis as unknown as { __konvaDrop?: { x: number; y: number } }).__konvaDrop = { x, y };
}

describe('KaryotypeCanvas (Konva, P3)', () => {
  beforeEach(() => {
    delete (globalThis as unknown as { __konvaDrop?: unknown }).__konvaDrop;
  });

  it('renderiza el visor y un botón por cromosoma activo', () => {
    render(
      <KaryotypeCanvas
        chromosomes={[chromo({ id: 'a', predicted_class: '1' }), chromo({ id: 'b', predicted_class: '2' })]}
        selectedId={null}
        onSelect={() => {}}
      />,
    );
    const viewer = screen.getByTestId('karyotype-viewer');
    expect(viewer.querySelectorAll('button').length).toBe(2);
  });

  it('excluye los cromosomas inactivos (JOIN)', () => {
    render(
      <KaryotypeCanvas
        chromosomes={[chromo({ id: 'a' }), chromo({ id: 'b', predicted_class: '2', is_active: false })]}
        selectedId={null}
        onSelect={() => {}}
      />,
    );
    expect(screen.queryByTestId('chromosome-b')).not.toBeInTheDocument();
  });

  it('click en un cromosoma dispara onSelect', async () => {
    const onSelect = vi.fn();
    render(<KaryotypeCanvas chromosomes={[chromo({ id: 'a' })]} selectedId={null} onSelect={onSelect} />);
    await userEvent.click(screen.getByTestId('chromosome-a'));
    expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ id: 'a' }));
  });

  it('arrastrar a otro slot dispara onReclassify con la clase destino', () => {
    const onReclassify = vi.fn();
    render(
      <KaryotypeCanvas
        chromosomes={[chromo({ id: 'a', predicted_class: '1' })]}
        selectedId={null}
        onSelect={() => {}}
        onReclassify={onReclassify}
      />,
    );
    // Soltar sobre el slot 2 (columna siguiente) un cromosoma de clase 1.
    setDrop(PAD + SLOT_W + 10, PAD + 10);
    fireEvent(screen.getByTestId('chromosome-a'), new CustomEvent('konvadragend'));
    expect(onReclassify).toHaveBeenCalledWith(expect.objectContaining({ id: 'a' }), '2');
  });

  it('soltar en el mismo slot no reclasifica', () => {
    const onReclassify = vi.fn();
    render(
      <KaryotypeCanvas chromosomes={[chromo({ id: 'a', predicted_class: '1' })]} selectedId={null} onSelect={() => {}} onReclassify={onReclassify} />,
    );
    setDrop(PAD + 10, PAD + 10); // slot 1 = clase actual
    fireEvent(screen.getByTestId('chromosome-a'), new CustomEvent('konvadragend'));
    expect(onReclassify).not.toHaveBeenCalled();
  });

  it('en modo "Mover" (panMode) el cromosoma no reclasifica al arrastrar', () => {
    const onReclassify = vi.fn();
    render(
      <KaryotypeCanvas
        chromosomes={[chromo({ id: 'a', predicted_class: '1' })]}
        selectedId={null}
        viewport={{ ...INITIAL_VIEWPORT, panMode: true }}
        onSelect={() => {}}
        onReclassify={onReclassify}
      />,
    );
    setDrop(PAD + SLOT_W + 10, PAD + 10);
    fireEvent(screen.getByTestId('chromosome-a'), new CustomEvent('konvadragend'));
    expect(onReclassify).not.toHaveBeenCalled();
  });

  it('aplica el CSS filter de brillo/contraste al contenedor', () => {
    render(
      <KaryotypeCanvas
        chromosomes={[chromo({ id: 'a' })]}
        selectedId={null}
        viewport={{ ...INITIAL_VIEWPORT, brightness: 120, contrast: 80 }}
        onSelect={() => {}}
      />,
    );
    expect(screen.getByTestId('karyotype-viewer')).toHaveStyle({ filter: 'brightness(120%) contrast(80%)' });
  });

  it('con editable=false el cromosoma no es arrastrable (sin onReclassify)', () => {
    const onReclassify = vi.fn();
    render(
      <KaryotypeCanvas
        chromosomes={[chromo({ id: 'a', predicted_class: '1' })]}
        selectedId={null}
        editable={false}
        onSelect={() => {}}
        onReclassify={onReclassify}
      />,
    );
    setDrop(PAD + SLOT_W + 10, PAD + 10);
    fireEvent(screen.getByTestId('chromosome-a'), new CustomEvent('konvadragend'));
    expect(onReclassify).not.toHaveBeenCalled();
  });
});

/**
 * Recorte manual sobre el lienzo.
 *
 * Konva no existe en jsdom: el mock reenvía los eventos de ratón con un stage
 * de identidad, así que aquí se prueba la MÁQUINA DE ESTADOS del arrastre
 * —cuándo se emite el recorte y cuándo no—, no la conversión de coordenadas.
 * Esa transformación es de Konva y se valida en E2E.
 */
describe('KaryotypeCanvas — recorte manual', () => {
  function setPointer(x: number, y: number) {
    (globalThis as unknown as { __konvaPointer?: { x: number; y: number } }).__konvaPointer = { x, y };
  }

  /** Arrastra de una esquina a otra sobre el lienzo. */
  function arrastrar(desde: [number, number], hasta: [number, number]) {
    const stage = screen.getByTestId('karyo-stage');
    setPointer(...desde);
    fireEvent.mouseDown(stage);
    setPointer(...hasta);
    fireEvent.mouseMove(stage);
    fireEvent.mouseUp(stage);
  }

  function renderCrop(onCropDone = vi.fn(), props = {}) {
    render(
      <KaryotypeCanvas
        chromosomes={[chromo({ id: 'a' })]}
        selectedId="a"
        cropMode
        onCropDone={onCropDone}
        onSelect={() => {}}
        {...props}
      />,
    );
    return onCropDone;
  }

  it('arrastrar emite el bbox del rectángulo', () => {
    const onCropDone = renderCrop();

    arrastrar([10, 20], [50, 90]);

    expect(onCropDone).toHaveBeenCalledWith({ x: 10, y: 20, w: 40, h: 70 });
  });

  it('el bbox llega normalizado aunque se arrastre hacia atrás', () => {
    const onCropDone = renderCrop();

    arrastrar([50, 90], [10, 20]);

    expect(onCropDone).toHaveBeenCalledWith({ x: 10, y: 20, w: 40, h: 70 });
  });

  it('un clic suelto no dispara un recorte', () => {
    // Sin esto, cualquier clic mandaría al servidor un bbox degenerado.
    const onCropDone = renderCrop();

    arrastrar([30, 40], [31, 41]);

    expect(onCropDone).not.toHaveBeenCalled();
  });

  it('el rectángulo se ve mientras se arrastra y desaparece al soltar', () => {
    renderCrop();
    const stage = screen.getByTestId('karyo-stage');

    setPointer(10, 20);
    fireEvent.mouseDown(stage);
    setPointer(50, 90);
    fireEvent.mouseMove(stage);
    expect(screen.getByTestId('recorte-rect')).toBeInTheDocument();

    fireEvent.mouseUp(stage);
    expect(screen.queryByTestId('recorte-rect')).not.toBeInTheDocument();
  });

  it('salir del lienzo cancela el arrastre sin dejar el rectángulo pegado', () => {
    renderCrop();
    const stage = screen.getByTestId('karyo-stage');

    setPointer(10, 20);
    fireEvent.mouseDown(stage);
    setPointer(12, 22);   // demasiado corto para valer como recorte
    fireEvent.mouseMove(stage);
    fireEvent.mouseLeave(stage);

    expect(screen.queryByTestId('recorte-rect')).not.toBeInTheDocument();
  });

  it('sin cropMode el arrastre no emite nada', () => {
    const onCropDone = vi.fn();
    renderCrop(onCropDone, { cropMode: false });

    arrastrar([10, 20], [50, 90]);

    expect(onCropDone).not.toHaveBeenCalled();
  });

  it('recortando, arrastrar un cromosoma NO lo reclasifica', () => {
    // Los dos gestos son un arrastre: sin excluirse, recortar movería el
    // cromosoma de par sin que nadie lo pidiera.
    const onReclassify = vi.fn();
    render(
      <KaryotypeCanvas
        chromosomes={[chromo({ id: 'a', predicted_class: '1' })]}
        selectedId="a"
        cropMode
        onSelect={() => {}}
        onReclassify={onReclassify}
      />,
    );

    setDrop(PAD + SLOT_W + 10, PAD + 10);
    fireEvent(screen.getByTestId('chromosome-a'), new CustomEvent('konvadragend'));

    expect(onReclassify).not.toHaveBeenCalled();
  });
});
