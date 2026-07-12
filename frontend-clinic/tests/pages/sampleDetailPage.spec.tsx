import { describe, expect, it } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Routes, Route } from 'react-router-dom';
import { SampleDetailPage } from '../../src/clinic/pages/SampleDetailPage';
import { SampleFormPage } from '../../src/clinic/pages/SampleFormPage';
import { renderWithProviders } from '../testUtils';

const SAMPLE_ID = '00000000-0000-0000-0000-000000000442';

function renderDetail(id: string) {
  return renderWithProviders(
    <Routes>
      <Route path="/clinic/samples/:id" element={<SampleDetailPage />} />
    </Routes>,
    { route: `/clinic/samples/${id}` },
  );
}

describe('SampleDetailPage', () => {
  it('muestra skeleton mientras carga', () => {
    renderDetail(SAMPLE_ID);
    expect(screen.getByLabelText('Cargando')).toBeInTheDocument();
  });

  it('renderiza el CHN y estado tras cargar', async () => {
    renderDetail(SAMPLE_ID);
    await waitFor(() => expect(screen.getByText('CHN-2026-04-10-0442')).toBeInTheDocument());
  });

  it('muestra la metadata de la muestra', async () => {
    renderDetail(SAMPLE_ID);
    await waitFor(() => expect(screen.getByText(/notes: Posible variante estructural/)).toBeInTheDocument());
  });

  it('id inexistente muestra mensaje de error', async () => {
    renderDetail('nonexistent-id');
    await waitFor(() => expect(screen.getByText(/no encontrada/)).toBeInTheDocument());
  });

  it('click en Editar navega a la página de edición', async () => {
    renderWithProviders(
      <Routes>
        <Route path="/clinic/samples/:id" element={<SampleDetailPage />} />
        <Route path="/clinic/samples/:id/edit" element={<SampleFormPage />} />
      </Routes>,
      { route: `/clinic/samples/${SAMPLE_ID}` },
    );
    await waitFor(() => expect(screen.getByText('CHN-2026-04-10-0442')).toBeInTheDocument());
    await userEvent.click(screen.getByText('Editar'));
    await waitFor(() => expect(screen.getByText('Editar Muestra')).toBeInTheDocument());
  });

  it('link "Ver cariotipo" apunta al visor vanilla con el sample id', async () => {
    renderDetail(SAMPLE_ID);
    await waitFor(() => expect(screen.getByText('CHN-2026-04-10-0442')).toBeInTheDocument());
    const link = screen.getByText(/Ver cariotipo/);
    expect(link).toHaveAttribute('href', `/correccion de cariotipo.html?sample=${SAMPLE_ID}`);
  });
});
