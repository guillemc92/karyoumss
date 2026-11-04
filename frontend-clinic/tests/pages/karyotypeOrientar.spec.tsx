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
import { fijarBboxMock, fijarContornoMock, setSampleStatus } from '../../src/clinic/msw/handlers';
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

  it('ajuste fino (DD-KARYO-008 T4): +5° dos veces gira el cromosoma 10° y deja dos ORIENT', async () => {
    // Un 10 × 100 inclinado 30°, centrado en (300, 200), con su caja: se endereza girándolo −30°.
    const a = Math.PI / 6;
    const contour = [[-5, -50], [5, -50], [5, 50], [-5, 50]].map(([x, y]) => [
      300 + x * Math.cos(a) - y * Math.sin(a), 200 + x * Math.sin(a) + y * Math.cos(a),
    ]);
    fijarBboxMock(SAMPLE, CROMOSOMA, { x: 270, y: 152, w: 60, h: 96 });
    fijarContornoMock(SAMPLE, CROMOSOMA, contour);
    const user = userEvent.setup();
    renderPage();
    const silueta = () => screen.getByTestId(`chromosome-silueta-${CROMOSOMA}`);
    await waitFor(() => expect(silueta()).toHaveAttribute('data-giro-final', '330'));
    await user.click(screen.getByTestId(`chromosome-${CROMOSOMA}`));

    await user.click(await screen.findByTestId('action-ajuste-mas'));
    await waitFor(() => expect(screen.getByTestId('ajuste-valor')).toHaveTextContent('Ajuste +5°'));
    await user.click(screen.getByTestId('action-ajuste-mas'));
    await waitFor(() => expect(silueta()).toHaveAttribute('data-giro-final', '340'));
    expect(screen.getByTestId('ajuste-valor')).toHaveTextContent('Ajuste +10°');

    // Girar 180° conserva el ajuste: 330 + 10 + 180 = 520 → 160.
    await user.click(screen.getByTestId('action-girar'));
    await waitFor(() => expect(silueta()).toHaveAttribute('data-giro-final', '160'));
    expect(screen.getByTestId('ajuste-valor')).toHaveTextContent('Ajuste +10°');

    await user.click(screen.getByTestId('toggle-audit'));
    expect(await screen.findAllByText(/Giró o volteó un cromosoma/)).toHaveLength(3);
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
