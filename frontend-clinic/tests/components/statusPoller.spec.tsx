import { describe, expect, it } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { StatusPoller } from '../../src/clinic/components/StatusPoller';
import { renderWithProviders } from '../testUtils';

const PROCESSING_SAMPLE_ID = '00000000-0000-0000-0000-000000000441';

describe('StatusPoller', () => {
  it('renderiza el track de estados', () => {
    renderWithProviders(<StatusPoller sampleId="1" initialStatus="PENDING_AI" />);
    expect(screen.getByText('PENDING_AI')).toBeInTheDocument();
    expect(screen.getByText('PROCESSING')).toBeInTheDocument();
    expect(screen.getByText('READY')).toBeInTheDocument();
  });

  it('no hace polling si el estado inicial ya es terminal (READY)', () => {
    renderWithProviders(<StatusPoller sampleId="1" initialStatus="READY" />);
    expect(screen.queryByText(/Polling cada 2s/)).not.toBeInTheDocument();
  });

  it('no hace polling si el estado inicial es VALIDATED', () => {
    renderWithProviders(<StatusPoller sampleId="1" initialStatus="VALIDATED" />);
    expect(screen.queryByText(/Polling cada 2s/)).not.toBeInTheDocument();
  });

  it('con status inicial PROCESSING, hace polling y muestra el resultado con chromosome_count', async () => {
    renderWithProviders(<StatusPoller sampleId={PROCESSING_SAMPLE_ID} initialStatus="PROCESSING" />);
    await waitFor(() => expect(screen.getByText(/chromosomes:/)).toBeInTheDocument(), { timeout: 3000 });
  });
});
