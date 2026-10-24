import { describe, expect, it } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ProcessButton } from '../../src/clinic/components/ProcessButton';
import { renderWithProviders } from '../testUtils';
import { setDegradedMode } from '../../src/clinic/msw/handlers';

describe('ProcessButton', () => {
  it('renderiza habilitado cuando status es READY', () => {
    renderWithProviders(<ProcessButton sampleId="1" status="READY" />);
    expect(screen.getByText('▶ Procesar')).toBeEnabled();
  });

  it('deshabilitado cuando status es PROCESSING', () => {
    renderWithProviders(<ProcessButton sampleId="1" status="PROCESSING" />);
    expect(screen.getByText('Procesando...')).toBeDisabled();
  });

  it('deshabilitado cuando status es VALIDATED', () => {
    renderWithProviders(<ProcessButton sampleId="1" status="VALIDATED" />);
    expect(screen.getByText('▶ Procesar')).toBeDisabled();
  });

  it('click encola el procesamiento sin lanzar error ni activar modo degradado', async () => {
    renderWithProviders(<ProcessButton sampleId="00000000-0000-0000-0000-000000000442" status="READY" />);
    await userEvent.click(screen.getByText('▶ Procesar'));
    await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument());
  });

  it('en modo degradado (503 ML_DEGRADED) muestra DegradedBanner', async () => {
    setDegradedMode(true);
    renderWithProviders(<ProcessButton sampleId="00000000-0000-0000-0000-000000000442" status="READY" />);
    await userEvent.click(screen.getByText('▶ Procesar'));
    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument());
    setDegradedMode(false);
  });

  it('click en Reintentar del DegradedBanner limpia el estado y reintenta', async () => {
    setDegradedMode(true);
    renderWithProviders(<ProcessButton sampleId="00000000-0000-0000-0000-000000000442" status="READY" />);
    await userEvent.click(screen.getByText('▶ Procesar'));
    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument());
    setDegradedMode(false);
    await userEvent.click(screen.getByText('↻ Reintentar'));
    await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument());
  });

});
