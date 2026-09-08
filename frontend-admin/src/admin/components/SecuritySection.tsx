/**
 * SecuritySection — vista de la sección "Seguridad" del bounded context
 * config (DD-ADMIN-002 P2, ADR-0014).
 *
 * Dos bloques independientes (no comparten un único "recurso" PATCH-able,
 * a diferencia de ProfileSection, por eso no reutiliza ConfigForm):
 *  - Cambio de contraseña: POST /api/admin/me/password/.
 *  - 2FA: POST /api/admin/me/2fa/setup/ (genera QR+secret) y
 *    POST /api/admin/me/2fa/toggle/ (confirma con código TOTP y
 *    activa/desactiva). El QR ya viene renderizado como PNG base64 desde
 *    el backend — el frontend no necesita ninguna librería TOTP, solo
 *    mostrar la imagen y el input de 6 dígitos.
 *
 * El estado inicial de 2FA (`two_factor_enabled`) se lee del mismo
 * /me/profile/ que ya consume ProfileSection (ver AdminProfileSerializer).
 */
import { FormEvent, useCallback, useState } from 'react';
import { ConfigSection } from './ConfigSection';
import { StatusToggle } from './StatusToggle';
import { AdminApiException } from '../types/adminUser';
import { adminConfigClient } from '../api/adminConfigClient';
import {
  AdminProfile,
  TwoFactorSetup,
  changePasswordSchema,
  totpCodeSchema,
} from '../types/config';

function errorMessageFromUnknown(err: unknown): string {
  if (err instanceof AdminApiException) {
    if (err.error.kind === 'validation' && err.error.fieldErrors) {
      const lines = Object.entries(err.error.fieldErrors)
        .map(([k, v]) => `${k}: ${v.join(', ')}`)
        .join(' · ');
      return lines || err.error.message;
    }
    return err.error.message;
  }
  return err instanceof Error ? err.message : 'Error desconocido';
}

