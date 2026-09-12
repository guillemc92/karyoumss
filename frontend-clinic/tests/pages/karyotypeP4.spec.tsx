import { describe, expect, it } from 'vitest';
import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Route, Routes } from 'react-router-dom';
import { KaryotypePage } from '../../src/clinic/pages/KaryotypePage';
import { setDegradedMode } from '../../src/clinic/msw/handlers';
import { renderWithProviders } from '../testUtils';

const SAMPLE = '00000000-0000-0000-0000-000000000442';

function renderPage() {
  return renderWithProviders(
    <Routes>
      <Route path="/clinic/samples/:id/karyotype" element={<KaryotypePage />} />
    </Routes>,
    { route: `/clinic/samples/${SAMPLE}/karyotype` },
  );
}

describe('KaryotypePage — P4 (herramientas de imagen + modo degradado)', () => {
  it('la toolbar de imagen ajusta el zoom y restablece', async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByTestId('karyotype-viewer');
    expect(screen.getByTestId('viewport-zoom-level')).toHaveTextContent('100%');

    await user.click(screen.getByTestId('viewport-zoom-in'));
    expect(screen.getByTestId('viewport-zoom-level')).toHaveTextContent('125%');

    await user.click(screen.getByTestId('viewport-reset'));
    expect(screen.getByTestId('viewport-zoom-level')).toHaveTextContent('100%');
  });

  it('el brillo aplica un CSS filter al lienzo', async () => {
    renderPage();
    const viewer = await screen.findByTestId('karyotype-viewer');
    expect(viewer).toHaveStyle({ filter: 'brightness(100%) contrast(100%)' });
    fireEvent.change(screen.getByTestId('viewport-brightness'), { target: { value: '130' } });
    await waitFor(() => expect(viewer).toHaveStyle({ filter: 'brightness(130%) contrast(100%)' }));
  });

  it('con la IA caída muestra el banner de Modo Manual', async () => {
    setDegradedMode(true);
    renderPage();
    await screen.findByTestId('karyotype-viewer');
    expect(await screen.findByTestId('karyo-degraded-banner')).toHaveTextContent(/Modo Manual/i);
  });

  it('en modo degradado, una corrección manual queda marcada "degradado" en la bitácora', async () => {
    setDegradedMode(true);
    const user = userEvent.setup();
    renderPage();
    await screen.findByTestId('karyotype-viewer');
    await screen.findByTestId('karyo-degraded-banner'); // asegura clinicMode='degradado'

    await user.click(screen.getByTestId(`chromosome-${SAMPLE}-chr-18-0`));
    await screen.findByTestId('chromosome-props');
    await user.selectOptions(screen.getByTestId('reclassify-select'), '7');

    await user.click(screen.getByTestId('toggle-audit'));
    const log = await screen.findByTestId('audit-log');
    await waitFor(() => expect(within(log).getByTestId('audit-mode-degradado')).toBeInTheDocument());
  });
});
