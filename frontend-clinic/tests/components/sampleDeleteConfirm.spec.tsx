import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SampleDeleteConfirm } from '../../src/clinic/components/SampleDeleteConfirm';

describe('SampleDeleteConfirm', () => {
  it('muestra el CHN de la muestra a eliminar', () => {
    render(<SampleDeleteConfirm chnCode="CHN-DEL-001" onConfirm={vi.fn()} onCancel={vi.fn()} />);
    expect(screen.getByText('CHN-DEL-001')).toBeInTheDocument();
  });

  it('click en Eliminar llama onConfirm', async () => {
    const onConfirm = vi.fn();
    render(<SampleDeleteConfirm chnCode="CHN-DEL-001" onConfirm={onConfirm} onCancel={vi.fn()} />);
    await userEvent.click(screen.getByText('Eliminar'));
    expect(onConfirm).toHaveBeenCalled();
  });

  it('click en Cancelar llama onCancel', async () => {
    const onCancel = vi.fn();
    render(<SampleDeleteConfirm chnCode="CHN-DEL-001" onConfirm={vi.fn()} onCancel={onCancel} />);
    await userEvent.click(screen.getByText('Cancelar'));
    expect(onCancel).toHaveBeenCalled();
  });

  it('mientras isDeleting=true, el botón muestra estado de carga y está deshabilitado', () => {
    render(<SampleDeleteConfirm chnCode="CHN-DEL-001" onConfirm={vi.fn()} onCancel={vi.fn()} isDeleting />);
    expect(screen.getByText('Eliminando...')).toBeDisabled();
  });
});
