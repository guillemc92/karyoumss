import { describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SampleFormModal } from '../../src/clinic/components/SampleFormModal';
import { renderWithProviders } from '../testUtils';

describe('SampleFormModal', () => {
  it('modo create: renderiza campos vacíos', () => {
    renderWithProviders(<SampleFormModal mode="create" onSubmit={vi.fn()} onCancel={vi.fn()} />);
    expect(screen.getByLabelText(/CHN/)).toHaveValue('');
    expect(screen.getByText('Nueva Muestra')).toBeInTheDocument();
  });

  it('modo create: submit vacío muestra errores de validación', async () => {
    const onSubmit = vi.fn();
    renderWithProviders(<SampleFormModal mode="create" onSubmit={onSubmit} onCancel={vi.fn()} />);
    await userEvent.click(screen.getByText('Guardar Muestra'));
    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByText('CHN requerido')).toBeInTheDocument();
  });

  it('modo create: submit válido llama onSubmit con los datos', async () => {
    const onSubmit = vi.fn();
    renderWithProviders(<SampleFormModal mode="create" onSubmit={onSubmit} onCancel={vi.fn()} />);
    await userEvent.type(screen.getByLabelText(/CHN/), 'CHN-2026-07-12-0001');
    await userEvent.type(screen.getByLabelText(/Paciente/), 'ANON-001');
    await userEvent.click(screen.getByText('Guardar Muestra'));
    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({ chn_code: 'CHN-2026-07-12-0001', patient_ref: 'ANON-001' }),
    );
  });

  it('modo edit: campo CHN está deshabilitado (RN-04)', () => {
    renderWithProviders(
      <SampleFormModal
        mode="edit"
        initial={{
          id: '1', chn_code: 'CHN-X', patient_ref: 'ANON-X', image_path: '', status: 'READY',
          analyst: 1, analyst_name: 'A', supervisor: null, supervisor_name: '', metadata: {},
          created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z',
        }}
        onSubmit={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByLabelText(/CHN/)).toBeDisabled();
  });

  it('click en Cancelar llama onCancel', async () => {
    const onCancel = vi.fn();
    renderWithProviders(<SampleFormModal mode="create" onSubmit={vi.fn()} onCancel={onCancel} />);
    await userEvent.click(screen.getByText('Cancelar'));
    expect(onCancel).toHaveBeenCalled();
  });
});
