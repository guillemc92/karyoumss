import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ClinicalHistorySection } from '../../src/clinic/components/ClinicalHistorySection';

const EMPTY = { indication: '', family_history: '' };

describe('ClinicalHistorySection', () => {
  it('renderiza los 2 textareas', () => {
    render(<ClinicalHistorySection value={EMPTY} onChange={vi.fn()} />);
    expect(screen.getByPlaceholderText(/motivo de la solicitud/)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Historial de condiciones/)).toBeInTheDocument();
  });

  it('escribir en indicación llama onChange', async () => {
    const onChange = vi.fn();
    render(<ClinicalHistorySection value={EMPTY} onChange={onChange} />);
    await userEvent.type(screen.getByPlaceholderText(/motivo de la solicitud/), 'X');
    expect(onChange).toHaveBeenCalledWith({ ...EMPTY, indication: 'X' });
  });

  it('escribir en antecedentes familiares llama onChange', async () => {
    const onChange = vi.fn();
    render(<ClinicalHistorySection value={EMPTY} onChange={onChange} />);
    await userEvent.type(screen.getByPlaceholderText(/Historial de condiciones/), 'Y');
    expect(onChange).toHaveBeenCalledWith({ ...EMPTY, family_history: 'Y' });
  });
});
