/**
 * Tests de AppearanceSection (DD-ADMIN-002 P6, ADR-0014).
 *
 * Verifica el cableado completo:
 *  - Loading inicial + render de los 4 selects con defaults del MSW.
 *  - Aplica data-theme/lang en <html> al montar.
 *  - Cambiar tema + guardar hace PATCH solo con el campo modificado y
 *    reaplica data-theme.
 *  - Cancelar revierte ediciones no guardadas.
 *  - Guardar sin cambios no llama al backend pero da feedback.
 *  - Error de validación (400) → banner con el campo señalado.
 *  - Error de carga inicial → banner con Reintentar.
 */
import { afterEach, describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { AppearanceSection } from '../../src/admin/components/AppearanceSection';
import { server } from '../../src/admin/msw/server';

describe('AppearanceSection — P6', () => {
  afterEach(() => {
    delete document.documentElement.dataset.theme;
    document.documentElement.lang = '';
  });

  it('muestra loading inicial y luego los 4 selects con defaults del MSW', async () => {
    render(<AppearanceSection />);
    expect(screen.getByTestId('appearance-section-loading')).toBeInTheDocument();
    expect(await screen.findByTestId('appearance-section-content')).toBeInTheDocument();

    expect(screen.getByTestId('appearance-input-theme')).toHaveValue('light');
    expect(screen.getByTestId('appearance-input-density')).toHaveValue('comfortable');
    expect(screen.getByTestId('appearance-input-language')).toHaveValue('es');
    expect(screen.getByTestId('appearance-input-font-size')).toHaveValue('md');
  });

  it('aplica data-theme y lang en <html> al montar', async () => {
    render(<AppearanceSection />);
    await screen.findByTestId('appearance-section-content');
    expect(document.documentElement.dataset.theme).toBe('light');
    expect(document.documentElement.lang).toBe('es');
  });

  it('cambiar tema y guardar hace PATCH solo con ese campo y reaplica data-theme', async () => {
    let receivedBody: Record<string, unknown> | null = null;
    server.use(
      http.patch('/api/admin/me/appearance/', async ({ request }) => {
        receivedBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({
          id: 'dddddddd-dddd-dddd-dddd-dddddddddddd',
          theme: 'dark',
          density: 'comfortable',
          language: 'es',
          font_size: 'md',
          updated_at: new Date().toISOString(),
        });
      }),
    );
    const user = userEvent.setup();
    render(<AppearanceSection />);
    await screen.findByTestId('appearance-section-content');

    await user.selectOptions(screen.getByTestId('appearance-input-theme'), 'dark');
    await user.click(screen.getByTestId('appearance-form-submit'));

    expect(await screen.findByTestId('appearance-form-saved-at')).toBeInTheDocument();
    expect(receivedBody).toEqual({ theme: 'dark' });
    expect(document.documentElement.dataset.theme).toBe('dark');
  });

  it('cancelar revierte ediciones no guardadas', async () => {
    const user = userEvent.setup();
    render(<AppearanceSection />);
    await screen.findByTestId('appearance-section-content');

    await user.selectOptions(screen.getByTestId('appearance-input-density'), 'spacious');
    expect(screen.getByTestId('appearance-input-density')).toHaveValue('spacious');

    await user.click(screen.getByTestId('appearance-form-cancel'));
    expect(screen.getByTestId('appearance-input-density')).toHaveValue('comfortable');
  });

  it('cambiar idioma y tamaño de fuente hace PATCH con ambos campos', async () => {
    let receivedBody: Record<string, unknown> | null = null;
    server.use(
      http.patch('/api/admin/me/appearance/', async ({ request }) => {
        receivedBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({
          id: 'dddddddd-dddd-dddd-dddd-dddddddddddd',
          theme: 'light',
          density: 'comfortable',
          language: 'en',
          font_size: 'lg',
          updated_at: new Date().toISOString(),
        });
      }),
    );
    const user = userEvent.setup();
    render(<AppearanceSection />);
    await screen.findByTestId('appearance-section-content');

    await user.selectOptions(screen.getByTestId('appearance-input-language'), 'en');
    await user.selectOptions(screen.getByTestId('appearance-input-font-size'), 'lg');
    await user.click(screen.getByTestId('appearance-form-submit'));

    expect(await screen.findByTestId('appearance-form-saved-at')).toBeInTheDocument();
    expect(receivedBody).toEqual({ language: 'en', font_size: 'lg' });
    expect(document.documentElement.lang).toBe('en');
  });

  it('guardar sin cambios no llama al backend pero da feedback', async () => {
    let patchCalls = 0;
    server.use(
      http.patch('/api/admin/me/appearance/', async ({ request }) => {
        patchCalls += 1;
        return HttpResponse.json(await request.json());
      }),
    );
    const user = userEvent.setup();
    render(<AppearanceSection />);
    await screen.findByTestId('appearance-section-content');

    await user.click(screen.getByTestId('appearance-form-submit'));
    expect(await screen.findByTestId('appearance-form-saved-at')).toBeInTheDocument();
    expect(patchCalls).toBe(0);
  });

  it('error de validación (400) → banner con el campo señalado', async () => {
    server.use(
      http.patch('/api/admin/me/appearance/', () =>
        HttpResponse.json({ theme: ['"invalid" no es una elección válida.'] }, { status: 400 }),
      ),
    );
    const user = userEvent.setup();
    render(<AppearanceSection />);
    await screen.findByTestId('appearance-section-content');

    await user.selectOptions(screen.getByTestId('appearance-input-theme'), 'dark');
    await user.click(screen.getByTestId('appearance-form-submit'));

    const err = await screen.findByTestId('appearance-form-error-general');
    expect(err.textContent).toMatch(/theme/);
  });

  it('error del backend con detail plano (sin fieldErrors) → usa err.error.message', async () => {
    server.use(
      http.patch('/api/admin/me/appearance/', () =>
        HttpResponse.json({ detail: 'No autorizado' }, { status: 403 }),
      ),
    );
    const user = userEvent.setup();
    render(<AppearanceSection />);
    await screen.findByTestId('appearance-section-content');

    await user.selectOptions(screen.getByTestId('appearance-input-theme'), 'dark');
    await user.click(screen.getByTestId('appearance-form-submit'));

    const err = await screen.findByTestId('appearance-form-error-general');
    expect(err).toHaveTextContent(/No autorizado/);
  });

  it('error de carga inicial → banner con Reintentar', async () => {
    server.use(
      http.get('/api/admin/me/appearance/', () =>
        HttpResponse.json({ detail: 'Servicio caído' }, { status: 503 }),
      ),
    );
    render(<AppearanceSection />);
    const errBanner = await screen.findByTestId('appearance-section-error-message');
    expect(errBanner).toHaveTextContent(/Servicio caído|Error/i);
    expect(screen.getByTestId('appearance-section-retry')).toBeInTheDocument();
  });
});
