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
  general?: string;
}

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function UserForm({ editing, onSubmit, onCancel }: UserFormProps) {
  const [fullName, setFullName] = useState(editing?.full_name ?? '');
  const [email, setEmail] = useState(editing?.email ?? '');
  const [role, setRole] = useState<AdminRole>(editing?.role ?? 'analista');
  const [active, setActive] = useState<boolean>(editing?.active ?? true);
  const [errors, setErrors] = useState<FieldErrors>({});
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    setFullName(editing?.full_name ?? '');
    setEmail(editing?.email ?? '');
    setRole(editing?.role ?? 'analista');
    setActive(editing?.active ?? true);
    setErrors({});
  }, [editing?.id, editing?.full_name, editing?.email, editing?.role, editing?.active]);

  function validate(): FieldErrors {
    const e: FieldErrors = {};
    const trimmedName = fullName.trim();
    if (trimmedName.length < 2) e.full_name = 'El nombre debe tener al menos 2 caracteres';
    if (trimmedName.length > 80) e.full_name = 'El nombre no debe exceder 80 caracteres';
    if (!editing) {
      // En creación, email es obligatorio y formato válido
      const trimmedEmail = email.trim().toLowerCase();
      if (!trimmedEmail) e.email = 'El email es obligatorio';
      else if (!EMAIL_RE.test(trimmedEmail)) e.email = 'Email inválido';
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
      const draft: AdminUserDraft = editing
        ? { full_name: fullName.trim(), email: email.trim().toLowerCase(), role, active }
        : { full_name: fullName.trim(), email: email.trim().toLowerCase(), role, active };
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

      <label>
        <span>Nombre completo</span>
        <input
          type="text"
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
      </label>

      <label>
        <span>Email</span>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          data-testid="input-email"
          required
          readOnly={Boolean(editing)}
          aria-readonly={Boolean(editing)}
        />
        {editing && (
          <small className="biomed-form-hint">El email no se puede modificar.</small>
        )}
        {errors.email && (
          <span role="alert" className="biomed-form-error" data-testid="error-email">
            {errors.email}
          </span>
        )}
      </label>

      <label>
        <span>Rol</span>
        <select
          value={role}
          onChange={(e) => setRole(e.target.value as AdminRole)}
          data-testid="select-role"
        >
          <option value="analista">Analista</option>
          <option value="supervisor">Supervisor</option>
          <option value="admin">Administrador</option>
        </select>
        {errors.role && (
          <span role="alert" className="biomed-form-error">
            {errors.role}
          </span>
        )}
      </label>

      <StatusToggle active={active} onChange={setActive} disabled={submitting} />

      {errors.general && (
        <p role="alert" className="biomed-form-error" data-testid="error-general">
          {errors.general}
        </p>
      )}

      <div className="biomed-form-actions">
        <button
          type="submit"
          disabled={submitting}
          data-testid="submit-user"
          className="biomed-btn biomed-btn--primary"
        >
          {submitting ? 'Guardando…' : editing ? 'Guardar cambios' : 'Crear usuario'}
        </button>
        <button
          type="button"
          onClick={onCancel}
          disabled={submitting}
          data-testid="cancel-user"
          className="biomed-btn"
        >
          Cancelar
        </button>
      </div>
    </form>
  );
}