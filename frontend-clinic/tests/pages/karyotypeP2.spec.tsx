import { describe, expect, it } from 'vitest';
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { Route, Routes } from 'react-router-dom';
import { KaryotypePage } from '../../src/clinic/pages/KaryotypePage';
import { server } from '../../src/clinic/msw/server';
import { renderWithProviders } from '../testUtils';

const SAMPLE = '00000000-0000-0000-0000-000000000442'; // READY, cariotipo con 3 naranjas (18/5/13)
const ORANGES = [`${SAMPLE}-chr-18-0`, `${SAMPLE}-chr-5-0`, `${SAMPLE}-chr-13-0`];

function renderPage() {
  return renderWithProviders(
    <Routes>
      <Route path="/clinic/samples/:id/karyotype" element={<KaryotypePage />} />
    </Routes>,
    { route: `/clinic/samples/${SAMPLE}/karyotype` },
  );
}

async function selectChromosome(user: ReturnType<typeof userEvent.setup>, id: string) {
  await user.click(screen.getByTestId(`chromosome-${id}`));
  await screen.findByTestId('chromosome-props');
}

describe('KaryotypePage — P2 (XAI + resolución + gating + audit)', () => {
  it('seleccionar un naranja muestra acciones; Aceptar deshabilitado hasta ver XAI', async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByTestId('karyotype-viewer');
    await selectChromosome(user, ORANGES[0]);

    expect(screen.getByTestId('action-xai')).toBeInTheDocument();
    expect(screen.getByTestId('action-resolve')).toBeDisabled();
    expect(screen.getByTestId('xai-required-hint')).toBeInTheDocument();
  });

  it('ver XAI abre el modal con heatmap y habilita Aceptar', async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByTestId('karyotype-viewer');
    await selectChromosome(user, ORANGES[0]);

    await user.click(screen.getByTestId('action-xai'));
    expect(await screen.findByTestId('xai-modal')).toBeInTheDocument();
    expect(await screen.findByTestId('xai-heatmap')).toBeInTheDocument();
    await user.click(screen.getByTestId('xai-close'));

    await waitFor(() => expect(screen.getByTestId('action-resolve')).toBeEnabled());
  });

  it('resolver un naranja baja la cuenta de revisión', async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByTestId('karyotype-viewer');
    await waitFor(() => expect(screen.getByTestId('karyo-review-banner')).toHaveTextContent(/3 cromosoma/));

    await selectChromosome(user, ORANGES[0]);
    await user.click(screen.getByTestId('action-xai'));
    await screen.findByTestId('xai-heatmap');
    await user.click(screen.getByTestId('xai-close'));
    await waitFor(() => expect(screen.getByTestId('action-resolve')).toBeEnabled());
    await user.click(screen.getByTestId('action-resolve'));

    await waitFor(() => expect(screen.getByTestId('karyo-review-banner')).toHaveTextContent(/2 cromosoma/));
  });

  it('botón Pasar a Supervisor bloqueado hasta resolver todos los naranjas', async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByTestId('karyotype-viewer');
    expect(screen.getByTestId('btn-pass-supervisor')).toBeDisabled();

    for (const id of ORANGES) {
      await selectChromosome(user, id);
      await user.click(screen.getByTestId('action-xai'));
      await screen.findByTestId('xai-heatmap');
      await user.click(screen.getByTestId('xai-close'));
      await waitFor(() => expect(screen.getByTestId('action-resolve')).toBeEnabled());
      await user.click(screen.getByTestId('action-resolve'));
    }

    await waitFor(() => expect(screen.getByTestId('btn-pass-supervisor')).toBeEnabled());
    await user.click(screen.getByTestId('btn-pass-supervisor'));
    expect(await screen.findByTestId('karyo-validated-banner')).toBeInTheDocument();
  });

  it('marcar anomalía refleja el estado en el panel', async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByTestId('karyotype-viewer');
    await selectChromosome(user, ORANGES[0]);

    await user.click(screen.getByTestId('action-anomaly'));
    await waitFor(() => expect(screen.getByTestId('props-semaphore')).toHaveTextContent(/Anomalía/));
  });

  it('si el XAI falla, el modal muestra el error', async () => {
    server.use(
      http.post('/api/clinic/samples/:id/chromosomes/:cid/xai/', () =>
        HttpResponse.json({ code: 'SERVER_ERROR', detail: 'Servicio XAI caído' }, { status: 500 }),
      ),
    );
    const user = userEvent.setup();
    renderPage();
    await screen.findByTestId('karyotype-viewer');
    await selectChromosome(user, ORANGES[0]);
    await user.click(screen.getByTestId('action-xai'));
    expect(await screen.findByTestId('xai-error')).toBeInTheDocument();
  });

  it('la bitácora de auditoría registra las acciones', async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByTestId('karyotype-viewer');
    await selectChromosome(user, ORANGES[0]);
    await user.click(screen.getByTestId('action-xai'));
    await screen.findByTestId('xai-heatmap');
    await user.click(screen.getByTestId('xai-close'));

    await user.click(screen.getByTestId('toggle-audit'));
    const log = await screen.findByTestId('audit-log');
    await waitFor(() => expect(within(log).getByText(/Consultó explicabilidad/)).toBeInTheDocument());
  });
});
