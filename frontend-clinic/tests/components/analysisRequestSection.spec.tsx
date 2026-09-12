import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AnalysisRequestSection } from '../../src/clinic/components/AnalysisRequestSection';

describe('AnalysisRequestSection', () => {
  it('renderiza los 6 checkboxes', () => {
    render(<AnalysisRequestSection selected={[]} onChange={vi.fn()} />);
    expect(screen.getByLabelText(/Cariotipo de alta resolución/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Array-CGH/)).toBeInTheDocument();
  });

  it('checkbox marcado por defecto se refleja en el estado', () => {
    render(<AnalysisRequestSection selected={['karyotype_high_res']} onChange={vi.fn()} />);
    expect(screen.getByLabelText(/Cariotipo de alta resolución/)).toBeChecked();
    expect(screen.getByLabelText(/Array-CGH/)).not.toBeChecked();
  });

  it('marcar un checkbox lo agrega a la selección', async () => {
    const onChange = vi.fn();
    render(<AnalysisRequestSection selected={['karyotype_high_res']} onChange={onChange} />);
    await userEvent.click(screen.getByLabelText(/FISH/));
    expect(onChange).toHaveBeenCalledWith(['karyotype_high_res', 'fish']);
  });

  it('desmarcar un checkbox lo quita de la selección', async () => {
    const onChange = vi.fn();
    render(<AnalysisRequestSection selected={['karyotype_high_res', 'fish']} onChange={onChange} />);
    await userEvent.click(screen.getByLabelText(/FISH/));
    expect(onChange).toHaveBeenCalledWith(['karyotype_high_res']);
  });
});
