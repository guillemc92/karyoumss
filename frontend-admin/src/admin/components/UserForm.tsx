import { FormEvent, useEffect, useState } from 'react';
import { ADMIN_ROLES, AdminRole, AdminUser, AdminUserDraft } from '../types/adminUser';
import { StatusToggle } from './StatusToggle';

interface UserFormProps {
  /** Si se pasa, el formulario opera en modo edición. */
  editing?: AdminUser;
  onSubmit: (draft: AdminUserDraft) => Promise<void>;
  onCancel: () => void;
}

interface FieldErrors {
  full_name?: string;
  email?: string;
  role?: string;
  password?: string;
  confirm_password?: string;
  general?: string;
}

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
/** Misma política que backend-admin (services.create_admin_user /
 * apps.config.services.rotate_password): ≥12 caracteres, 1 mayúscula, 1 dígito. */
const PASSWORD_MIN_LENGTH = 12;

function validatePasswordStrength(password: string): string | undefined {
  if (
    password.length < PASSWORD_MIN_LENGTH ||
    !/[A-Z]/.test(password) ||
    !/[0-9]/.test(password)
  ) {
    return `Mínimo ${PASSWORD_MIN_LENGTH} caracteres, 1 mayúscula, 1 dígito`;
  }
  return undefined;
}

