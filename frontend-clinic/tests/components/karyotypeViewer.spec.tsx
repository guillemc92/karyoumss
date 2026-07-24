import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { KaryotypeViewer } from '../../src/clinic/components/KaryotypeViewer';
import type { Chromosome } from '../../src/clinic/types/karyotype';

function chromo(overrides: Partial<Chromosome> = {}): Chromosome {
  return {
    id: 'c1',
    predicted_class: '1',
    position_index: 0,
    confidence_score: '0.960',
    semaphore: 'green',
    resolution_status: 'AUTO',
    xai_viewed: false,
    is_anomaly: false,
    is_active: true,
    measures: {},
    bbox: {},
    order: 0,
    ...overrides,
  };
}

describe('KaryotypeViewer', () => {
  it('renderiza los cromosomas con su semáforo', () => {
    const chromosomes = [
      chromo({ id: 'g', predicted_class: '1', semaphore: 'green' }),
      chromo({ id: 'o', predicted_class: '18', semaphore: 'orange', confidence_score: '0.720' }),
      chromo({ id: 'r', predicted_class: '21', semaphore: 'red', confidence_score: null }),
    ];
    render(<KaryotypeViewer chromosomes={chromosomes} selectedId={null} onSelect={() => {}} />);

    expect(screen.getByTestId('chromosome-g')).toHaveAttribute('data-semaphore', 'green');
    expect(screen.getByTestId('chromosome-o')).toHaveAttribute('data-semaphore', 'orange');
    expect(screen.getByTestId('chromosome-r')).toHaveAttribute('data-semaphore', 'red');
  });

  it('renderiza los 24 slots (1–22, X, Y)', () => {
    render(<KaryotypeViewer chromosomes={[]} selectedId={null} onSelect={() => {}} />);
    expect(screen.getByTestId('karyo-slot-1')).toBeInTheDocument();
    expect(screen.getByTestId('karyo-slot-22')).toBeInTheDocument();
    expect(screen.getByTestId('karyo-slot-X')).toBeInTheDocument();
    expect(screen.getByTestId('karyo-slot-Y')).toBeInTheDocument();
  });

  it('click en un cromosoma dispara onSelect con ese cromosoma', async () => {
    const onSelect = vi.fn();
    const c = chromo({ id: 'clickable', predicted_class: '5' });
    render(<KaryotypeViewer chromosomes={[c]} selectedId={null} onSelect={onSelect} />);
    await userEvent.click(screen.getByTestId('chromosome-clickable'));
    expect(onSelect).toHaveBeenCalledWith(c);
  });

  it('el cromosoma seleccionado marca aria-pressed', () => {
    const c = chromo({ id: 'sel' });
    render(<KaryotypeViewer chromosomes={[c]} selectedId="sel" onSelect={() => {}} />);
    expect(screen.getByTestId('chromosome-sel')).toHaveAttribute('aria-pressed', 'true');
  });

  it('ordena las copias de un par por position_index', () => {
    const chromosomes = [
      chromo({ id: 'copy1', predicted_class: '7', position_index: 1 }),
      chromo({ id: 'copy0', predicted_class: '7', position_index: 0 }),
    ];
    render(<KaryotypeViewer chromosomes={chromosomes} selectedId={null} onSelect={() => {}} />);
    const slot = screen.getByTestId('karyo-slot-7');
    const buttons = slot.querySelectorAll('button');
    expect(buttons[0].getAttribute('data-testid')).toBe('chromosome-copy0');
    expect(buttons[1].getAttribute('data-testid')).toBe('chromosome-copy1');
  });
});
