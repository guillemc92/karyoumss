import { describe, expect, it, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { RegisterProcessingModal } from '../../src/clinic/components/RegisterProcessingModal';
import { renderWithProviders } from '../testUtils';

const READY_SAMPLE_ID = '00000000-0000-0000-0000-000000000442';
const PROCESSING_SAMPLE_ID = '00000000-0000-0000-0000-000000000441';

describe('RegisterProcessingModal', () => {
  it('renderiza el título y los 3 pasos con texto U-Net (no Mask R-CNN)', () => {
    renderWithProviders(<RegisterProcessingModal sampleId={READY_SAMPLE_ID} degraded={false} onComplete={vi.fn()} />);
    expect(screen.getByText('Procesando con Biomed IA')).toBeInTheDocument();
    expect(screen.getByText(/Segmentación de instancias \(U-Net\)/)).toBeInTheDocument();
    expect(screen.queryByText(/Mask R-CNN/)).not.toBeInTheDocument();
  });

  it('en modo degradado muestra DegradedBanner en vez de la barra de progreso', () => {
    renderWithProviders(<RegisterProcessingModal sampleId={READY_SAMPLE_ID} degraded={true} onComplete={vi.fn()} />);
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.queryByText(/Procesando\.\.\./)).not.toBeInTheDocument();
  });

  it('cuando el status llega a terminal, llama onComplete', async () => {
    const onComplete = vi.fn();
    renderWithProviders(<RegisterProcessingModal sampleId={READY_SAMPLE_ID} degraded={false} onComplete={onComplete} />);
    await waitFor(() => expect(onComplete).toHaveBeenCalled(), { timeout: 3000 });
  });

  it('con status PROCESSING inicial, hace polling hasta terminar', async () => {
    const onComplete = vi.fn();
    renderWithProviders(<RegisterProcessingModal sampleId={PROCESSING_SAMPLE_ID} degraded={false} onComplete={onComplete} />);
    await waitFor(() => expect(onComplete).toHaveBeenCalled(), { timeout: 3000 });
  });
});
