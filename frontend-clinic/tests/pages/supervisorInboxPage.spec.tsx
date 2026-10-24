import { beforeEach, describe, expect, it, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SupervisorInboxPage } from '../../src/clinic/pages/SupervisorInboxPage';
import { setSampleStatus } from '../../src/clinic/msw/handlers';
import { renderWithProviders } from '../testUtils';

// `renderWithProviders` monta un MemoryRouter: la navegación no toca
// window.location, así que se observa el destino a través de useNavigate.
const navigateMock = vi.fn();
vi.mock('react-router-dom', async () => {
  const real = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return { ...real, useNavigate: () => navigateMock };
});

const VALIDADO = '00000000-0000-0000-0000-000000000442';
const FIRMADO = '00000000-0000-0000-0000-000000000441';
const REPORTADO = '00000000-0000-0000-0000-000000000440';

/** Deja un caso en cada etapa del flujo del Supervisor. */
function conCasosEnCadaEtapa() {
  setSampleStatus(VALIDADO, 'ANALYST_VALIDATED');
  setSampleStatus(FIRMADO, 'SIGNED');
  setSampleStatus(REPORTADO, 'REPORTED');
}

describe('SupervisorInboxPage', () => {
  beforeEach(() => navigateMock.mockClear());

  describe('agrupación por etapa del flujo', () => {
    it('muestra las tres etapas del Supervisor', async () => {
      renderWithProviders(<SupervisorInboxPage />, { asSupervisor: true, route: '/clinic/supervisor' });

      await screen.findByTestId('inbox-stage-ANALYST_VALIDATED');
      expect(screen.getByTestId('inbox-stage-SIGNED')).toBeInTheDocument();
      expect(screen.getByTestId('inbox-stage-REPORTED')).toBeInTheDocument();
    });

    it('coloca cada caso en la etapa que le corresponde', async () => {
      conCasosEnCadaEtapa();
      renderWithProviders(<SupervisorInboxPage />, { asSupervisor: true, route: '/clinic/supervisor' });

      await waitFor(() => expect(screen.getByTestId(`inbox-row-${VALIDADO}`)).toBeInTheDocument());

      const validados = screen.getByTestId('inbox-stage-ANALYST_VALIDATED');
      const firmados = screen.getByTestId('inbox-stage-SIGNED');
      expect(validados).toContainElement(screen.getByTestId(`inbox-row-${VALIDADO}`));
      expect(firmados).toContainElement(screen.getByTestId(`inbox-row-${FIRMADO}`));
    });

    it('cuenta los casos por etapa', async () => {
      conCasosEnCadaEtapa();
      renderWithProviders(<SupervisorInboxPage />, { asSupervisor: true, route: '/clinic/supervisor' });

      await waitFor(() =>
        expect(screen.getByTestId('inbox-count-ANALYST_VALIDATED')).toHaveTextContent('1'));
      expect(screen.getByTestId('inbox-count-SIGNED')).toHaveTextContent('1');
    });

    it('resume cuántos casos esperan acción (validados + firmados)', async () => {
      conCasosEnCadaEtapa();
      renderWithProviders(<SupervisorInboxPage />, { asSupervisor: true, route: '/clinic/supervisor' });

      // Los REPORTED están cerrados: no cuentan como trabajo pendiente.
      await waitFor(() =>
        expect(screen.getByTestId('inbox-total-pending')).toHaveTextContent('2 caso(s)'));
    });

    it('una etapa sin casos lo dice, en vez de quedar vacía', async () => {
      setSampleStatus(VALIDADO, 'READY');
      setSampleStatus(FIRMADO, 'READY');
      setSampleStatus(REPORTADO, 'READY');
      renderWithProviders(<SupervisorInboxPage />, { asSupervisor: true, route: '/clinic/supervisor' });

      await waitFor(() =>
        expect(screen.getByTestId('inbox-empty-ANALYST_VALIDATED')).toBeInTheDocument());
    });
  });

  describe('acción por etapa', () => {
    it('la acción ofrecida depende del estado del caso', async () => {
      conCasosEnCadaEtapa();
      renderWithProviders(<SupervisorInboxPage />, { asSupervisor: true, route: '/clinic/supervisor' });

      await waitFor(() => expect(screen.getByTestId(`inbox-open-${VALIDADO}`)).toBeInTheDocument());
      expect(screen.getByTestId(`inbox-open-${VALIDADO}`)).toHaveTextContent('Auditar y firmar');
      expect(screen.getByTestId(`inbox-open-${FIRMADO}`)).toHaveTextContent('Generar ISCN');
      expect(screen.getByTestId(`inbox-open-${REPORTADO}`)).toHaveTextContent('Ver caso');
    });

    it('abrir un caso lleva al visor, donde vive el gating real', async () => {
      conCasosEnCadaEtapa();
      const user = userEvent.setup();
      renderWithProviders(<SupervisorInboxPage />, { asSupervisor: true, route: '/clinic/supervisor' });

      await waitFor(() => expect(screen.getByTestId(`inbox-open-${VALIDADO}`)).toBeInTheDocument());
      await user.click(screen.getByTestId(`inbox-open-${VALIDADO}`));

      expect(navigateMock).toHaveBeenCalledWith(`/clinic/samples/${VALIDADO}/karyotype`);
    });
  });

  describe('segregación de roles (RN-06)', () => {
    it('el analista no ve la bandeja', async () => {
      renderWithProviders(<SupervisorInboxPage />, { route: '/clinic/supervisor' });

      await waitFor(() => expect(screen.getByTestId('inbox-forbidden')).toBeInTheDocument());
      expect(screen.queryByTestId('inbox-stage-SIGNED')).not.toBeInTheDocument();
    });

    it('el admin sí la ve', async () => {
      renderWithProviders(<SupervisorInboxPage />, { asAdmin: true, route: '/clinic/supervisor' });

      await screen.findByTestId('inbox-stage-SIGNED');
      expect(screen.queryByTestId('inbox-forbidden')).not.toBeInTheDocument();
    });
  });
});
