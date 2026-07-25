import { describe, expect, it } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { Route, Routes } from 'react-router-dom';
import { KaryotypePage } from '../../src/clinic/pages/KaryotypePage';
import { setSampleStatus } from '../../src/clinic/msw/handlers';
import { renderWithProviders } from '../testUtils';

const SAMPLE = '00000000-0000-0000-0000-000000000442';

function renderPage(opts: { asSupervisor?: boolean } = {}) {
  return renderWithProviders(
    <Routes>
      <Route path="/clinic/samples/:id/karyotype" element={<KaryotypePage />} />
    </Routes>,
    { route: `/clinic/samples/${SAMPLE}/karyotype`, ...opts },
  );
}

describe('KaryotypePage — Supervisor S1 (gating del panel de auditoría)', () => {
  it('supervisor sobre caso ANALYST_VALIDATED ve el panel de auditoría 5%', async () => {
    setSampleStatus(SAMPLE, 'ANALYST_VALIDATED');
    renderPage({ asSupervisor: true });
    await screen.findByTestId('karyotype-viewer');
    await waitFor(() => expect(screen.getByTestId('audit-panel')).toBeInTheDocument(), { timeout: 5000 });
    await waitFor(
      () => expect(screen.getByTestId('audit-progress')).toHaveTextContent('/3'),
      { timeout: 5000 },
    );
  });

  it('analista NO ve el panel de auditoría (segregación de funciones)', async () => {
    setSampleStatus(SAMPLE, 'ANALYST_VALIDATED');
    renderPage(); // rol analista por defecto
    await screen.findByTestId('karyotype-viewer');
    expect(screen.queryByTestId('audit-panel')).not.toBeInTheDocument();
  });

  it('supervisor sobre caso READY (aún no validado) no ve el panel', async () => {
    renderPage({ asSupervisor: true }); // SAMPLE arranca READY
    await screen.findByTestId('karyotype-viewer');
    expect(screen.queryByTestId('audit-panel')).not.toBeInTheDocument();
  });

  it('supervisor sobre caso SIGNED ve el banner de reporte firmado (S2)', async () => {
    setSampleStatus(SAMPLE, 'SIGNED');
    renderPage({ asSupervisor: true });
    await screen.findByTestId('karyotype-viewer');
    await waitFor(() => expect(screen.getByTestId('audit-panel')).toBeInTheDocument(), { timeout: 5000 });
    expect(await screen.findByTestId('report-signed-banner')).toBeInTheDocument();
    expect(screen.queryByTestId('btn-sign-report')).not.toBeInTheDocument();
  });
});
