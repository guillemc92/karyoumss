/**
 * Girar 180° y voltear desde el visor (DD-KARYO-007 T7), contra el doble MSW:
 * el botón del panel cambia cómo se pinta el cromosoma en el cariograma y deja
 * la acción en la bitácora.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Route, Routes } from 'react-router-dom';
import { KaryotypePage } from '../../src/clinic/pages/KaryotypePage';
import { setSampleStatus } from '../../src/clinic/msw/handlers';
import { renderWithProviders } from '../testUtils';

const metafase = vi.hoisted(() => ({
  doble: { width: 1024, height: 768, naturalWidth: 1024, naturalHeight: 768 },
  valor: null as unknown,
}));
vi.mock('../../src/clinic/hooks/useMetaphaseImage', () => ({
  useMetaphaseImage: () => metafase.valor,
}));

const SAMPLE = '00000000-0000-0000-0000-000000000442';
const CROMOSOMA = `${SAMPLE}-chr-1-0`;

beforeEach(() => {
  metafase.valor = { imagen: metafase.doble, estado: 'lista' };
});

function renderPage() {
  return renderWithProviders(
    <Routes>
      <Route path="/clinic/samples/:id/karyotype" element={<KaryotypePage />} />
    </Routes>,
    { route: `/clinic/samples/${SAMPLE}/karyotype` },
  );
}

describe('KaryotypePage — girar y voltear (DD-KARYO-007 T7)', () => {
  it('girar y voltear cambian el cariograma y quedan en la bitácora', async () => {
    const user = userEvent.setup();
    renderPage();
    const img = await screen.findByTestId(`chromosome-img-${CROMOSOMA}`);
    expect(img).toHaveAttribute('data-orientacion', '0');
    await user.click(screen.getByTestId(`chromosome-${CROMOSOMA}`));

    await user.click(await screen.findByTestId('action-girar'));
    await waitFor(() =>
      expect(screen.getByTestId(`chromosome-img-${CROMOSOMA}`)).toHaveAttribute('data-orientacion', '180'));
    await user.click(screen.getByTestId('action-voltear'));
    await waitFor(() =>
      expect(screen.getByTestId(`chromosome-img-${CROMOSOMA}`)).toHaveAttribute('data-orientacion', '180-v'));

    await user.click(screen.getByTestId('toggle-audit'));
    expect(await screen.findAllByText(/Giró o volteó un cromosoma/)).toHaveLength(2);
  });

  it('en un caso validado no se puede orientar', async () => {
    setSampleStatus(SAMPLE, 'ANALYST_VALIDATED');
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByTestId(`chromosome-${CROMOSOMA}`));
    await screen.findByTestId('chromosome-props');
    expect(screen.queryByTestId('action-girar')).toBeNull();
  });

  it('sin metafase no hay nada que orientar', async () => {
    metafase.valor = { imagen: null, estado: 'sin-imagen' };
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByTestId(`chromosome-${CROMOSOMA}`));
    await screen.findByTestId('chromosome-props');
    expect(screen.queryByTestId('action-girar')).toBeNull();
  });
});
