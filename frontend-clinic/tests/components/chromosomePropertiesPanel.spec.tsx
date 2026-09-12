import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChromosomePropertiesPanel } from '../../src/clinic/components/ChromosomePropertiesPanel';
import type { Chromosome } from '../../src/clinic/types/karyotype';

function chromo(overrides: Partial<Chromosome> = {}): Chromosome {
  return {
    id: 'c1', predicted_class: '1', position_index: 0, confidence_score: '0.960',
    semaphore: 'green', resolution_status: 'AUTO', xai_viewed: false,
    is_anomaly: false,
    is_active: true,
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

  // --- P3 (corrección manual, DD-KARYO-003) ---
  describe('acciones P3', () => {
    it('sin callbacks P3 no muestra el bloque de corrección', () => {
      render(<ChromosomePropertiesPanel chromosome={chromo()} />);
      expect(screen.queryByTestId('chromosome-p3-actions')).not.toBeInTheDocument();
    });

    it('reclasificar por "Mover a par" dispara onReclassify con la clase destino', async () => {
      const onReclassify = vi.fn();
      render(<ChromosomePropertiesPanel chromosome={chromo({ predicted_class: '1' })} onReclassify={onReclassify} />);
      await userEvent.selectOptions(screen.getByTestId('reclassify-select'), '7');
      expect(onReclassify).toHaveBeenCalledWith(expect.objectContaining({ id: 'c1' }), '7');
    });

    it('separar dispara onSplit', async () => {
      const onSplit = vi.fn();
      render(<ChromosomePropertiesPanel chromosome={chromo()} onSplit={onSplit} />);
      await userEvent.click(screen.getByTestId('action-split'));
      expect(onSplit).toHaveBeenCalledOnce();
    });

    it('resolver cruce dispara onResolveCross', async () => {
      const onResolveCross = vi.fn();
      render(<ChromosomePropertiesPanel chromosome={chromo()} onResolveCross={onResolveCross} />);
      await userEvent.click(screen.getByTestId('action-cross'));
      expect(onResolveCross).toHaveBeenCalledOnce();
    });

    it('unir: sin pick previo muestra "marcar"; con pick de otro muestra "confirmar"', async () => {
      const onJoinPick = vi.fn();
      const onJoinConfirm = vi.fn();
      const { rerender } = render(
        <ChromosomePropertiesPanel chromosome={chromo({ id: 'c1' })} onJoinPick={onJoinPick} onJoinConfirm={onJoinConfirm} joinPick={null} />,
      );
      await userEvent.click(screen.getByTestId('action-join-pick'));
      expect(onJoinPick).toHaveBeenCalledOnce();

      // Con un fragmento ya marcado (otro id) → botón de confirmar.
      rerender(
        <ChromosomePropertiesPanel
          chromosome={chromo({ id: 'c2', predicted_class: '2' })}
          onJoinPick={onJoinPick}
          onJoinConfirm={onJoinConfirm}
          joinPick={{ id: 'c1', label: '1' }}
        />,
      );
      const confirm = screen.getByTestId('action-join-confirm');
      expect(confirm).toHaveTextContent('Unir con par 1');
      await userEvent.click(confirm);
      expect(onJoinConfirm).toHaveBeenCalledWith(expect.objectContaining({ id: 'c2' }));
    });
  });
});
