/**
 * Descartar y añadir objetos desde el visor (DD-KARYO-007 T3), de punta a
 * punta contra el doble MSW.
 *
 * Lo que se fija:
 * - descartar saca el objeto de la metafase, del recuento y de la selección;
 * - añadir crea el cromosoma, lo deja seleccionado y aparece en el cariograma;
 * - sin IA y sin clase, el error del servidor se ve y no se añade nada; al
 *   elegir la clase, sí;
 * - en un caso validado no hay herramientas.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Route, Routes } from 'react-router-dom';
import { KaryotypePage } from '../../src/clinic/pages/KaryotypePage';
import { fallarAnadirSinClase, fijarBboxMock, setSampleStatus } from '../../src/clinic/msw/handlers';
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

beforeEach(() => {
  metafase.valor = { imagen: metafase.doble, estado: 'lista' };
  fijarBboxMock(SAMPLE, NARANJA, { x: 448, y: 35, w: 175, h: 73 });
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

function dibujarCaja() {
  const stage = screen.getByTestId('metafase-editor-stage');
  const fijar = (x: number, y: number) => {
    (globalThis as unknown as { __konvaPointer?: { x: number; y: number } }).__konvaPointer = { x, y };
  };
  fijar(600, 500);
  fireEvent.mouseDown(stage);
  fijar(630, 560);
  fireEvent.mouseMove(stage);
  fireEvent.mouseUp(stage);
}

describe('KaryotypePage — descartar y añadir (DD-KARYO-007 T3)', () => {
  it('descartar quita el objeto de la metafase, del recuento y de la selección', async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByTestId(`metafase-objeto-${NARANJA}`));
    await screen.findByTestId('chromosome-props');
    const antes = total();

    await user.click(screen.getByTestId('metafase-descartar'));
    await user.selectOptions(screen.getByTestId('metafase-motivo'), 'suciedad');
    await user.click(screen.getByTestId('metafase-confirmar'));

    await waitFor(() => expect(screen.queryByTestId(`metafase-objeto-${NARANJA}`)).toBeNull());
    expect(total()).toBe(antes - 1);
    expect(screen.getByTestId('chromosome-props-empty')).toBeInTheDocument();
    expect(screen.queryByTestId(`chromosome-${NARANJA}`)).toBeNull();   // tampoco en el cariograma

    await user.click(screen.getByTestId('toggle-audit'));
    expect(await screen.findByText(/Descartó un objeto/)).toBeInTheDocument();
  });

  it('añadir crea el cromosoma, lo selecciona y aparece en el cariograma', async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByTestId('metafase-editor');
    const antes = total();
    await user.click(screen.getByTestId('metafase-herramienta-anadir'));
    dibujarCaja();

    await waitFor(() => expect(total()).toBe(antes + 1));
    expect(screen.getByTestId('props-class')).toHaveTextContent('21');
    const nuevo = screen.getAllByTestId(/^metafase-objeto-.*-chr-nuevo-/);
    expect(nuevo).toHaveLength(1);
    expect(nuevo[0]).toHaveAttribute('data-seleccionado', 'true');
    expect(screen.getAllByTestId(/^chromosome-.*-chr-nuevo-/).length).toBeGreaterThan(0);
  });

  it('sin IA y sin clase se ve el motivo y no se añade; eligiendo la clase, sí', async () => {
    fallarAnadirSinClase(true);
    const user = userEvent.setup();
    renderPage();
    await screen.findByTestId('metafase-editor');
    const antes = total();
    await user.click(screen.getByTestId('metafase-herramienta-anadir'));
    dibujarCaja();

    expect(await screen.findByTestId('karyo-action-error')).toHaveTextContent('elija la clase');
    expect(total()).toBe(antes);

    await user.selectOptions(screen.getByTestId('metafase-anadir-clase'), 'Y');
    dibujarCaja();
    await waitFor(() => expect(total()).toBe(antes + 1));
    expect(screen.getByTestId('props-class')).toHaveTextContent('Y');
    expect(screen.queryByTestId('karyo-action-error')).toBeNull();
  });

  it('en un caso validado no hay herramientas de edición', async () => {
    setSampleStatus(SAMPLE, 'ANALYST_VALIDATED');
    renderPage();
    await screen.findByTestId('metafase-editor');
    expect(screen.queryByTestId('metafase-herramientas')).toBeNull();
  });
});
