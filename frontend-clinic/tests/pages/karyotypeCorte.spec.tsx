/**
 * Separar por línea y deshacer desde el visor (DD-KARYO-007 T6), de punta a
 * punta contra el doble MSW.
 *
 * - separar envía la línea, aparece el trozo nuevo y el original sigue
 *   seleccionado;
 * - «Deshacer» enseña la última edición y, al pulsarlo, el cariotipo vuelve a
 *   como estaba y la bitácora lo registra;
 * - sin backend-ml el motivo se ve y no cambia nada (RN-07).
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Route, Routes } from 'react-router-dom';
import { KaryotypePage } from '../../src/clinic/pages/KaryotypePage';
import { LIENZO_MAX } from '../../src/clinic/components/MetafaseEditor';
import { fallarSeparar, fijarBboxMock } from '../../src/clinic/msw/handlers';
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
const AJUSTE = Math.min(LIENZO_MAX.w / 1024, LIENZO_MAX.h / 768, 1);

beforeEach(() => {
  metafase.valor = { imagen: metafase.doble, estado: 'lista' };
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

const total = () => Number(/(\d+) cromosomas/.exec(screen.getByText(/cromosomas ·/).textContent ?? '')?.[1]);

/** Línea horizontal a la altura `y` de la metafase, de lado a lado de la caja. */
function trazarHorizontal(y: number) {
  const stage = screen.getByTestId('metafase-editor-stage');
  const fijar = (x: number, yy: number) => {
    (globalThis as unknown as { __konvaPointer?: { x: number; y: number } }).__konvaPointer = { x: x * AJUSTE, y: yy * AJUSTE };
  };
  fijar(CAJA.x - 10, y);
  fireEvent.mouseDown(stage);
  fijar(CAJA.x + CAJA.w / 2, y);
  fireEvent.mouseMove(stage);
  fijar(CAJA.x + CAJA.w + 10, y);
  fireEvent.mouseMove(stage);
  fireEvent.mouseUp(stage);
}

async function separarNaranja(user: ReturnType<typeof userEvent.setup>) {
  await user.click(await screen.findByTestId(`metafase-objeto-${NARANJA}`));
  await screen.findByTestId('chromosome-props');
  await user.click(screen.getByTestId('metafase-herramienta-cortar'));
  trazarHorizontal(CAJA.y + 30);
}

describe('KaryotypePage — separar y deshacer (DD-KARYO-007 T6)', () => {
  it('separar crea el trozo y el original sigue seleccionado', async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByTestId('metafase-editor');
    const antes = total();
    await separarNaranja(user);

    await waitFor(() => expect(total()).toBe(antes + 1));
    expect(screen.getByTestId(`metafase-objeto-${NARANJA}`)).toHaveAttribute('data-seleccionado', 'true');
    expect(screen.getByTestId('props-class')).toHaveTextContent('18');
  });

  it('deshacer enseña la edición y deja el cariotipo como estaba', async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByTestId('metafase-editor');
    const antes = total();
    expect(screen.getByTestId('metafase-deshacer')).toBeDisabled();
    await separarNaranja(user);
    await waitFor(() => expect(total()).toBe(antes + 1));

    const boton = await screen.findByText('Deshacer: Separó');
    await user.click(boton);

    await waitFor(() => expect(total()).toBe(antes));
    expect(screen.getByTestId('metafase-deshacer')).toHaveTextContent('Nada que deshacer');
    expect(screen.getByTestId('chromosome-props-empty')).toBeInTheDocument();
    await user.click(screen.getByTestId('toggle-audit'));
    expect(await screen.findByText(/Deshizo una edición/)).toBeInTheDocument();
  });

  it('sin backend-ml, separar dice por qué y no cambia nada', async () => {
    fallarSeparar(true);
    const user = userEvent.setup();
    renderPage();
    await screen.findByTestId('metafase-editor');
    const antes = total();
    await separarNaranja(user);
    expect(await screen.findByTestId('karyo-action-error')).toHaveTextContent('separar por línea no está disponible');
    expect(total()).toBe(antes);
  });

  it('una línea que el servidor rechaza muestra su motivo', async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByTestId('metafase-editor');
    await user.click(await screen.findByTestId(`metafase-objeto-${NARANJA}`));
    await user.click(screen.getByTestId('metafase-herramienta-cortar'));
    // La línea cruza el borde de la caja (el cliente la deja pasar), pero el
    // doble la rechaza porque su altura media queda fuera del objeto.
    const stage = screen.getByTestId('metafase-editor-stage');
    const fijar = (x: number, y: number) => {
      (globalThis as unknown as { __konvaPointer?: { x: number; y: number } }).__konvaPointer = { x: x * AJUSTE, y: y * AJUSTE };
    };
    fijar(CAJA.x + 20, CAJA.y - 200);
    fireEvent.mouseDown(stage);
    fijar(CAJA.x + 20, CAJA.y + 40);
    fireEvent.mouseMove(stage);
    fijar(CAJA.x + 60, CAJA.y - 200);
    fireEvent.mouseMove(stage);
    fireEvent.mouseUp(stage);
    expect(await screen.findByTestId('karyo-action-error')).toHaveTextContent('de borde a borde');
  });
});
