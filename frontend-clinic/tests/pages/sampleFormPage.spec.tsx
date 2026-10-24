import { describe, expect, it } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Routes, Route } from 'react-router-dom';
import { SampleFormPage } from '../../src/clinic/pages/SampleFormPage';
import { SampleListPage } from '../../src/clinic/pages/SampleListPage';
import { renderWithProviders } from '../testUtils';

function renderCreate() {
  return renderWithProviders(
    <Routes>
      <Route path="/clinic/samples" element={<SampleListPage />} />
      <Route path="/clinic/samples/new" element={<SampleFormPage />} />
    </Routes>,
    { route: '/clinic/samples/new' },
  );
}

function renderEdit(id: string) {
  return renderWithProviders(
    <Routes>
      <Route path="/clinic/samples" element={<SampleListPage />} />
      <Route path="/clinic/samples/:id/edit" element={<SampleFormPage />} />
    </Routes>,
    { route: `/clinic/samples/${id}/edit` },
  );
}

describe('SampleFormPage', () => {
  it('modo create: renderiza el modal de nueva muestra', () => {
    renderCreate();
    expect(screen.getByText('Nueva Muestra')).toBeInTheDocument();
  });

  it('modo create: crear una muestra navega de vuelta a la lista', async () => {
    renderCreate();
    await userEvent.type(screen.getByLabelText(/CHN/), 'CHN-FORM-001');
    await userEvent.type(screen.getByLabelText(/Paciente/), 'ANON-FORM');
    await userEvent.click(screen.getByText('Guardar Muestra'));
    await waitFor(() => expect(screen.getByText('Gestión de Muestras')).toBeInTheDocument());
  });

  it('modo edit: carga los datos existentes de la muestra', async () => {
    renderEdit('00000000-0000-0000-0000-000000000442');
    await waitFor(() => expect(screen.getByLabelText(/Paciente/)).toHaveValue('ANON-442'));
  });

  it('click en Cancelar navega de vuelta a la lista', async () => {
    renderCreate();
    await userEvent.click(screen.getByText('Cancelar'));
    await waitFor(() => expect(screen.getByText('Gestión de Muestras')).toBeInTheDocument());
  });

  it('modo edit: guardar cambios navega de vuelta a la lista', async () => {
    renderEdit('00000000-0000-0000-0000-000000000442');
    await waitFor(() => expect(screen.getByLabelText(/Paciente/)).toHaveValue('ANON-442'));
    await userEvent.clear(screen.getByLabelText(/Paciente/));
    await userEvent.type(screen.getByLabelText(/Paciente/), 'ANON-442-EDITADO');
    await userEvent.click(screen.getByText('Guardar Muestra'));
    await waitFor(() => expect(screen.getByText('Gestión de Muestras')).toBeInTheDocument());
  });
});
