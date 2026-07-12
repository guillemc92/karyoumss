import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SamplePagination } from '../../src/clinic/components/SamplePagination';

describe('SamplePagination', () => {
  it('muestra el rango y total correctos', () => {
    render(<SamplePagination page={1} pageSize={8} total={20} onPageChange={vi.fn()} />);
    expect(screen.getByText('Mostrando 1-8 de 20')).toBeInTheDocument();
  });

  it('botón Siguiente llama onPageChange con page+1', async () => {
    const onPageChange = vi.fn();
    render(<SamplePagination page={1} pageSize={8} total={20} onPageChange={onPageChange} />);
    await userEvent.click(screen.getByText('Siguiente →'));
    expect(onPageChange).toHaveBeenCalledWith(2);
  });

  it('botón Anterior llama onPageChange con page-1', async () => {
    const onPageChange = vi.fn();
    render(<SamplePagination page={2} pageSize={8} total={20} onPageChange={onPageChange} />);
    await userEvent.click(screen.getByText('← Anterior'));
    expect(onPageChange).toHaveBeenCalledWith(1);
  });

  it('botón Anterior está deshabilitado en la primera página', () => {
    render(<SamplePagination page={1} pageSize={8} total={20} onPageChange={vi.fn()} />);
    expect(screen.getByText('← Anterior')).toBeDisabled();
  });

  it('botón Siguiente está deshabilitado en la última página', () => {
    render(<SamplePagination page={3} pageSize={8} total={20} onPageChange={vi.fn()} />);
    expect(screen.getByText('Siguiente →')).toBeDisabled();
  });

  it('con total=0, muestra rango 0-0', () => {
    render(<SamplePagination page={1} pageSize={8} total={0} onPageChange={vi.fn()} />);
    expect(screen.getByText('Mostrando 0-0 de 0')).toBeInTheDocument();
  });
});
