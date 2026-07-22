/**
 * Tests de NotificationsSection (DD-ADMIN-002 P4, ADR-0014).
 *
 * Verifica el cableado completo:
 *  - Loading inicial + render de la matriz (4 categorías × 2 canales) y
 *    del bloque de horario silencioso.
 *  - Toggle de una celda + guardar hace PATCH solo con el campo cambiado.
 *  - Horario silencioso: activar el toggle revela los time pickers;
 *    cambiarlos y guardar persiste "HH:MM:SS".
 *  - Cancelar revierte ediciones no guardadas.
 *  - Guardar sin cambios no llama al backend pero da feedback.
 *  - Error del backend → banner general.
 */
import { describe, expect, it } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { NotificationsSection } from '../../src/admin/components/NotificationsSection';
import { server } from '../../src/admin/msw/server';

describe('NotificationsSection — P4', () => {
  it('muestra loading inicial y luego la matriz + horario silencioso', async () => {
    render(<NotificationsSection />);
    expect(screen.getByTestId('notifications-section-loading')).toBeInTheDocument();
    expect(await screen.findByTestId('notifications-section-content')).toBeInTheDocument();

    expect(screen.getByTestId('notifications-matrix')).toHaveTextContent('Revisión pendiente');
    expect(screen.getByTestId('notifications-matrix')).toHaveTextContent('Errores del sistema');

    // Defaults del mock: email_training_completed=false, resto=true
    const trainingEmailCell = screen.getByTestId('notifications-cell-email-training_completed');
    expect(within(trainingEmailCell).getByTestId('status-toggle-off')).toBeInTheDocument();
    const reviewEmailCell = screen.getByTestId('notifications-cell-email-review_pending');
    expect(within(reviewEmailCell).getByTestId('status-toggle-on')).toBeInTheDocument();

    // Horario silencioso deshabilitado por defecto → sin time pickers
    expect(screen.queryByTestId('notifications-quiet-start')).not.toBeInTheDocument();
  });

  it('togglear una celda y guardar hace PATCH solo con ese campo', async () => {
    let receivedBody: Record<string, unknown> | null = null;
    server.use(
      http.patch('/api/admin/me/notifications/', async ({ request }) => {
        receivedBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({
          id: 'cccccccc-cccc-cccc-cccc-cccccccccccc',
          email_review_pending: true,
          email_supervisor_validation: true,
          email_system_errors: true,
          email_training_completed: true,
          inapp_review_pending: true,
          inapp_supervisor_validation: true,
          inapp_system_errors: true,
          inapp_training_completed: true,
          quiet_hours_enabled: false,
          quiet_hours_start: '20:00:00',
          quiet_hours_end: '07:00:00',
          updated_at: new Date().toISOString(),
        });
      }),
    );
    const user = userEvent.setup();
    render(<NotificationsSection />);
    await screen.findByTestId('notifications-section-content');

    const trainingEmailCell = screen.getByTestId('notifications-cell-email-training_completed');
    await user.click(within(trainingEmailCell).getByTestId('status-toggle-off'));
    await user.click(screen.getByTestId('notifications-form-submit'));

    expect(await screen.findByTestId('notifications-form-saved-at')).toBeInTheDocument();
    expect(receivedBody).toEqual({ email_training_completed: true });
  });

  it('activar horario silencioso revela los time pickers y permite cambiarlos', async () => {
    const user = userEvent.setup();
    render(<NotificationsSection />);
    await screen.findByTestId('notifications-section-content');

    const quietCell = screen.getByTestId('notifications-cell-quiet-hours-enabled');
    await user.click(within(quietCell).getByTestId('status-toggle-off'));

    const startInput = await screen.findByTestId('notifications-quiet-start');
    expect(startInput).toHaveValue('20:00');
    const endInput = screen.getByTestId('notifications-quiet-end');
    expect(endInput).toHaveValue('07:00');

    await user.clear(startInput);
    await user.type(startInput, '22:30');
    await user.clear(endInput);
    await user.type(endInput, '06:15');
    await user.click(screen.getByTestId('notifications-form-submit'));

    expect(await screen.findByTestId('notifications-form-saved-at')).toBeInTheDocument();
  });

  it('error de validación con fieldErrors → banner aplanado por campo', async () => {
    server.use(
      http.patch('/api/admin/me/notifications/', () =>
        HttpResponse.json({ quiet_hours_start: ['Formato inválido'] }, { status: 400 }),
      ),
    );
    const user = userEvent.setup();
    render(<NotificationsSection />);
    await screen.findByTestId('notifications-section-content');

    const trainingEmailCell = screen.getByTestId('notifications-cell-email-training_completed');
    await user.click(within(trainingEmailCell).getByTestId('status-toggle-off'));
    await user.click(screen.getByTestId('notifications-form-submit'));

    const err = await screen.findByTestId('notifications-form-error-general');
    expect(err.textContent).toMatch(/quiet_hours_start/);
  });

  it('cancelar revierte ediciones no guardadas', async () => {
    const user = userEvent.setup();
    render(<NotificationsSection />);
    await screen.findByTestId('notifications-section-content');

    const trainingEmailCell = screen.getByTestId('notifications-cell-email-training_completed');
    await user.click(within(trainingEmailCell).getByTestId('status-toggle-off'));
    expect(within(trainingEmailCell).getByTestId('status-toggle-on')).toBeInTheDocument();

    await user.click(screen.getByTestId('notifications-form-cancel'));
    expect(within(trainingEmailCell).getByTestId('status-toggle-off')).toBeInTheDocument();
  });

  it('guardar sin cambios no llama al backend pero da feedback', async () => {
    let patchCalls = 0;
    server.use(
      http.patch('/api/admin/me/notifications/', async ({ request }) => {
        patchCalls += 1;
        return HttpResponse.json(await request.json());
      }),
    );
    const user = userEvent.setup();
    render(<NotificationsSection />);
    await screen.findByTestId('notifications-section-content');

    await user.click(screen.getByTestId('notifications-form-submit'));
    expect(await screen.findByTestId('notifications-form-saved-at')).toBeInTheDocument();
    expect(patchCalls).toBe(0);
  });

  it('error del backend en PATCH → banner general', async () => {
    server.use(
      http.patch('/api/admin/me/notifications/', () =>
        HttpResponse.json({ detail: 'Servicio caído' }, { status: 503 }),
      ),
    );
    const user = userEvent.setup();
    render(<NotificationsSection />);
    await screen.findByTestId('notifications-section-content');

    const trainingEmailCell = screen.getByTestId('notifications-cell-email-training_completed');
    await user.click(within(trainingEmailCell).getByTestId('status-toggle-off'));
    await user.click(screen.getByTestId('notifications-form-submit'));

    const err = await screen.findByTestId('notifications-form-error-general');
    expect(err).toHaveTextContent(/Servicio caído/);
  });

  it('error de carga inicial → banner con Reintentar', async () => {
    server.use(
      http.get('/api/admin/me/notifications/', () =>
        HttpResponse.json({ detail: 'Servicio caído' }, { status: 503 }),
      ),
    );
    render(<NotificationsSection />);
    const errBanner = await screen.findByTestId('notifications-section-error-message');
    expect(errBanner).toHaveTextContent(/Servicio caído|Error/i);
    expect(screen.getByTestId('notifications-section-retry')).toBeInTheDocument();
  });
});
