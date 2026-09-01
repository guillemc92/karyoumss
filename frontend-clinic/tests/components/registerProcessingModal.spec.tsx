import { describe, expect, it, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { RegisterProcessingModal } from '../../src/clinic/components/RegisterProcessingModal';
import { renderWithProviders } from '../testUtils';

const READY_SAMPLE_ID = '00000000-0000-0000-0000-000000000442';
const PROCESSING_SAMPLE_ID = '00000000-0000-0000-0000-000000000441';

describe('RegisterProcessingModal', () => {
  it('nombra el pipeline REAL, no un modelo que no se construyó', () => {
    renderWithProviders(<RegisterProcessingModal sampleId={READY_SAMPLE_ID} degraded={false} onComplete={vi.fn()} />);
    expect(screen.getByText('Procesando con Biomed IA')).toBeInTheDocument();
    expect(screen.getByText(/OpenCV \+ watershed/)).toBeInTheDocument();
    expect(screen.getByText(/EfficientNet-B3/)).toBeInTheDocument();
    // U-Net es diseño (ADR-0007), no implementación: la pantalla no puede
    // afirmarlo. Mask R-CNN además viola AGENTS §11.
    expect(screen.queryByText(/U-Net/)).not.toBeInTheDocument();
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

  // --- fase "en vuelo": el POST /register/ todavía no ha vuelto -------------
  // Es la fase que antes no existía: la barra solo se montaba DESPUÉS del POST,
  // cuando la muestra ya estaba READY, así que nunca se veía trabajar.

  it('sin sampleId muestra la barra y el tiempo transcurrido, no un porcentaje del servidor', () => {
    renderWithProviders(<RegisterProcessingModal sampleId={null} degraded={false} onComplete={vi.fn()} />);
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
    expect(screen.getByText(/Analizando las metafases/)).toBeInTheDocument();
    expect(screen.getByText(/suele tardar unos 32 s/)).toBeInTheDocument();
    expect(screen.queryByText(/Procesando\.\.\./)).not.toBeInTheDocument();
  });

  it('sin sampleId avisa de no cerrar y no marca ningún paso como completado', () => {
    const { container } = renderWithProviders(
      <RegisterProcessingModal sampleId={null} degraded={false} onComplete={vi.fn()} />,
    );
    expect(screen.getByText(/No cierres esta ventana/)).toBeInTheDocument();
    expect(container.querySelectorAll('.ai-step.active')).toHaveLength(0);
  });

  it('sin sampleId no llama a onComplete: todavía no hay nada que abrir', async () => {
    const onComplete = vi.fn();
    renderWithProviders(<RegisterProcessingModal sampleId={null} degraded={false} onComplete={onComplete} />);
    await new Promise((r) => setTimeout(r, 1200));
    expect(onComplete).not.toHaveBeenCalled();
  });

  it('la barra arranca en 0% y nunca miente con un 100% en vuelo', () => {
    renderWithProviders(<RegisterProcessingModal sampleId={null} degraded={false} onComplete={vi.fn()} />);
    const barra = screen.getByRole('progressbar');
    expect(barra).toHaveAttribute('aria-valuenow', '0');
    expect(Number(barra.getAttribute('aria-valuenow'))).toBeLessThan(100);
  });
});
