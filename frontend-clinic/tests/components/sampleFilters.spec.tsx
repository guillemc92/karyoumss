import { describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SampleFilters } from '../../src/clinic/components/SampleFilters';

describe('SampleFilters', () => {
  it('cambiar el select de estado llama onChange', async () => {
    const onChange = vi.fn();
    render(<SampleFilters value={{}} onChange={onChange} />);
    await userEvent.selectOptions(screen.getByLabelText('Filtrar por estado'), 'READY');
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ status: 'READY' }));
  });

  it('volver a "Todas" limpia el filtro de status', async () => {
    const onChange = vi.fn();
    render(<SampleFilters value={{ status: 'READY' }} onChange={onChange} />);
    await userEvent.selectOptions(screen.getByLabelText('Filtrar por estado'), '');
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ status: undefined }));
  });

  it('cambiar fecha desde llama onChange', async () => {
    const onChange = vi.fn();
    render(<SampleFilters value={{}} onChange={onChange} />);
    const input = screen.getByLabelText('Fecha desde');
    await userEvent.type(input, '2026-07-01');
    expect(onChange).toHaveBeenCalled();
  });

  it('cambiar fecha hasta llama onChange', async () => {
    const onChange = vi.fn();
    render(<SampleFilters value={{}} onChange={onChange} />);
    const input = screen.getByLabelText('Fecha hasta');
    await userEvent.type(input, '2026-07-12');
    expect(onChange).toHaveBeenCalled();
  });

  it('escribir en búsqueda CHN dispara onChange tras el debounce', async () => {
    const onChange = vi.fn();
    render(<SampleFilters value={{}} onChange={onChange} />);
    await userEvent.type(screen.getByLabelText('Buscar por CHN'), 'CHN-2026');
    await waitFor(() => expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ chn_query: 'CHN-2026' })), {
      timeout: 1000,
    });
  });
});
