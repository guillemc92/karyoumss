import { describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SampleTable } from '../../src/clinic/components/SampleTable';
import { renderWithProviders } from '../testUtils';
import type { SampleListItem } from '../../src/clinic/types/sample';

const items: SampleListItem[] = [
  {
    id: '1', chn_code: 'CHN-A', patient_ref: 'ANON-A', status: 'READY',
    analyst_name: 'Dra. García', has_karyotype: true,
    created_at: '2026-04-10T09:00:00Z', updated_at: '2026-04-10T09:00:00Z',
  },
  {
    id: '2', chn_code: 'CHN-B', patient_ref: 'ANON-B', status: 'PROCESSING',
    analyst_name: 'Dr. Martínez', has_karyotype: false,
    created_at: '2026-04-09T09:00:00Z', updated_at: '2026-04-09T09:00:00Z',
  },
];

describe('SampleTable', () => {
  it('renderiza las filas con CHN y estado', () => {
    renderWithProviders(<SampleTable items={items} onEdit={vi.fn()} onDelete={vi.fn()} />);
    expect(screen.getByText('CHN-A')).toBeInTheDocument();
    expect(screen.getByText('CHN-B')).toBeInTheDocument();
  });

  it('muestra estado vacío cuando no hay items', () => {
    renderWithProviders(<SampleTable items={[]} onEdit={vi.fn()} onDelete={vi.fn()} />);
    expect(screen.getByText(/No hay muestras/)).toBeInTheDocument();
  });

  it('click en Editar llama onEdit con el id correcto', async () => {
    const onEdit = vi.fn();
    renderWithProviders(<SampleTable items={items} onEdit={onEdit} onDelete={vi.fn()} />);
    const editButtons = screen.getAllByText(/Editar/);
    await userEvent.click(editButtons[0]);
    expect(onEdit).toHaveBeenCalledWith('1');
  });

  it('analista (rol por defecto en forceAnalystOnMount) NO ve botón Eliminar (RN-06 gating)', () => {
    renderWithProviders(<SampleTable items={items} onEdit={vi.fn()} onDelete={vi.fn()} />);
    expect(screen.queryByText(/Eliminar/)).not.toBeInTheDocument();
  });

  it('el link de CHN apunta al detalle de la muestra', () => {
    renderWithProviders(<SampleTable items={items} onEdit={vi.fn()} onDelete={vi.fn()} />);
    const link = screen.getByText('CHN-A').closest('a');
    expect(link).toHaveAttribute('href', '/clinic/samples/1');
  });

  it('muestra el nombre del analista', () => {
    renderWithProviders(<SampleTable items={items} onEdit={vi.fn()} onDelete={vi.fn()} />);
    expect(screen.getByText('Dra. García')).toBeInTheDocument();
  });
});
