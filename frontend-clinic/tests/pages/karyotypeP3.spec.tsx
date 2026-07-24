import { describe, expect, it } from 'vitest';
import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Route, Routes } from 'react-router-dom';
import { KaryotypePage } from '../../src/clinic/pages/KaryotypePage';
import { renderWithProviders } from '../testUtils';
import { PAD } from '../../src/clinic/lib/karyoLayout';

const SAMPLE = '00000000-0000-0000-0000-000000000442'; // READY, 46 cromosomas, 3 naranjas (18/5/13)

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

function setDrop(x: number, y: number) {
  (globalThis as unknown as { __konvaDrop?: { x: number; y: number } }).__konvaDrop = { x, y };
}

describe('KaryotypePage — P3 (corrección manual sobre Konva)', () => {
  it('reclasificar con "Mover a par" resuelve el naranja y baja la cuenta de revisión', async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByTestId('karyotype-viewer');
    await waitFor(() => expect(screen.getByTestId('karyo-review-banner')).toHaveTextContent(/3 cromosoma/));

    await selectChromosome(user, `${SAMPLE}-chr-18-0`);
    await user.selectOptions(screen.getByTestId('reclassify-select'), '7');

    await waitFor(() => expect(screen.getByTestId('karyo-review-banner')).toHaveTextContent(/2 cromosoma/));
  });

  it('reclasificar por drag & drop a otro par resuelve el naranja', async () => {
    renderPage();
    await screen.findByTestId('karyotype-viewer');
    await waitFor(() => expect(screen.getByTestId('karyo-review-banner')).toHaveTextContent(/3 cromosoma/));

    // Arrastrar el naranja 18 al slot 1 (columna 0, fila 0).
    setDrop(PAD + 10, PAD + 10);
    fireEvent(screen.getByTestId(`chromosome-${SAMPLE}-chr-18-0`), new CustomEvent('konvadragend'));

    await waitFor(() => expect(screen.getByTestId('karyo-review-banner')).toHaveTextContent(/2 cromosoma/));
  });

  it('separar (touching) agrega un cromosoma al visor', async () => {
    const user = userEvent.setup();
    renderPage();
    const viewer = await screen.findByTestId('karyotype-viewer');
    await waitFor(() => expect(viewer.querySelectorAll('button').length).toBe(46));

    await selectChromosome(user, `${SAMPLE}-chr-1-0`);
    await user.click(screen.getByTestId('action-split'));

    await waitFor(() => expect(viewer.querySelectorAll('button').length).toBe(47));
  });

  it('unir dos fragmentos deja uno inactivo (desaparece del visor)', async () => {
    const user = userEvent.setup();
    renderPage();
    const viewer = await screen.findByTestId('karyotype-viewer');
    await waitFor(() => expect(viewer.querySelectorAll('button').length).toBe(46));

    // Marcar la copia 0 del par 1 y unir la copia 1 en ella.
    await selectChromosome(user, `${SAMPLE}-chr-1-0`);
    await user.click(screen.getByTestId('action-join-pick'));
    await selectChromosome(user, `${SAMPLE}-chr-1-1`);
    await user.click(screen.getByTestId('action-join-confirm'));

    await waitFor(() => expect(viewer.querySelectorAll('button').length).toBe(45));
    expect(screen.queryByTestId(`chromosome-${SAMPLE}-chr-1-1`)).not.toBeInTheDocument();
  });

  it('resolver cruce marca el naranja como resuelto (baja la cuenta)', async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByTestId('karyotype-viewer');
    await waitFor(() => expect(screen.getByTestId('karyo-review-banner')).toHaveTextContent(/3 cromosoma/));

    await selectChromosome(user, `${SAMPLE}-chr-5-0`);
    await user.click(screen.getByTestId('action-cross'));

    await waitFor(() => expect(screen.getByTestId('karyo-review-banner')).toHaveTextContent(/2 cromosoma/));
  });

  it('la bitácora registra la reclasificación (CORRECT_CLASS)', async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByTestId('karyotype-viewer');
    await selectChromosome(user, `${SAMPLE}-chr-13-0`);
    await user.selectOptions(screen.getByTestId('reclassify-select'), '9');

    await user.click(screen.getByTestId('toggle-audit'));
    const log = await screen.findByTestId('audit-log');
    await waitFor(() => expect(within(log).getByText(/Corrigió clase/)).toBeInTheDocument());
  });
});
