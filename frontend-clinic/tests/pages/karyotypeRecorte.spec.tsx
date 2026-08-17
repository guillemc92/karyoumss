/**
 * Recorte manual del cromosoma, de punta a punta (visor → API → visor).
 *
 * ## Por qué existe esta herramienta
 *
 * La segmentación sub-segmenta: dos cromosomas solapados salen como una sola
 * detección. Ese recorte malo es el origen medido de las falsas «clase 1» —un
 * cúmulo es más grande que cualquier cromosoma, y la clase 1 es la más
 * grande—. Recortar a mano y volver a clasificar es la vía para arreglar
 * justamente esos casos sin esperar a un segmentador mejor.
 *
 * Lo que se fija aquí es la propiedad clínica que le da sentido: **el recorte
 * arrastra una clasificación nueva y reabre la revisión**. Si el recorte se
 * guardara sin reclasificar, la pantalla mostraría una clase calculada sobre
 * píxeles que ya nadie ve; y si el cromosoma siguiera «resuelto», se firmaría
 * una decisión tomada mirando otra cosa.
 */
import { describe, expect, it } from 'vitest';
import { fireEvent, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Route, Routes } from 'react-router-dom';
import { KaryotypePage } from '../../src/clinic/pages/KaryotypePage';
import { renderWithProviders } from '../testUtils';

const SAMPLE = '00000000-0000-0000-0000-000000000442';
const NARANJA = `${SAMPLE}-chr-18-0`;

function renderPage() {
  return renderWithProviders(
    <Routes>
      <Route path="/clinic/samples/:id/karyotype" element={<KaryotypePage />} />
    </Routes>,
    { route: `/clinic/samples/${SAMPLE}/karyotype` },
  );
}

function setPointer(x: number, y: number) {
  (globalThis as unknown as { __konvaPointer?: { x: number; y: number } }).__konvaPointer = { x, y };
}

/** Dibuja el rectángulo de recorte sobre el lienzo. */
function dibujarRecorte(desde: [number, number] = [40, 40], hasta: [number, number] = [90, 150]) {
  const stage = screen.getByTestId('karyo-stage');
  setPointer(...desde);
  fireEvent.mouseDown(stage);
  setPointer(...hasta);
  fireEvent.mouseMove(stage);
  fireEvent.mouseUp(stage);
}

async function seleccionarYActivarRecorte(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByTestId(`chromosome-${NARANJA}`));
  await screen.findByTestId('chromosome-props');
  await user.click(screen.getByTestId('action-crop'));
}

describe('KaryotypePage — recorte manual', () => {
  it('recortar cambia la clase del cromosoma', async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByTestId('karyotype-viewer');
    await seleccionarYActivarRecorte(user);
    expect(screen.getByTestId('props-class')).toHaveTextContent('Par 18');

    dibujarRecorte();

    await waitFor(() => expect(screen.getByTestId('props-class')).toHaveTextContent('Par 20'));
  });

  it('tras recortar hay que volver a mirar el XAI antes de aceptar (BR-004)', async () => {
    // La decisión anterior se tomó sobre píxeles distintos: no vale.
    const user = userEvent.setup();
    renderPage();
    await screen.findByTestId('karyotype-viewer');
    await seleccionarYActivarRecorte(user);

    dibujarRecorte();

    await waitFor(() => expect(screen.getByTestId('xai-required-hint')).toBeInTheDocument());
    expect(screen.getByTestId('action-resolve')).toBeDisabled();
  });

  it('el modo se apaga solo al soltar', async () => {
    // Quedarse en modo recorte invitaría a recortar otra vez sin haber visto
    // el resultado del primero.
    const user = userEvent.setup();
    renderPage();
    await screen.findByTestId('karyotype-viewer');
    await seleccionarYActivarRecorte(user);
    expect(screen.getByTestId('crop-hint')).toBeInTheDocument();

    dibujarRecorte();

    await waitFor(() => expect(screen.queryByTestId('crop-hint')).not.toBeInTheDocument());
  });

  it('queda registrado en la bitácora', async () => {
    // RN-05: toda corrección manual deja traza append-only.
    const user = userEvent.setup();
    renderPage();
    await screen.findByTestId('karyotype-viewer');
    await seleccionarYActivarRecorte(user);
    dibujarRecorte();
    await waitFor(() => expect(screen.getByTestId('props-class')).toHaveTextContent('Par 20'));

    await user.click(screen.getByTestId('toggle-audit'));

    await waitFor(() =>
      expect(screen.getByTestId('audit-log')).toHaveTextContent('Recortó y reclasificó'));
  });

  it('medir y recortar no se pisan', async () => {
    // Los dos gestos son un arrastre sobre el mismo lienzo.
    const user = userEvent.setup();
    renderPage();
    await screen.findByTestId('karyotype-viewer');
    await seleccionarYActivarRecorte(user);

    await user.click(screen.getByTestId('medicion-toggle'));

    expect(screen.queryByTestId('crop-hint')).not.toBeInTheDocument();
  });
});
