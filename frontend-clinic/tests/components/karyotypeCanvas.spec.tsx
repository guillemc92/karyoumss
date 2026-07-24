import { describe, expect, it, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { KaryotypeCanvas } from '../../src/clinic/components/KaryotypeCanvas';
import type { Chromosome } from '../../src/clinic/types/karyotype';
import { PAD, SLOT_W } from '../../src/clinic/lib/karyoLayout';

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
