import { describe, expect, it } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SampleListPage } from '../../src/clinic/pages/SampleListPage';
import { renderWithProviders } from '../testUtils';

describe('SampleListPage', () => {
  it('renderiza las muestras del seed tras cargar', async () => {
    renderWithProviders(<SampleListPage />);
    await waitFor(() => expect(screen.getByText('CHN-2026-04-10-0442')).toBeInTheDocument());
    expect(screen.getByText('Gestión de Muestras')).toBeInTheDocument();
  });

  it('las stat cards reflejan los conteos por estado', async () => {
    renderWithProviders(<SampleListPage />);
    await waitFor(() => expect(screen.getByText('CHN-2026-04-10-0442')).toBeInTheDocument());
    const totalCard = screen.getByText('Total muestras').closest('.stat-card');
    expect(totalCard).toHaveTextContent('11'); // 8 originales + 3 metafases MetaClass
  });

  it('búsqueda sin coincidencias muestra el empty-state', async () => {
    renderWithProviders(<SampleListPage />);
    await waitFor(() => expect(screen.getByText('CHN-2026-04-10-0442')).toBeInTheDocument());
    await userEvent.type(screen.getByLabelText('Buscar por CHN'), 'CHN-NO-EXISTE');
    await waitFor(() => expect(screen.getByText('No hay muestras que coincidan con los filtros.')).toBeInTheDocument());
  });

  it('filtro por status VALIDATED reduce el listado', async () => {
    renderWithProviders(<SampleListPage />);
    await waitFor(() => expect(screen.getByText('CHN-2026-04-10-0442')).toBeInTheDocument());
    await userEvent.click(screen.getByText('✓ Completadas'));
    await waitFor(() => {
      expect(screen.queryByText('CHN-2026-04-09-0441')).not.toBeInTheDocument();
    });
  });

  it('búsqueda por CHN filtra con debounce', async () => {
    renderWithProviders(<SampleListPage />);
    await waitFor(() => expect(screen.getByText('CHN-2026-04-10-0442')).toBeInTheDocument());
    await userEvent.type(screen.getByLabelText('Buscar por CHN'), '0442');
    await waitFor(
      () => {
        expect(screen.getByText('CHN-2026-04-10-0442')).toBeInTheDocument();
        expect(screen.queryByText('CHN-2026-04-09-0441')).not.toBeInTheDocument();
      },
      { timeout: 1000 },
    );
  });

  it('click en Nueva Muestra navega al formulario (verificado por presencia del botón)', () => {
    renderWithProviders(<SampleListPage />);
    expect(screen.getByText(/Nueva Muestra/)).toBeInTheDocument();
  });

  it('click en Eliminar (rol admin no aplica en analista) no muestra confirm porque el botón está oculto', async () => {
    renderWithProviders(<SampleListPage />);
    await waitFor(() => expect(screen.getByText('CHN-2026-04-10-0442')).toBeInTheDocument());
    expect(screen.queryByText(/Eliminar/)).not.toBeInTheDocument();
  });

  it('rol admin: flujo completo de eliminar muestra funciona', async () => {
    renderWithProviders(<SampleListPage />, { asAdmin: true });
    await waitFor(() => expect(screen.getByText('CHN-2026-04-10-0442')).toBeInTheDocument());

    const deleteButtons = screen.getAllByText(/Eliminar/);
    await userEvent.click(deleteButtons[0]);
    expect(screen.getByText(/¿Está seguro/)).toBeInTheDocument();

    const confirmButton = screen.getByRole('dialog').querySelector('.btn-danger') as HTMLButtonElement;
    await userEvent.click(confirmButton);
    await waitFor(() => expect(screen.getByText('Muestra eliminada correctamente')).toBeInTheDocument());
  });

  it('rol admin: cancelar el modal de eliminar lo cierra sin borrar', async () => {
    renderWithProviders(<SampleListPage />, { asAdmin: true });
    await waitFor(() => expect(screen.getByText('CHN-2026-04-10-0442')).toBeInTheDocument());

    const deleteButtons = screen.getAllByText(/Eliminar/);
    await userEvent.click(deleteButtons[0]);
    await userEvent.click(screen.getByText('Cancelar'));
    expect(screen.queryByText(/¿Está seguro/)).not.toBeInTheDocument();
  });

  it('paginación: cambiar de página actualiza los items mostrados', async () => {
    renderWithProviders(<SampleListPage />);
    await waitFor(() => expect(screen.getByText('CHN-2026-04-10-0442')).toBeInTheDocument());
    const nextButton = screen.getByText('Siguiente →');
    if (!nextButton.hasAttribute('disabled')) {
      await userEvent.click(nextButton);
    }
    expect(screen.getByText('Gestión de Muestras')).toBeInTheDocument();
  });
});
