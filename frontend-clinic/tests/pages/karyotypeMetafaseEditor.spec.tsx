/**
 * Editor de metafase dentro del visor (DD-KARYO-007 T2), de punta a punta
 * contra el doble MSW.
 *
 * Lo que se fija aquí:
 * - la metafase y el cariograma comparten la selección, en los dos sentidos;
 * - un caso antiguo (solo cajas) pide las siluetas UNA vez al abrirse, y no en
 *   un caso validado;
 * - si backend-ml no puede calcularlas, se sigue viendo la caja y no se reintenta
 *   en bucle (RN-07).
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { Route, Routes } from 'react-router-dom';
import { KaryotypePage } from '../../src/clinic/pages/KaryotypePage';
import { fijarBboxMock, fijarContornoMock, setSampleStatus } from '../../src/clinic/msw/handlers';
import { server } from '../../src/clinic/msw/server';
import { renderWithProviders } from '../testUtils';

const metafase = vi.hoisted(() => ({
  doble: { width: 1024, height: 768, naturalWidth: 1024, naturalHeight: 768 },
  valor: null as unknown,
}));
vi.mock('../../src/clinic/hooks/useMetaphaseImage', () => ({
  useMetaphaseImage: () => metafase.valor,
}));

const SAMPLE = '00000000-0000-0000-0000-000000000442';
const NARANJA = `${SAMPLE}-chr-18-0`;
const CAJA = { x: 448, y: 35, w: 175, h: 73 };
const SILUETA = [[450, 40], [600, 50], [610, 100], [460, 90]];

let pedidas = 0;
const contar = ({ request }: { request: Request }) => {
  if (request.method === 'POST' && request.url.includes('/karyotype/contours/')) pedidas += 1;
};

beforeEach(() => {
  metafase.valor = { imagen: metafase.doble, estado: 'lista' };
  fijarBboxMock(SAMPLE, NARANJA, CAJA);
  pedidas = 0;
  server.events.on('request:start', contar);
});
afterEach(() => {
  server.events.removeListener('request:start', contar);
});

function renderPage() {
  return renderWithProviders(
    <Routes>
      <Route path="/clinic/samples/:id/karyotype" element={<KaryotypePage />} />
    </Routes>,
    { route: `/clinic/samples/${SAMPLE}/karyotype` },
  );
}

describe('KaryotypePage — editor de metafase (DD-KARYO-007 T2)', () => {
  it('la metafase es el primer lienzo y el cariograma sigue debajo', async () => {
    renderPage();
    const editor = await screen.findByTestId('metafase-editor');
    const cariograma = screen.getByTestId('karyotype-viewer');
    // DOCUMENT_POSITION_FOLLOWING: el cariograma va después del editor.
    expect(editor.compareDocumentPosition(cariograma) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('sin metafase no hay editor: se ve el aviso y el cariograma de cajas', async () => {
    metafase.valor = { imagen: null, estado: 'sin-imagen' };
    renderPage();
    await screen.findByTestId('karyotype-viewer');
    expect(screen.queryByTestId('metafase-editor')).toBeNull();
    expect(screen.getByTestId('metafase-aviso')).toBeInTheDocument();
  });

  it('seleccionar en la metafase selecciona el mismo cromosoma en el cariograma', async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByTestId(`metafase-objeto-${NARANJA}`));
    expect(await screen.findByTestId('chromosome-props')).toBeInTheDocument();
    // El panel de propiedades lee la misma selección que el cariograma.
    expect(screen.getByTestId('props-class')).toHaveTextContent('18');
  });

  it('seleccionar en el cariograma lo marca en la metafase', async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByTestId('metafase-editor');
    await user.click(screen.getByTestId(`chromosome-${NARANJA}`));
    await waitFor(() =>
      expect(screen.getByTestId(`metafase-objeto-${NARANJA}`)).toHaveAttribute('data-seleccionado', 'true'));
  });

  it('un caso antiguo pide las siluetas una vez y pasa a pintarlas', async () => {
    renderPage();
    const objeto = await screen.findByTestId(`metafase-objeto-${NARANJA}`);
    expect(objeto).toHaveAttribute('data-silueta', 'false');
    await waitFor(() =>
      expect(screen.getByTestId(`metafase-objeto-${NARANJA}`)).toHaveAttribute('data-silueta', 'true'));
    expect(pedidas).toBe(1);
  });

  it('si todas tienen silueta no se pide nada', async () => {
    renderPage();
    // Se deja que la primera carga complete las del seed y se cuenta desde ahí.
    await waitFor(() => expect(pedidas).toBe(1));
    fijarContornoMock(SAMPLE, NARANJA, SILUETA);
    pedidas = 0;
    renderPage();
    await screen.findAllByTestId(`metafase-objeto-${NARANJA}`);
    await new Promise((r) => setTimeout(r, 50));
    expect(pedidas).toBe(0);
  });

  it('en un caso validado no se piden (el servidor daría 409)', async () => {
    setSampleStatus(SAMPLE, 'ANALYST_VALIDATED');
    renderPage();
    await screen.findByTestId(`metafase-objeto-${NARANJA}`);
    await new Promise((r) => setTimeout(r, 50));
    expect(pedidas).toBe(0);
  });

  it('sin backend-ml se queda la caja y no se reintenta en cada recarga (RN-07)', async () => {
    server.use(
      http.post('*/samples/:id/karyotype/contours/', () =>
        HttpResponse.json({ code: 'ML_UNAVAILABLE', detail: 'backend-ml no responde' }, { status: 503 })),
    );
    const user = userEvent.setup();
    renderPage();
    await screen.findByTestId(`metafase-objeto-${NARANJA}`);
    await waitFor(() => expect(pedidas).toBe(1));
    // Una acción cualquiera recarga el cariotipo; no debe volver a pedirlas.
    await user.click(screen.getByTestId(`chromosome-${NARANJA}`));
    await user.click(screen.getByTestId('action-anomaly'));
    await waitFor(() => expect(screen.getByTestId(`chromosome-${NARANJA}`)).toBeInTheDocument());
    await new Promise((r) => setTimeout(r, 50));
    expect(pedidas).toBe(1);
    expect(screen.getByTestId(`metafase-objeto-${NARANJA}`)).toHaveAttribute('data-silueta', 'false');
    expect(screen.queryByTestId('karyo-action-error')).toBeNull();
  });
});
