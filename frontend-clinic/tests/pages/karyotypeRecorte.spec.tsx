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
 *
 * Desde DD-KARYO-006 D7 el recorte se dibuja en el panel «Metafase», sobre la
 * imagen real, y se envía en píxeles de la metafase. Antes se dibujaba sobre el
 * cariograma y se enviaba la caja del hueco (`{x: 9, y: 18, w: 22, h: 100}`).
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Route, Routes } from 'react-router-dom';
import { KaryotypePage } from '../../src/clinic/pages/KaryotypePage';
import { fijarBboxMock } from '../../src/clinic/msw/handlers';
import { server } from '../../src/clinic/msw/server';
import { aPanel, escalaPanel, regionDeRecorte } from '../../src/clinic/lib/recorteMetafase';
import { renderWithProviders } from '../testUtils';

type EstadoMetafase = {
  imagen: HTMLImageElement | null;
  estado: 'cargando' | 'lista' | 'sin-imagen' | 'error';
};

// jsdom no decodifica imágenes: la metafase es un doble de 1024 × 768.
const metafase = vi.hoisted(() => ({
  doble: { width: 1024, height: 768, naturalWidth: 1024, naturalHeight: 768 },
  valor: null as unknown,
}));
vi.mock('../../src/clinic/hooks/useMetaphaseImage', () => ({
  useMetaphaseImage: () => metafase.valor,
}));
const LISTA: EstadoMetafase = { imagen: metafase.doble as HTMLImageElement, estado: 'lista' };

const SAMPLE = '00000000-0000-0000-0000-000000000442';
const NARANJA = `${SAMPLE}-chr-18-0`;
// El cromosoma con el que se reprodujo el defecto el 13/10.
const CAJA = { x: 448, y: 35, w: 175, h: 73 };

beforeEach(() => {
  metafase.valor = LISTA;
  fijarBboxMock(SAMPLE, NARANJA, CAJA);
});

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

/** Dibuja en el panel «Metafase» la mitad izquierda del cromosoma. */
function dibujarRecorte() {
  const region = regionDeRecorte(CAJA, { w: 1024, h: 768 });
  const p = aPanel(CAJA, region, escalaPanel(region));
  const stage = screen.getByTestId('metafase-stage');
  setPointer(p.x, p.y);
  fireEvent.mouseDown(stage);
  setPointer(p.x + p.w / 2, p.y + p.h);
  fireEvent.mouseMove(stage);
  fireEvent.mouseUp(stage);
}

async function seleccionar(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByTestId(`chromosome-${NARANJA}`));
  await screen.findByTestId('chromosome-props');
}

async function seleccionarYActivarRecorte(user: ReturnType<typeof userEvent.setup>) {
  await seleccionar(user);
  await user.click(screen.getByTestId('action-crop'));
}

describe('KaryotypePage — recorte manual', () => {
  it('se envía en píxeles de la metafase, dentro del cromosoma', async () => {
    // El defecto del 13/10, de punta a punta: lo que llega al servidor.
    const enviados: unknown[] = [];
    const escuchar = ({ request }: { request: Request }) => {
      if (request.url.includes('/recrop/')) {
        void request.clone().json().then((cuerpo) => enviados.push(cuerpo));
      }
    };
    server.events.on('request:start', escuchar);
    try {
      const user = userEvent.setup();
      renderPage();
      await screen.findByTestId('karyotype-viewer');
      await seleccionarYActivarRecorte(user);

      dibujarRecorte();

      await waitFor(() => expect(enviados).toHaveLength(1));
      const { bbox } = enviados[0] as { bbox: { x: number; y: number; w: number; h: number } };
      expect(bbox.x).toBe(CAJA.x);
      expect(bbox.y).toBe(CAJA.y);
      expect(Math.abs(bbox.w - CAJA.w / 2)).toBeLessThanOrEqual(1);
      expect(bbox.h).toBe(CAJA.h);
    } finally {
      server.events.removeListener('request:start', escuchar);
    }
  });

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

  it('el panel se cierra solo al soltar', async () => {
    // Quedarse recortando invitaría a recortar otra vez sin haber visto el
    // resultado del primero.
    const user = userEvent.setup();
    renderPage();
    await screen.findByTestId('karyotype-viewer');
    await seleccionarYActivarRecorte(user);
    expect(screen.getByTestId('metafase-panel')).toBeInTheDocument();
    expect(screen.getByTestId('crop-hint')).toBeInTheDocument();

    dibujarRecorte();

    await waitFor(() => expect(screen.queryByTestId('metafase-panel')).not.toBeInTheDocument());
    expect(screen.queryByTestId('crop-hint')).not.toBeInTheDocument();
  });

  it('Cancelar cierra el panel sin recortar', async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByTestId('karyotype-viewer');
    await seleccionarYActivarRecorte(user);

    await user.click(screen.getByTestId('metafase-cancelar'));

    expect(screen.queryByTestId('metafase-panel')).not.toBeInTheDocument();
    expect(screen.getByTestId('props-class')).toHaveTextContent('Par 18');
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
    const user = userEvent.setup();
    renderPage();
    await screen.findByTestId('karyotype-viewer');
    await seleccionarYActivarRecorte(user);

    await user.click(screen.getByTestId('medicion-toggle'));

    expect(screen.queryByTestId('metafase-panel')).not.toBeInTheDocument();
  });

  it('sin metafase no se ofrece recortar (RN-07)', async () => {
    // No hay imagen sobre la que dibujar: el botón no aparece.
    metafase.valor = { imagen: null, estado: 'sin-imagen' } satisfies EstadoMetafase;
    const user = userEvent.setup();
    renderPage();
    await screen.findByTestId('karyotype-viewer');
    await seleccionar(user);

    expect(screen.queryByTestId('action-crop')).not.toBeInTheDocument();
  });

  it('un cromosoma cuya caja se sale de la metafase no se puede recortar', async () => {
    fijarBboxMock(SAMPLE, NARANJA, { x: 1000, y: 700, w: 100, h: 100 });   // 1024 × 768
    const user = userEvent.setup();
    renderPage();
    await screen.findByTestId('karyotype-viewer');
    await seleccionar(user);

    expect(screen.queryByTestId('action-crop')).not.toBeInTheDocument();
  });
});