export function UserForm({ editing, onSubmit, onCancel }: UserFormProps) {
  const [fullName, setFullName] = useState(editing?.full_name ?? '');
  const [email, setEmail] = useState(editing?.email ?? '');
  const [role, setRole] = useState<AdminRole>(editing?.role ?? 'analista');
  const [active, setActive] = useState<boolean>(editing?.active ?? true);
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [errors, setErrors] = useState<FieldErrors>({});
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    setFullName(editing?.full_name ?? '');
    setEmail(editing?.email ?? '');
    setRole(editing?.role ?? 'analista');
    setActive(editing?.active ?? true);
    setPassword('');
    setConfirmPassword('');
    setErrors({});
  }, [editing?.id, editing?.full_name, editing?.email, editing?.role, editing?.active]);

  function validate(): FieldErrors {
    const e: FieldErrors = {};
    const trimmedName = fullName.trim();
    if (trimmedName.length < 2) e.full_name = 'El nombre debe tener al menos 2 caracteres';
    if (trimmedName.length > 80) e.full_name = 'El nombre no debe exceder 80 caracteres';
    if (!editing) {
      const trimmedEmail = email.trim().toLowerCase();
      if (!trimmedEmail) e.email = 'El email es obligatorio';
      else if (!EMAIL_RE.test(trimmedEmail)) e.email = 'Email inválido';

      const strengthError = validatePasswordStrength(password);
      if (strengthError) e.password = strengthError;
      if (confirmPassword !== password) e.confirm_password = 'No coincide con la contraseña';
    }
    if (!ADMIN_ROLES.includes(role)) e.role = 'Rol inválido';
    return e;
  }

  async function handleSubmit(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    const v = validate();
    setErrors(v);
    if (Object.keys(v).length > 0) return;
    setSubmitting(true);
    try {
      const draft: AdminUserDraft = {
        full_name: fullName.trim(),
        email: email.trim().toLowerCase(),
        role,
        active,
        password,
      };
      await onSubmit(draft);
    } catch (err) {
      setErrors({ general: err instanceof Error ? err.message : 'Error al guardar' });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form
      className="biomed-user-form"
      data-testid="user-form"
      onSubmit={handleSubmit}
      noValidate
    >
      <h2>{editing ? 'Editar usuario' : 'Nuevo usuario'}</h2>

      <div className="biomed-form-section">
        <div className="biomed-form-section-title">Información del usuario</div>
        <div className="biomed-form-grid">
          <div className="biomed-form-group" style={{ gridColumn: '1 / -1' }}>
            <label className="biomed-form-label" htmlFor="user-input-full_name">
              Nombre completo *
            </label>
            <input
              id="user-input-full_name"
              type="text"
              className="biomed-form-input"
              value={fullName}
              maxLength={80}
              onChange={(e) => setFullName(e.target.value)}
              data-testid="input-full_name"
              required
            />
            {errors.full_name && (
              <span role="alert" className="biomed-form-error" data-testid="error-full_name">
                {errors.full_name}
              </span>
            )}
          </div>

          <div className="biomed-form-group" style={{ gridColumn: '1 / -1' }}>
            <label className="biomed-form-label" htmlFor="user-input-email">
              Email institucional *
            </label>
            <input
              id="user-input-email"
              type="email"
              className="biomed-form-input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              data-testid="input-email"
              required
              readOnly={Boolean(editing)}
              aria-readonly={Boolean(editing)}
            />
            {editing && <small className="biomed-form-hint">El email no se puede modificar.</small>}
            {errors.email && (
              <span role="alert" className="biomed-form-error" data-testid="error-email">
                {errors.email}
              </span>
            )}
          </div>

          {!editing && (
            <>
              <div className="biomed-form-group">
                <label className="biomed-form-label" htmlFor="user-input-password">
                  Contraseña inicial *
                </label>
                <input
                  id="user-input-password"
                  type="password"
                  className="biomed-form-input"
                  value={password}
                  autoComplete="new-password"
                  onChange={(e) => setPassword(e.target.value)}
                  data-testid="input-password"
                  required
                />
                <small className="biomed-form-hint">Mínimo 12 caracteres, 1 mayúscula, 1 dígito.</small>
                {errors.password && (
                  <span role="alert" className="biomed-form-error" data-testid="error-password">
                    {errors.password}
                  </span>
                )}
              </div>

              <div className="biomed-form-group">
                <label className="biomed-form-label" htmlFor="user-input-confirm-password">
                  Confirmar contraseña *
                </label>
                <input
                  id="user-input-confirm-password"
                  type="password"
                  className="biomed-form-input"
                  value={confirmPassword}
                  autoComplete="new-password"
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  data-testid="input-confirm-password"
                  required
                />
                {errors.confirm_password && (
                  <span role="alert" className="biomed-form-error" data-testid="error-confirm-password">
                    {errors.confirm_password}
                  </span>
                )}
              </div>
            </>
          )}

          <div className="biomed-form-group">
            <label className="biomed-form-label" htmlFor="user-input-role">
              Rol *
            </label>
            <select
              id="user-input-role"
              className="biomed-form-select"
              value={role}
              onChange={(e) => setRole(e.target.value as AdminRole)}
              data-testid="select-role"
            >
              <option value="analista">Analista</option>
              <option value="supervisor">Supervisor</option>
              <option value="admin">Administrador TI</option>
            </select>
            {errors.role && (
              <span role="alert" className="biomed-form-error">
                {errors.role}
              </span>
            )}
          </div>

          <div className="biomed-form-group">
            <label className="biomed-form-label">Estado</label>
            <StatusToggle active={active} onChange={setActive} disabled={submitting} />
          </div>
        </div>
      </div>

      {errors.general && (
        <p role="alert" className="biomed-form-error" data-testid="error-general">
          {errors.general}
        </p>
      )}

      <div className="biomed-form-actions">
        <button
          type="button"
          onClick={onCancel}
          disabled={submitting}
          data-testid="cancel-user"
          className="biomed-btn biomed-btn--outline"
        >
          <i className="fas fa-times" aria-hidden="true" /> Cancelar
        </button>
        <button
          type="submit"
          disabled={submitting}
          data-testid="submit-user"
          className="biomed-btn biomed-btn--primary"
        >
          <i className="fas fa-save" aria-hidden="true" />
          {submitting ? 'Guardando…' : editing ? 'Guardar cambios' : 'Crear usuario'}
        </button>
      </div>
    </form>
  );
}
