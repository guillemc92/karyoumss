/**
 * Tests de SecuritySection (DD-ADMIN-002 P2, ADR-0014).
 *
 * Verifica el cableado completo:
 *  - Loading inicial + render de ambos bloques (password, 2FA).
 *  - Password: validación Zod (corta/mismatch), submit válido, error backend.
 *  - 2FA: activar (setup → QR/secret → código) éxito e inválido; desactivar
 *    (código directo, sin nuevo QR) éxito e inválido.
 */
import { describe, expect, it } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { SecuritySection } from '../../src/admin/components/SecuritySection';
import { server } from '../../src/admin/msw/server';

describe('SecuritySection — P2', () => {
  it('muestra loading inicial y luego ambos bloques (password + 2FA)', async () => {
    render(<SecuritySection />);
    expect(screen.getByTestId('security-section-loading')).toBeInTheDocument();
    expect(await screen.findByTestId('security-section-content')).toBeInTheDocument();
    expect(screen.getByTestId('security-password-form')).toBeInTheDocument();
    expect(screen.getByTestId('security-2fa-section')).toBeInTheDocument();
    // Perfil mock por defecto: 2FA deshabilitado
    expect(screen.getByTestId('status-toggle-off')).toBeInTheDocument();
  });

  describe('Cambiar contraseña', () => {
    it('valida contraseña muy corta antes de llamar al backend', async () => {
      const user = userEvent.setup();
      render(<SecuritySection />);
      await screen.findByTestId('security-section-content');

      await user.type(screen.getByTestId('security-password-form-input-current'), 'CurrentPass1');
      await user.type(screen.getByTestId('security-password-form-input-new'), 'Sh0rt');
      await user.type(screen.getByTestId('security-password-form-input-confirm'), 'Sh0rt');
      await user.click(screen.getByTestId('security-password-form-submit'));

      expect(await screen.findByTestId('security-password-form-error-new')).toHaveTextContent(
        /12 caracteres/,
      );
    });

    it('valida mismatch entre nueva y confirmación', async () => {
      const user = userEvent.setup();
      render(<SecuritySection />);
      await screen.findByTestId('security-section-content');

      await user.type(screen.getByTestId('security-password-form-input-current'), 'CurrentPass1');
      await user.type(screen.getByTestId('security-password-form-input-new'), 'NuevaPass123x');
      await user.type(screen.getByTestId('security-password-form-input-confirm'), 'Different123x');
      await user.click(screen.getByTestId('security-password-form-submit'));

      expect(await screen.findByTestId('security-password-form-error-confirm')).toHaveTextContent(
        /no coincide/i,
      );
    });

    it('submit válido → feedback "Contraseña actualizada a las …"', async () => {
      const user = userEvent.setup();
      render(<SecuritySection />);
      await screen.findByTestId('security-section-content');

      await user.type(screen.getByTestId('security-password-form-input-current'), 'CurrentPass1');
      await user.type(screen.getByTestId('security-password-form-input-new'), 'NuevaPass123x');
      await user.type(screen.getByTestId('security-password-form-input-confirm'), 'NuevaPass123x');
      await user.click(screen.getByTestId('security-password-form-submit'));

      const saved = await screen.findByTestId('security-password-form-saved-at');
      expect(saved).toHaveTextContent(/Contraseña actualizada/);
    });

    it('current incorrecta → banner de error del backend', async () => {
      const user = userEvent.setup();
      render(<SecuritySection />);
      await screen.findByTestId('security-section-content');

      await user.type(screen.getByTestId('security-password-form-input-current'), 'wrong-password');
      await user.type(screen.getByTestId('security-password-form-input-new'), 'NuevaPass123x');
      await user.type(screen.getByTestId('security-password-form-input-confirm'), 'NuevaPass123x');
      await user.click(screen.getByTestId('security-password-form-submit'));

      const err = await screen.findByTestId('security-password-form-error-general');
      expect(err.textContent).toMatch(/incorrecta/i);
    });
  });

  describe('2FA', () => {
    it('activar: click en toggle → genera QR/secret → código inválido rechazado', async () => {
      const user = userEvent.setup();
      render(<SecuritySection />);
      await screen.findByTestId('security-section-content');

      await user.click(screen.getByTestId('status-toggle-off'));

      expect(await screen.findByTestId('security-2fa-setup')).toBeInTheDocument();
      expect(screen.getByTestId('security-2fa-qr')).toBeInTheDocument();
      expect(screen.getByTestId('security-2fa-secret')).toHaveTextContent('JBSWY3DPEHPK3PXP');

      await user.type(screen.getByTestId('security-2fa-code-input'), '000000');
      await user.click(screen.getByTestId('security-2fa-confirm'));

      // '000000' pasa la validación de formato (6 dígitos) client-side, así
      // que el rechazo viene del backend → banner general, no codeError.
      expect(await screen.findByTestId('security-2fa-error-general')).toHaveTextContent(/inválid/i);
    });

    it('activar: código válido → 2FA queda habilitado', async () => {
      const user = userEvent.setup();
      render(<SecuritySection />);
      await screen.findByTestId('security-section-content');

      await user.click(screen.getByTestId('status-toggle-off'));
      await screen.findByTestId('security-2fa-setup');

      await user.type(screen.getByTestId('security-2fa-code-input'), '123456');
      await user.click(screen.getByTestId('security-2fa-confirm'));

      await waitFor(() => {
        expect(screen.getByTestId('status-toggle-on')).toBeInTheDocument();
      });
      expect(screen.queryByTestId('security-2fa-code-form')).not.toBeInTheDocument();
    });

    it('código con formato inválido (no 6 dígitos) se rechaza client-side', async () => {
      const user = userEvent.setup();
      render(<SecuritySection />);
      await screen.findByTestId('security-section-content');

      await user.click(screen.getByTestId('status-toggle-off'));
      await screen.findByTestId('security-2fa-setup');

      await user.type(screen.getByTestId('security-2fa-code-input'), '12');
      await user.click(screen.getByTestId('security-2fa-confirm'));

      expect(await screen.findByTestId('security-2fa-code-error')).toHaveTextContent(/6 dígitos/);
    });

    it('cancelar durante el setup vuelve al estado inicial (sin QR)', async () => {
      const user = userEvent.setup();
      render(<SecuritySection />);
      await screen.findByTestId('security-section-content');

      await user.click(screen.getByTestId('status-toggle-off'));
      await screen.findByTestId('security-2fa-setup');
      await user.click(screen.getByTestId('security-2fa-cancel'));

      expect(screen.queryByTestId('security-2fa-setup')).not.toBeInTheDocument();
      expect(screen.queryByTestId('security-2fa-code-form')).not.toBeInTheDocument();
      expect(screen.getByTestId('status-toggle-off')).toBeInTheDocument();
    });

    it('desactivar: 2FA ya habilitado → click pide código directo (sin QR nuevo)', async () => {
      server.use(
        http.get('/api/admin/me/profile/', () =>
          HttpResponse.json({
            id: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
            full_name: 'María García López',
            email: 'maria.garcia@biomed.umss.bo',
            specialty: 'Citogenética Clínica',
            professional_license: 'MED-4452-BO',
            phone: '+591 2 2154847',
            location: 'UMSS · Hospital del Norte',
            avatar_url: '',
            updated_at: '2026-06-15T10:00:00Z',
            two_factor_enabled: true,
          }),
        ),
      );
      const user = userEvent.setup();
      render(<SecuritySection />);
      await screen.findByTestId('security-section-content');
      expect(screen.getByTestId('status-toggle-on')).toBeInTheDocument();

      await user.click(screen.getByTestId('status-toggle-on'));

      expect(await screen.findByTestId('security-2fa-code-form')).toBeInTheDocument();
      expect(screen.queryByTestId('security-2fa-setup')).not.toBeInTheDocument();

      await user.type(screen.getByTestId('security-2fa-code-input'), '123456');
      await user.click(screen.getByTestId('security-2fa-confirm'));

      await waitFor(() => {
        expect(screen.getByTestId('status-toggle-off')).toBeInTheDocument();
      });
    });

    it('error del backend en /2fa/setup/ → banner general', async () => {
      server.use(
        http.post('/api/admin/me/2fa/setup/', () =>
          HttpResponse.json({ detail: 'Servicio caído' }, { status: 503 }),
        ),
      );
      const user = userEvent.setup();
      render(<SecuritySection />);
      await screen.findByTestId('security-section-content');

      await user.click(screen.getByTestId('status-toggle-off'));

      const err = await screen.findByTestId('security-2fa-error-general');
      expect(err).toBeInTheDocument();
    });
  });
});
