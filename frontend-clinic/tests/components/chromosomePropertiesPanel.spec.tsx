import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ChromosomePropertiesPanel } from '../../src/clinic/components/ChromosomePropertiesPanel';
import type { Chromosome } from '../../src/clinic/types/karyotype';

function chromo(overrides: Partial<Chromosome> = {}): Chromosome {
  return {
    id: 'c1', predicted_class: '1', position_index: 0, confidence_score: '0.960',
    semaphore: 'green', resolution_status: 'AUTO', xai_viewed: false,
    is_anomaly: false,
    measures: {}, bbox: {}, order: 0, ...overrides,
  };
}

describe('ChromosomePropertiesPanel', () => {
  it('sin cromosoma muestra el estado vacío', () => {
    render(<ChromosomePropertiesPanel chromosome={null} />);
    expect(screen.getByTestId('chromosome-props-empty')).toBeInTheDocument();
  });

  it('con medidas ausentes muestra los fallbacks "—"', () => {
    render(<ChromosomePropertiesPanel chromosome={chromo({ measures: {} })} />);
    expect(screen.getByTestId('props-length')).toHaveTextContent('—');
  });

  it('cromosoma rojo (confidence null) muestra "—" y etiqueta de falla', () => {
    render(<ChromosomePropertiesPanel chromosome={chromo({ semaphore: 'red', confidence_score: null })} />);
    expect(screen.getByTestId('props-confidence')).toHaveTextContent('—');
    expect(screen.getByTestId('props-semaphore')).toHaveTextContent(/fallida/i);
  });

  it('con medidas presentes las muestra', () => {
    render(
      <ChromosomePropertiesPanel
        chromosome={chromo({ measures: { length_um: 5.2, centromeric_index: 0.42, band_count: 380, quality: 'alta' } })}
      />,
    );
    expect(screen.getByTestId('props-length')).toHaveTextContent('5.2');
  });
});
