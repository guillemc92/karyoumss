/**
 * Tests de ModelsSection (DD-ADMIN-002 P3, ADR-0014).
 *
 * Verifica el cableado completo:
 *  - Loading inicial + render de config real (U-Net/EfficientNet-B3) y métricas.
 *  - Banner de cumplimiento cuando confidence_threshold < 0.85.
 *  - Sliders/selects hidratan desde el backend y hacen diff antes del PATCH.
 *  - Guardar sin cambios no llama al backend pero sí da feedback.
 *  - Restaurar valores por defecto revierte ediciones no guardadas.
 *  - Métricas: sparkline con ≥2 snapshots, estado vacío, error no bloquea el form.
 */
import { describe, expect, it } from 'vitest';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { ModelsSection } from '../../src/admin/components/ModelsSection';
import { server } from '../../src/admin/msw/server';

describe('ModelsSection — P3', () => {
  it('muestra loading inicial y luego el contenido con datos reales del MSW', async () => {
    render(<ModelsSection />);
    expect(screen.getByTestId('models-section-loading')).toBeInTheDocument();
    expect(await screen.findByTestId('models-section-content')).toBeInTheDocument();

    expect(screen.getByTestId('models-card-unet')).toHaveTextContent('U-Net (segmentación)');
    expect(screen.getByTestId('models-card-unet')).toHaveTextContent('u-net-v2.1');
    expect(screen.getByTestId('models-card-classifier')).toHaveTextContent('EfficientNet-B3 (clasificación)');
    expect(screen.getByTestId('models-card-classifier')).toHaveTextContent('efficientnet-b3-v1.4');

    expect(screen.getByTestId('models-input-confidence')).toHaveValue('85');
    expect(screen.getByTestId('models-input-analysis-mode')).toHaveValue('balanced');
    expect(screen.getByTestId('models-input-log-level')).toHaveValue('INFO');

    // No hay compliance_warning con el default (0.85)
    expect(screen.queryByTestId('models-compliance-banner')).not.toBeInTheDocument();
  });

  it('carga métricas reales: última métrica + sparkline con 3 snapshots', async () => {
    render(<ModelsSection />);
    await screen.findByTestId('models-section-content');

    expect(await screen.findByTestId('models-metric-precision')).toHaveTextContent('97.2%');
    expect(screen.getByTestId('models-metric-recall')).toHaveTextContent('96.8%');
    expect(screen.getByTestId('models-metric-f1')).toHaveTextContent('0.969');
    expect(screen.getByTestId('models-latency-p50')).toHaveTextContent('92 ms');
    expect(screen.getByTestId('models-sparkline')).toBeInTheDocument();
  });

  it('estado vacío de métricas cuando no hay snapshots', async () => {
    server.use(
      http.get('/api/admin/models/metrics/latest/', () => new HttpResponse(null, { status: 204 })),
      http.get('/api/admin/models/metrics/', () => HttpResponse.json([])),
    );
    render(<ModelsSection />);
    await screen.findByTestId('models-section-content');
    expect(await screen.findByTestId('models-metrics-empty')).toBeInTheDocument();
    expect(screen.queryByTestId('models-sparkline')).not.toBeInTheDocument();
  });

  it('error al cargar métricas no bloquea el formulario de configuración', async () => {
    server.use(
      http.get('/api/admin/models/metrics/latest/', () =>
        HttpResponse.json({ detail: 'Servicio caído' }, { status: 503 }),
      ),
    );
    render(<ModelsSection />);
    await screen.findByTestId('models-section-content');
    expect(await screen.findByTestId('models-metrics-error')).toBeInTheDocument();
    // El form de configuración sigue operable
    expect(screen.getByTestId('models-form-submit')).toBeEnabled();
  });

  it('banner de cumplimiento visible cuando confidence_threshold < 0.85', async () => {
    server.use(
      http.get('/api/admin/models/active/', () =>
        HttpResponse.json({
          id: 'x', is_active: true, unet_version: 'u-net-v2.1', unet_enabled: true,
          classifier_version: 'efficientnet-b3-v1.4', classifier_enabled: true,
          confidence_threshold: '0.700', detection_sensitivity: '0.500',
          analysis_mode: 'balanced', log_level: 'INFO',
          updated_at: '2026-06-15T10:00:00Z', updated_by: null, compliance_warning: true,
        }),
      ),
    );
    render(<ModelsSection />);
    await screen.findByTestId('models-section-content');
    expect(await screen.findByTestId('models-compliance-banner')).toHaveTextContent(/0.85/);
  });

  it('cambiar el slider y guardar hace PATCH y refleja compliance_warning', async () => {
    const user = userEvent.setup();
    render(<ModelsSection />);
    await screen.findByTestId('models-section-content');

    const slider = screen.getByTestId('models-input-confidence');
    fireEvent.change(slider, { target: { value: '70' } });
    expect(screen.getByTestId('models-confidence-value')).toHaveTextContent('70%');

    await user.click(screen.getByTestId('models-form-submit'));

    expect(await screen.findByTestId('models-form-saved-at')).toHaveTextContent(/Configuración guardada/);
    expect(await screen.findByTestId('models-compliance-banner')).toBeInTheDocument();
  });

  it('cambiar el slider de sensibilidad hace PATCH con el nuevo valor', async () => {
    const user = userEvent.setup();
    render(<ModelsSection />);
    await screen.findByTestId('models-section-content');

    const slider = screen.getByTestId('models-input-sensitivity');
    fireEvent.change(slider, { target: { value: '75' } });
    expect(screen.getByTestId('models-sensitivity-value')).toHaveTextContent('75%');

    await user.click(screen.getByTestId('models-form-submit'));
    expect(await screen.findByTestId('models-form-saved-at')).toBeInTheDocument();
  });

  it('guardar sin cambios no llama al backend pero da feedback', async () => {
    let patchCalls = 0;
    server.use(
      http.patch('/api/admin/models/active/', async ({ request }) => {
        patchCalls += 1;
        return HttpResponse.json(await request.json());
      }),
    );
    const user = userEvent.setup();
    render(<ModelsSection />);
    await screen.findByTestId('models-section-content');

    await user.click(screen.getByTestId('models-form-submit'));
    expect(await screen.findByTestId('models-form-saved-at')).toBeInTheDocument();
    expect(patchCalls).toBe(0);
  });

  it('restaurar valores por defecto revierte ediciones no guardadas', async () => {
    const user = userEvent.setup();
    render(<ModelsSection />);
    await screen.findByTestId('models-section-content');

    const slider = screen.getByTestId('models-input-confidence');
    fireEvent.change(slider, { target: { value: '10' } });
    expect(screen.getByTestId('models-confidence-value')).toHaveTextContent('10%');

    await user.click(screen.getByTestId('models-form-reset'));
    expect(screen.getByTestId('models-confidence-value')).toHaveTextContent('85%');
  });

  it('cambiar analysis_mode y log_level hace PATCH con los nuevos valores', async () => {
    const user = userEvent.setup();
    render(<ModelsSection />);
    await screen.findByTestId('models-section-content');

    await user.selectOptions(screen.getByTestId('models-input-analysis-mode'), 'accurate');
    await user.selectOptions(screen.getByTestId('models-input-log-level'), 'DEBUG');
    await user.click(screen.getByTestId('models-form-submit'));

    await waitFor(() => {
      expect(screen.getByTestId('models-input-analysis-mode')).toHaveValue('accurate');
    });
    expect(screen.getByTestId('models-input-log-level')).toHaveValue('DEBUG');
  });

  it('toggle de U-Net/EfficientNet cambia estado local y se guarda en PATCH', async () => {
    const user = userEvent.setup();
    render(<ModelsSection />);
    await screen.findByTestId('models-section-content');

    const unetCard = screen.getByTestId('models-card-unet');
    const unetToggle = within(unetCard).getByTestId('status-toggle-on');
    await user.click(unetToggle);
    await user.click(screen.getByTestId('models-form-submit'));

    expect(await screen.findByTestId('models-form-saved-at')).toBeInTheDocument();
  });

  it('PATCH invalido (analysis_mode fuera de choices) muestra error general', async () => {
    server.use(
      http.patch('/api/admin/models/active/', () =>
        HttpResponse.json({ analysis_mode: ['"ultra" no es una elección válida.'] }, { status: 400 }),
      ),
    );
    const user = userEvent.setup();
    render(<ModelsSection />);
    await screen.findByTestId('models-section-content');

    // Forzamos un cambio real para que el diff no esté vacío (analysis_mode)
    await user.selectOptions(screen.getByTestId('models-input-analysis-mode'), 'fast');
    await user.click(screen.getByTestId('models-form-submit'));

    const err = await screen.findByTestId('models-form-error-general');
    expect(err.textContent).toMatch(/analysis_mode/);
  });

  it('error de carga inicial del config → banner con Reintentar', async () => {
    server.use(
      http.get('/api/admin/models/active/', () =>
        HttpResponse.json({ detail: 'Servicio caído' }, { status: 503 }),
      ),
    );
    render(<ModelsSection />);
    const errBanner = await screen.findByTestId('models-section-error-message');
    expect(errBanner).toHaveTextContent(/Servicio caído|Error/i);
    expect(screen.getByTestId('models-section-retry')).toBeInTheDocument();
  });
});
