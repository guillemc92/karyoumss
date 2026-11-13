import { describe, expect, it } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ProcessButton } from '../../src/clinic/components/ProcessButton';
import { renderWithProviders } from '../testUtils';
import { setBusyMode, setDegradedMode } from '../../src/clinic/msw/handlers';

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

  // DD-OBS-001 D8: motor ocupado (503 ML_BUSY) no es motor caído.
  describe('con el motor ocupado', () => {
    const ID = '00000000-0000-0000-0000-000000000442';

    it('avisa de que hay otro caso en curso, con los segundos del backend', async () => {
      setBusyMode(25);
      renderWithProviders(<ProcessButton sampleId={ID} status="READY" />);
      await userEvent.click(screen.getByText('▶ Procesar'));
      const aviso = await screen.findByRole('status');
      expect(aviso).toHaveTextContent('procesando otro caso');
      expect(aviso).toHaveTextContent('reintentar en 25 s');
    });

    it('no entra en modo degradado ni ofrece el modo manual', async () => {
      setBusyMode(25);
      renderWithProviders(<ProcessButton sampleId={ID} status="READY" />);
      await userEvent.click(screen.getByText('▶ Procesar'));
      await screen.findByRole('status');
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
      expect(screen.queryByText(/modo manual/i)).not.toBeInTheDocument();
    });

    it('Reintentar con el motor ya libre procesa y quita el aviso', async () => {
      setBusyMode(25);
      renderWithProviders(<ProcessButton sampleId={ID} status="READY" />);
      await userEvent.click(screen.getByText('▶ Procesar'));
      await screen.findByRole('status');
      setBusyMode(null);
      await userEvent.click(screen.getByText('↻ Reintentar'));
      await waitFor(() => expect(screen.queryByRole('status')).not.toBeInTheDocument());
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });

    it('Reintentar con el motor todavía ocupado vuelve a avisar', async () => {
      setBusyMode(25);
      renderWithProviders(<ProcessButton sampleId={ID} status="READY" />);
      await userEvent.click(screen.getByText('▶ Procesar'));
      await screen.findByRole('status');
      setBusyMode(7);
      await userEvent.click(screen.getByText('↻ Reintentar'));
      await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('reintentar en 7 s'));
    });

    it('Cerrar quita el aviso', async () => {
      setBusyMode(25);
      renderWithProviders(<ProcessButton sampleId={ID} status="READY" />);
      await userEvent.click(screen.getByText('▶ Procesar'));
      await screen.findByRole('status');
      await userEvent.click(screen.getByLabelText('Cerrar'));
      expect(screen.queryByRole('status')).not.toBeInTheDocument();
    });

    it('si el motor cae después, el aviso de ocupado deja paso al de degradado', async () => {
      setBusyMode(25);
      renderWithProviders(<ProcessButton sampleId={ID} status="READY" />);
      await userEvent.click(screen.getByText('▶ Procesar'));
      await screen.findByRole('status');
      setBusyMode(null);
      setDegradedMode(true);
      await userEvent.click(screen.getByText('▶ Procesar'));
      await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument());
      expect(screen.queryByRole('status')).not.toBeInTheDocument();
      setDegradedMode(false);
    });
  });

});