function PasswordSection() {
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [confirm, setConfirm] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    setGeneralError(null);
    setSavedAt(null);

    const parsed = changePasswordSchema.safeParse({ current, new: next, confirm });
    if (!parsed.success) {
      const fieldErrors: Record<string, string> = {};
      for (const issue of parsed.error.issues) {
        const path = issue.path.join('.');
        if (path && !fieldErrors[path]) fieldErrors[path] = issue.message;
      }
      setErrors(fieldErrors);
      return;
    }
    setErrors({});
    setSubmitting(true);
    try {
      await adminConfigClient.changePassword(parsed.data);
      setSavedAt(new Date().toLocaleTimeString());
      setCurrent('');
      setNext('');
      setConfirm('');
    } catch (err) {
      setGeneralError(errorMessageFromUnknown(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form
      className="biomed-user-form"
      data-testid="security-password-form"
      onSubmit={handleSubmit}
      noValidate
    >
      <div className="biomed-form-section">
        <div className="biomed-form-section-title">Cambiar contraseña</div>
        <div className="biomed-form-grid">
          <div className="biomed-form-group" style={{ gridColumn: '1 / -1' }}>
            <label className="biomed-form-label" htmlFor="security-current-password">
              Contraseña actual
            </label>
            <input
              id="security-current-password"
              type="password"
              className="biomed-form-input"
              value={current}
              autoComplete="current-password"
              onChange={(e) => setCurrent(e.target.value)}
              data-testid="security-password-form-input-current"
            />
            {errors.current && (
              <span
                role="alert"
                className="biomed-form-error"
                data-testid="security-password-form-error-current"
              >
                {errors.current}
              </span>
            )}
          </div>
          <div className="biomed-form-group" style={{ gridColumn: '1 / -1' }}>
            <label className="biomed-form-label" htmlFor="security-new-password">
              Nueva contraseña
            </label>
            <input
              id="security-new-password"
              type="password"
              className="biomed-form-input"
              value={next}
              autoComplete="new-password"
              onChange={(e) => setNext(e.target.value)}
              data-testid="security-password-form-input-new"
            />
            {errors.new && (
              <span
                role="alert"
                className="biomed-form-error"
                data-testid="security-password-form-error-new"
              >
                {errors.new}
              </span>
            )}
          </div>
          <div className="biomed-form-group" style={{ gridColumn: '1 / -1' }}>
            <label className="biomed-form-label" htmlFor="security-confirm-password">
              Confirmar contraseña
            </label>
            <input
              id="security-confirm-password"
              type="password"
              className="biomed-form-input"
              value={confirm}
              autoComplete="new-password"
              onChange={(e) => setConfirm(e.target.value)}
              data-testid="security-password-form-input-confirm"
            />
            {errors.confirm && (
              <span
                role="alert"
                className="biomed-form-error"
                data-testid="security-password-form-error-confirm"
              >
                {errors.confirm}
              </span>
            )}
          </div>
        </div>
      </div>

      {generalError && (
        <p
          role="alert"
          className="biomed-form-error"
          data-testid="security-password-form-error-general"
        >
          {generalError}
        </p>
      )}
      {savedAt && !generalError && (
        <p
          className="biomed-form-hint"
          data-testid="security-password-form-saved-at"
          aria-live="polite"
        >
          <i className="fas fa-check" aria-hidden="true" /> Contraseña actualizada a las {savedAt}
        </p>
      )}

      <div className="biomed-form-actions">
        <button
          type="submit"
          disabled={submitting}
          data-testid="security-password-form-submit"
          className="biomed-btn biomed-btn--primary"
        >
          <i className="fas fa-key" aria-hidden="true" />
          {submitting ? 'Actualizando…' : 'Actualizar contraseña'}
        </button>
      </div>
    </form>
  );
}

function TwoFactorSection({ initialEnabled }: { initialEnabled: boolean }) {
  const [enabled, setEnabled] = useState(initialEnabled);
  const [setup, setSetup] = useState<TwoFactorSetup | null>(null);
  const [pendingDisable, setPendingDisable] = useState(false);
  const [code, setCode] = useState('');
  const [codeError, setCodeError] = useState<string | null>(null);
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [savedAt, setSavedAt] = useState<string | null>(null);

  const showCodeForm = setup !== null || pendingDisable;

  async function handleToggleClick(next: boolean) {
    setGeneralError(null);
    setSavedAt(null);
    setCode('');
    setCodeError(null);

    if (next) {
      setSubmitting(true);
      try {
        const result = await adminConfigClient.setup2FA();
        setSetup(result);
        setPendingDisable(false);
      } catch (err) {
        setGeneralError(errorMessageFromUnknown(err));
      } finally {
        setSubmitting(false);
      }
    } else {
      // Desactivar exige código también (protección contra sesión robada,
      // DD-ADMIN-002 §3.4) pero no requiere un QR nuevo.
      setSetup(null);
      setPendingDisable(true);
    }
  }

  async function handleConfirm(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    setGeneralError(null);
    setCodeError(null);

    const parsed = totpCodeSchema.safeParse(code);
    if (!parsed.success) {
      setCodeError(parsed.error.issues[0]?.message ?? 'Código inválido');
      return;
    }

    const targetEnabled = setup !== null;
    setSubmitting(true);
    try {
      const result = await adminConfigClient.toggle2FA(targetEnabled, parsed.data);
      setEnabled(result.two_factor_enabled);
      setSetup(null);
      setPendingDisable(false);
      setCode('');
      setSavedAt(new Date().toLocaleTimeString());
    } catch (err) {
      setGeneralError(errorMessageFromUnknown(err));
    } finally {
      setSubmitting(false);
    }
  }

  function handleCancel() {
    setSetup(null);
    setPendingDisable(false);
    setCode('');
    setCodeError(null);
    setGeneralError(null);
  }

  return (
    <div className="biomed-form-section" data-testid="security-2fa-section">
      <div className="biomed-form-section-title">Autenticación de dos factores</div>
      <div
        className="biomed-history-item"
        style={{
          padding: 16,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 16,
        }}
      >
        <div>
          <strong>Verificación en dos pasos (2FA)</strong>
          <p className="biomed-history-item__meta" style={{ margin: 0 }}>
            Agrega una capa adicional de seguridad a tu cuenta
          </p>
        </div>
        <StatusToggle
          active={enabled}
          disabled={submitting || showCodeForm}
          onChange={handleToggleClick}
        />
      </div>

      {setup && (
        <div data-testid="security-2fa-setup" style={{ marginTop: 16 }}>
          <p className="biomed-form-hint">
            Escanea el código con tu app autenticadora (Google Authenticator, Authy, etc.)
            o ingresa el secret manualmente.
          </p>
          <img
            src={`data:image/png;base64,${setup.qr_code_b64}`}
            alt="Código QR para configurar 2FA"
            data-testid="security-2fa-qr"
            width={180}
            height={180}
          />
          <p className="biomed-form-hint" data-testid="security-2fa-secret">
            Secret: <code>{setup.secret}</code>
          </p>
        </div>
      )}

      {showCodeForm && (
        <form
          onSubmit={handleConfirm}
          noValidate
          style={{ marginTop: 16 }}
          data-testid="security-2fa-code-form"
        >
          <div className="biomed-form-group">
            <label className="biomed-form-label" htmlFor="security-2fa-code">
              Código de verificación (6 dígitos)
            </label>
            <input
              id="security-2fa-code"
              type="text"
              inputMode="numeric"
              maxLength={6}
              className="biomed-form-input"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              data-testid="security-2fa-code-input"
            />
            {codeError && (
              <span role="alert" className="biomed-form-error" data-testid="security-2fa-code-error">
                {codeError}
              </span>
            )}
          </div>
          <div className="biomed-form-actions">
            <button
              type="button"
              className="biomed-btn biomed-btn--outline"
              onClick={handleCancel}
              disabled={submitting}
              data-testid="security-2fa-cancel"
            >
              Cancelar
            </button>
            <button
              type="submit"
              className="biomed-btn biomed-btn--primary"
              disabled={submitting}
              data-testid="security-2fa-confirm"
            >
              {submitting ? 'Verificando…' : pendingDisable ? 'Desactivar 2FA' : 'Activar 2FA'}
            </button>
          </div>
        </form>
      )}

      {generalError && (
        <p role="alert" className="biomed-form-error" data-testid="security-2fa-error-general">
          {generalError}
        </p>
      )}
      {savedAt && !generalError && !showCodeForm && (
        <p className="biomed-form-hint" data-testid="security-2fa-saved-at" aria-live="polite">
          <i className="fas fa-check" aria-hidden="true" /> Actualizado a las {savedAt}
        </p>
      )}
    </div>
  );
}

export function SecuritySection() {
  const loadProfile = useCallback(() => adminConfigClient.getProfile(), []);

  return (
    <ConfigSection<AdminProfile>
      load={loadProfile}
      testId="security-section"
      loadingText="Cargando seguridad…"
    >
      {(profile) => (
        <div data-testid="security-section-content">
          <PasswordSection />
          <TwoFactorSection initialEnabled={profile.two_factor_enabled} />
        </div>
      )}
    </ConfigSection>
  );
}
