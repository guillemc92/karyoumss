/**
 * SignMfaModal — captura del código MFA para firmar el reporte (S2, DD-SUP-002).
 * La verificación TOTP la hace backend-admin (ADR-0023 D3); acá solo se recoge
 * el código de 6 dígitos.
 */
import { useState } from 'react';

interface Props {
  onSubmit: (code: string) => void;
  onClose: () => void;
  busy?: boolean;
  error?: string | null;
}

export function SignMfaModal({ onSubmit, onClose, busy = false, error = null }: Props) {
  const [code, setCode] = useState('');
  const valid = /^\d{6}$/.test(code);

  return (
    <div className="modal-overlay" role="dialog" aria-modal="true" aria-label="Firmar reporte con MFA" data-testid="sign-mfa-modal">
      <div className="modal-content modal-content--small">
        <h3>🔐 Firmar reporte</h3>
        <div className="sign-mfa__body">
          <p className="karyo-props__hint">
            Ingrese el código de 6 dígitos de su app de autenticación (TOTP) para firmar
            digitalmente el reporte (21 CFR Part 11).
          </p>
          <input
            type="text"
            inputMode="numeric"
            maxLength={6}
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
            placeholder="123456"
            className="sign-mfa__input"
            data-testid="sign-mfa-input"
            aria-label="Código MFA"
            autoFocus
          />
          {error && <p className="karyo-alert karyo-alert--red" role="alert" data-testid="sign-mfa-error">{error}</p>}
          <div className="modal-actions">
            <button type="button" onClick={onClose} disabled={busy} data-testid="sign-mfa-cancel">Cancelar</button>
            <button
              type="button" className="btn-primary" disabled={!valid || busy}
              onClick={() => onSubmit(code)} data-testid="sign-mfa-submit"
            >{busy ? 'Firmando…' : 'Firmar'}</button>
          </div>
        </div>
      </div>
    </div>
  );
}
