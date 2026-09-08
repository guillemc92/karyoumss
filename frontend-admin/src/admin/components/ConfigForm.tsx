/**
 * ConfigForm — formulario genérico para secciones de configuración
 * (DD-ADMIN-002 P1–P6).
 *
 * P1: lo usa ProfileSection con un único Zod schema (profileSchema).
 * P3+: ConfigSectionRouter recibirá un mapa section→schema y este mismo
 * componente renderizará la sección activa (ver DD §11.3).
 *
 * Responsabilidades:
 *  - Hidratar el state desde los datos iniciales.
 *  - Validar con Zod antes de submit (espejo de AdminProfileSerializer).
 *  - Mostrar errores por campo y banner general.
 *  - Rehidratar al cambiar `initial` (refresh desde el backend).
 */
import { FormEvent, useEffect, useState } from 'react';
import { ZodIssue, ZodType } from 'zod';

export interface ConfigFieldDef<T> {
  name: keyof T & string;
  label: string;
  type?: 'text' | 'email' | 'url' | 'tel';
  hint?: string;
  required?: boolean;
  maxLength?: number;
}

interface ConfigFormProps<T extends Record<string, unknown>, S> {
  initial: T;
  /** Zod schema del subconjunto de campos editables (input/output de PATCH). */
  schema: ZodType<S>;
  fields: ConfigFieldDef<T>[];
  onSubmit: (patch: Partial<T>) => Promise<void>;
  onCancel?: () => void;
  submitLabel?: string;
  testId?: string;
}

type FieldErrors = Record<string, string>;
type FormState = Record<string, string>;

function zodIssuesToFieldErrors(issues: ZodIssue[]): FieldErrors {
  const out: FieldErrors = {};
  for (const issue of issues) {
    const path = issue.path.join('.');
    if (!path) continue;
    // Mantener el primer mensaje por campo (UX)
    if (!out[path]) out[path] = issue.message;
  }
  return out;
}

export function ConfigForm<T extends Record<string, unknown>, S>({
  initial,
  schema,
  fields,
  onSubmit,
  onCancel,
  submitLabel = 'Guardar cambios',
  testId = 'config-form',
}: ConfigFormProps<T, S>) {
  const [values, setValues] = useState<FormState>(() => {
    const seed: FormState = {};
    for (const f of fields) {
      const v = initial[f.name];
      seed[f.name] = v == null ? '' : String(v);
    }
    return seed;
  });
  const [errors, setErrors] = useState<FieldErrors>({});
  const [submitting, setSubmitting] = useState(false);
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<string | null>(null);

  // Re-hidratar al cambiar `initial` (refresh tras PATCH, recarga manual, etc.)
  useEffect(() => {
    const next: FormState = {};
    for (const f of fields) {
      const v = initial[f.name];
      next[f.name] = v == null ? '' : String(v);
    }
    setValues(next);
    setErrors({});
    setGeneralError(null);
  }, [initial, fields]);

  async function handleSubmit(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    setGeneralError(null);
    setSavedAt(null);

    // Construimos el payload respetando la forma del schema (puede tener .default())
    // Los inputs del form siempre producen strings; trim para whitespace.
    const draft: Record<string, string> = {};
    for (const f of fields) {
      const raw = values[f.name];
      draft[f.name] = typeof raw === 'string' ? raw.trim() : '';
    }

    const parsed = schema.safeParse(draft);
    if (!parsed.success) {
      setErrors(zodIssuesToFieldErrors(parsed.error.issues));
      return;
    }
    setErrors({});

    // Diff contra `initial` para enviar solo lo que cambió
    const patch: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(parsed.data as Record<string, unknown>)) {
      const initialVal = initial[k as keyof T];
      if (initialVal !== v) patch[k] = v;
    }

    setSubmitting(true);
    try {
      // Si no hay cambios, no llamamos al backend — feedback al usuario
      if (Object.keys(patch).length === 0) {
        setSavedAt(new Date().toLocaleTimeString());
        return;
      }
      await onSubmit(patch as Partial<T>);
      setSavedAt(new Date().toLocaleTimeString());
    } catch (err) {
      setGeneralError(err instanceof Error ? err.message : 'Error al guardar');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form
      className="biomed-user-form"
      data-testid={testId}
      onSubmit={handleSubmit}
      noValidate
    >
      <div className="biomed-form-section">
        <div className="biomed-form-section-title">Datos</div>
        <div className="biomed-form-grid">
          {fields.map((field) => {
            const fieldError = errors[field.name];
            const inputId = `${testId}-input-${field.name}`;
            return (
              <div
                key={field.name}
                className="biomed-form-group"
                style={{ gridColumn: '1 / -1' }}
              >
                <label className="biomed-form-label" htmlFor={inputId}>
                  {field.label}
                  {field.required ? ' *' : ''}
                </label>
                <input
                  id={inputId}
                  type={field.type ?? 'text'}
                  className="biomed-form-input"
                  value={values[field.name] || ''}
                  maxLength={field.maxLength}
                  onChange={(e) =>
                    setValues((prev) => ({ ...prev, [field.name]: e.target.value }))
                  }
                  data-testid={`${testId}-input-${field.name}`}
                  required={field.required}
                />
                {field.hint && !fieldError && (
                  <small className="biomed-form-hint">{field.hint}</small>
                )}
                {fieldError && (
                  <span
                    role="alert"
                    className="biomed-form-error"
                    data-testid={`${testId}-error-${field.name}`}
                  >
                    {fieldError}
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {generalError && (
        <p
          role="alert"
          className="biomed-form-error"
          data-testid={`${testId}-error-general`}
        >
          {generalError}
        </p>
      )}

      {savedAt && !generalError && (
        <p
          className="biomed-form-hint"
          data-testid={`${testId}-saved-at`}
          aria-live="polite"
        >
          <i className="fas fa-check" aria-hidden="true" /> Guardado a las {savedAt}
        </p>
      )}

      <div className="biomed-form-actions">
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            disabled={submitting}
            data-testid={`${testId}-cancel`}
            className="biomed-btn biomed-btn--outline"
          >
            <i className="fas fa-times" aria-hidden="true" /> Cancelar
          </button>
        )}
        <button
          type="submit"
          disabled={submitting}
          data-testid={`${testId}-submit`}
          className="biomed-btn biomed-btn--primary"
        >
          <i className="fas fa-save" aria-hidden="true" />
          {submitting ? 'Guardando…' : submitLabel}
        </button>
      </div>
    </form>
  );
}
