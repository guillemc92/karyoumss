import { describe, expect, it } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { Route, Routes } from 'react-router-dom';
import { KaryotypePage } from '../../src/clinic/pages/KaryotypePage';
import { server } from '../../src/clinic/msw/server';
import { buildMockKaryotype } from '../../src/clinic/msw/karyotypeSeed';
import { renderWithProviders } from '../testUtils';

const READY_SAMPLE = '00000000-0000-0000-0000-000000000442';       // tiene cariotipo
const PROCESSING_SAMPLE = '00000000-0000-0000-0000-000000000441';  // NO_KARYOTYPE

function renderPage(id: string) {
  return renderWithProviders(
    <Routes>
      <Route path="/clinic/samples/:id/karyotype" element={<KaryotypePage />} />
    </Routes>,
    { route: `/clinic/samples/${id}/karyotype` },
  );
}

describe('KaryotypePage', () => {
  it('muestra skeleton mientras carga', () => {
    renderPage(READY_SAMPLE);
    expect(screen.getByLabelText('Cargando')).toBeInTheDocument();
  });

  it('renderiza el visor con 46 cromosomas y la leyenda', async () => {
    renderPage(READY_SAMPLE);
    await waitFor(() => expect(screen.getByTestId('karyotype-viewer')).toBeInTheDocument());
    expect(screen.getByTestId('semaphore-legend')).toBeInTheDocument();
    // 46 cromosomas renderizados
    const grid = screen.getByTestId('karyotype-viewer');
    expect(grid.querySelectorAll('button').length).toBe(46);
  });

  it('muestra el banner de revisión con la cuenta de naranjas', async () => {
    renderPage(READY_SAMPLE);
    await waitFor(() =>
      expect(screen.getByTestId('karyo-review-banner')).toHaveTextContent(/3 cromosoma/),
    );
  });

  it('seleccionar un cromosoma muestra sus propiedades', async () => {
    renderPage(READY_SAMPLE);
    await waitFor(() => expect(screen.getByTestId('karyotype-viewer')).toBeInTheDocument());
    // Panel vacío al inicio
    expect(screen.getByTestId('chromosome-props-empty')).toBeInTheDocument();

    const orange = screen.getByTestId(`chromosome-${READY_SAMPLE}-chr-18-0`);
    await userEvent.click(orange);

    expect(await screen.findByTestId('chromosome-props')).toBeInTheDocument();
    expect(screen.getByTestId('props-class')).toHaveTextContent('18');
    expect(screen.getByTestId('props-confidence')).toHaveTextContent('72%');
    expect(screen.getByTestId('props-semaphore')).toHaveTextContent(/revisión/i);
  });

  it('muestra_mensaje NO_KARYOTYPE para muestra sin cariotipo', async () => {
    renderPage(PROCESSING_SAMPLE);
    await waitFor(() =>
      expect(screen.getByTestId('karyo-error')).toHaveTextContent(/aún no tiene un cariotipo/i),
    );
  });

  it('muestra banner rojo cuando hay cromosomas con clasificación fallida', async () => {
    server.use(
      http.get('/api/clinic/samples/:id/karyotype/', ({ params }) => {
        const k = buildMockKaryotype(String(params.id));
        k.chromosomes[0].confidence_score = null;
        k.chromosomes[0].semaphore = 'red';
        k.summary.red = 1;
        return HttpResponse.json(k);
      }),
    );
    renderPage(READY_SAMPLE);
    await waitFor(() =>
      expect(screen.getByTestId('karyo-red-banner')).toHaveTextContent(/clasificación fallida/i),
    );
  });

  it('error genérico (no NO_KARYOTYPE) muestra mensaje de fallo de carga', async () => {
    server.use(
      http.get('/api/clinic/samples/:id/karyotype/', () =>
        HttpResponse.json({ code: 'SERVER_ERROR', detail: 'boom' }, { status: 500 }),
      ),
    );
    renderPage(READY_SAMPLE);
    await waitFor(() =>
      expect(screen.getByTestId('karyo-error')).toHaveTextContent(/no se pudo cargar/i),
    );
  });
});
