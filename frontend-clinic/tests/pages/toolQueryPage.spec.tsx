import { afterEach, describe, expect, it } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ToolQueryPage } from '../../src/clinic/pages/ToolQueryPage';
import { setIaHabilitada } from '../../src/clinic/msw/handlers';
import { renderWithProviders } from '../testUtils';

/**
 * Los cuatro escenarios de la consigna, ahora desde la UI.
 *
 * Lo que se verifica no es solo que responda: es que **en pantalla se vea qué
 * herramienta se usó y de qué tabla salió el dato**. Sin esa evidencia visible,
 * la demostración no prueba nada.
 */

const CONTROLADA = '¿Qué cromosomas están naranjas?';
const SINONIMO = '¿Cuáles necesitan que el analista los mire de nuevo?';
const FUERA = '¿Cuál es el presupuesto del laboratorio para 2027?';

afterEach(() => setIaHabilitada(true));

async function preguntar(texto: string) {
  const user = userEvent.setup();
  renderWithProviders(<ToolQueryPage />, { route: '/clinic/consultas' });
  await user.type(screen.getByTestId('tool-input'), texto);
  await user.click(screen.getByTestId('tool-submit'));
  return user;
}

describe('ToolQueryPage — escenario 1: controlado', () => {
  it('resuelve sin modelo y lo dice en pantalla', async () => {
    await preguntar(CONTROLADA);

    await waitFor(() => expect(screen.getByTestId('tool-camino')).toBeInTheDocument());
    expect(screen.getByTestId('tool-camino')).toHaveTextContent('Sin IA');
  });

  it('muestra la herramienta y la tabla de origen', async () => {
    await preguntar(CONTROLADA);

    await waitFor(() => expect(screen.getByTestId('tool-nombre')).toBeInTheDocument());
    expect(screen.getByTestId('tool-nombre')).toHaveTextContent('CROMOSOMAS_PARA_REVISION');
    expect(screen.getByTestId('tool-fuente')).toHaveTextContent('clinic_chromosomes');
  });

  it('renderiza los datos como tabla', async () => {
    await preguntar(CONTROLADA);

    await waitFor(() => expect(screen.getByTestId('tool-tabla')).toBeInTheDocument());
    expect(screen.getAllByTestId('tool-fila')).toHaveLength(3);
  });
});

describe('ToolQueryPage — escenario 2: sinónimo', () => {
  it('el modelo elige la herramienta y se marca el camino LLM', async () => {
    await preguntar(SINONIMO);

    await waitFor(() => expect(screen.getByTestId('tool-camino')).toBeInTheDocument());
    expect(screen.getByTestId('tool-camino')).toHaveTextContent('modelo eligió');
    expect(screen.getByTestId('tool-nombre')).toHaveTextContent('CROMOSOMAS_PARA_REVISION');
  });

  it('expone por qué el modelo eligió esa herramienta', async () => {
    await preguntar(SINONIMO);

    await waitFor(() => expect(screen.getByTestId('tool-motivo')).toBeInTheDocument());
    expect(screen.getByTestId('tool-motivo')).toHaveTextContent(/revision manual/i);
  });

  it('devuelve los mismos datos que el escenario 1', async () => {
    /* Si difirieran, el modelo habría influido en la RESPUESTA, no solo en la
       elección de herramienta — que es lo que la arquitectura prohíbe. */
    await preguntar(SINONIMO);

    await waitFor(() => expect(screen.getByTestId('tool-tabla')).toBeInTheDocument());
    expect(screen.getAllByTestId('tool-fila')).toHaveLength(3);
    expect(screen.getByTestId('tool-fuente')).toHaveTextContent('clinic_chromosomes');
  });
});

describe('ToolQueryPage — escenario 3: fuera de alcance', () => {
  it('dice que no sabe sin mostrar un error', async () => {
    await preguntar(FUERA);

    await waitFor(() => expect(screen.getByTestId('tool-camino')).toBeInTheDocument());
    expect(screen.getByTestId('tool-camino')).toHaveTextContent('Fuera de alcance');
    expect(screen.queryByTestId('tool-error')).not.toBeInTheDocument();
  });

  it('no inventa datos', async () => {
    await preguntar(FUERA);

    await waitFor(() => expect(screen.getByTestId('tool-mensaje')).toBeInTheDocument());
    expect(screen.queryByTestId('tool-tabla')).not.toBeInTheDocument();
  });

  it('publica qué SÍ puede responder', async () => {
    await preguntar(FUERA);

    await waitFor(() => expect(screen.getByTestId('tool-catalogo-fallback')).toBeInTheDocument());
    expect(screen.getByTestId('tool-catalogo-fallback')).toHaveTextContent('CROMOSOMAS_PARA_REVISION');
  });
});

describe('ToolQueryPage — escenario 4: modelo apagado', () => {
  it('los datos siguen saliendo correctos', async () => {
    setIaHabilitada(false);
    await preguntar(CONTROLADA);

    await waitFor(() => expect(screen.getByTestId('tool-tabla')).toBeInTheDocument());
    expect(screen.getByTestId('tool-camino')).toHaveTextContent('Sin IA');
    expect(screen.getByTestId('tool-nombre')).toHaveTextContent('CROMOSOMAS_PARA_REVISION');
    expect(screen.getAllByTestId('tool-fila')).toHaveLength(3);
  });

  it('el sinónimo deja de funcionar — eso es lo que aporta la IA', async () => {
    setIaHabilitada(false);
    await preguntar(SINONIMO);

    await waitFor(() => expect(screen.getByTestId('tool-camino')).toBeInTheDocument());
    expect(screen.getByTestId('tool-camino')).toHaveTextContent('Fuera de alcance');
    expect(screen.getByTestId('tool-mensaje')).toHaveTextContent(/desactivada/i);
  });
});

describe('ToolQueryPage — usabilidad', () => {
  it('publica el catálogo antes de preguntar', async () => {
    renderWithProviders(<ToolQueryPage />, { route: '/clinic/consultas' });

    await waitFor(() => expect(screen.getByTestId('tool-catalogo')).toBeInTheDocument());
    expect(screen.getByTestId('tool-catalogo')).toHaveTextContent('clinic_chromosomes');
  });

  it('los escenarios precargados disparan la consulta', async () => {
    const user = userEvent.setup();
    renderWithProviders(<ToolQueryPage />, { route: '/clinic/consultas' });

    await user.click(screen.getByTestId('tool-ejemplo-1'));

    await waitFor(() => expect(screen.getByTestId('tool-resultado')).toBeInTheDocument());
    expect(screen.getByTestId('tool-camino')).toHaveTextContent('Sin IA');
  });

  it('no consulta con el campo vacío', () => {
    renderWithProviders(<ToolQueryPage />, { route: '/clinic/consultas' });
    expect(screen.getByTestId('tool-submit')).toBeDisabled();
  });

  it('muestra la latencia de cada consulta', async () => {
    await preguntar(CONTROLADA);

    await waitFor(() => expect(screen.getByTestId('tool-latencia')).toBeInTheDocument());
    expect(screen.getByTestId('tool-latencia')).toHaveTextContent('ms');
  });
});
