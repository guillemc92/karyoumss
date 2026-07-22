/**
 * NotificationsSection — vista de la sección "Notificaciones" del
 * bounded context config (DD-ADMIN-002 P4, ADR-0014).
 *
 * Recurso único PATCH-able (como ProfileSection), pero con una matriz
 * canal (email/in-app) × categoría en vez de un formulario plano — por
 * eso no reutiliza ConfigForm. Todos los cambios se juntan y se
 * confirman con un único "Guardar cambios" (diff contra el último
 * estado confirmado, igual que ModelsSection).
 */
import { FormEvent, useCallback, useState } from 'react';
import { ConfigSection } from './ConfigSection';
import { StatusToggle } from './StatusToggle';
import { AdminApiException } from '../types/adminUser';
import { adminConfigClient } from '../api/adminConfigClient';
import { NotificationPreference, NotificationPreferenceUpdate } from '../types/config';

type EditableFields = Omit<NotificationPreference, 'id' | 'updated_at'>;

function pickEditable(pref: NotificationPreference): EditableFields {
  const { id: _id, updated_at: _updatedAt, ...rest } = pref;
  return rest;
}

interface CategoryDef {
  key: string;
  label: string;
  emailField: keyof EditableFields;
  inappField: keyof EditableFields;
}

const CATEGORIES: CategoryDef[] = [
  {
    key: 'review_pending',
    label: 'Revisión pendiente',
    emailField: 'email_review_pending',
    inappField: 'inapp_review_pending',
  },
  {
    key: 'supervisor_validation',
    label: 'Validación de supervisor',
    emailField: 'email_supervisor_validation',
    inappField: 'inapp_supervisor_validation',
  },
  {
    key: 'system_errors',
    label: 'Errores del sistema',
    emailField: 'email_system_errors',
    inappField: 'inapp_system_errors',
  },
  {
    key: 'training_completed',
    label: 'Reentrenamiento completado',
    emailField: 'email_training_completed',
    inappField: 'inapp_training_completed',
  },
];

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

/** "HH:MM:SS" (API) ↔ "HH:MM" (<input type="time">). */
function toTimeInputValue(hhmmss: string): string {
  return hhmmss.slice(0, 5);
}
function fromTimeInputValue(hhmm: string): string {
  return `${hhmm}:00`;
}

function NotificationsContent({ initial }: { initial: NotificationPreference }) {
  const [baseline, setBaseline] = useState<EditableFields>(() => pickEditable(initial));
  const [values, setValues] = useState<EditableFields>(() => pickEditable(initial));
  const [submitting, setSubmitting] = useState(false);
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<string | null>(null);

  function toggleField(field: keyof EditableFields) {
    setValues((prev) => ({ ...prev, [field]: !prev[field] }));
  }

  async function handleSubmit(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    setGeneralError(null);
    setSavedAt(null);

    const patch: NotificationPreferenceUpdate = {};
    (Object.keys(values) as (keyof EditableFields)[]).forEach((key) => {
      if (values[key] !== baseline[key]) {
        (patch as Record<string, unknown>)[key] = values[key];
      }
    });

    setSubmitting(true);
    try {
      if (Object.keys(patch).length > 0) {
        const updated = await adminConfigClient.updateNotifications(patch);
        const next = pickEditable(updated);
        setValues(next);
        setBaseline(next);
      }
      setSavedAt(new Date().toLocaleTimeString());
    } catch (err) {
      setGeneralError(errorMessageFromUnknown(err));
    } finally {
      setSubmitting(false);
    }
  }

  function handleCancel() {
    setValues(baseline);
    setGeneralError(null);
    setSavedAt(null);
  }

  return (
    <form onSubmit={handleSubmit} noValidate data-testid="notifications-form">
      <div className="biomed-form-section">
        <div className="biomed-form-section-title">Preferencias de notificación</div>
        <div style={{ overflowX: 'auto' }}>
          <table className="biomed-table" data-testid="notifications-matrix" style={{ width: '100%' }}>
            <thead>
              <tr>
                <th style={{ textAlign: 'left' }}>Categoría</th>
                <th>Email</th>
                <th>In-app</th>
              </tr>
            </thead>
            <tbody>
              {CATEGORIES.map((cat) => (
                <tr key={cat.key}>
                  <td>{cat.label}</td>
                  <td style={{ textAlign: 'center' }} data-testid={`notifications-cell-email-${cat.key}`}>
                    <StatusToggle
                      active={values[cat.emailField]}
                      onChange={() => toggleField(cat.emailField)}
                      disabled={submitting}
                    />
                  </td>
                  <td style={{ textAlign: 'center' }} data-testid={`notifications-cell-inapp-${cat.key}`}>
                    <StatusToggle
                      active={values[cat.inappField]}
                      onChange={() => toggleField(cat.inappField)}
                      disabled={submitting}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="biomed-form-section">
        <div className="biomed-form-section-title">Horario silencioso</div>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: values.quiet_hours_enabled ? 16 : 0,
          }}
          data-testid="notifications-cell-quiet-hours-enabled"
        >
          <div>
            <strong>No notificar fuera de horario</strong>
            <p className="biomed-history-item__meta" style={{ margin: 0 }}>
              Se aplica a email e in-app por igual
            </p>
          </div>
          <StatusToggle
            active={values.quiet_hours_enabled}
            onChange={() => toggleField('quiet_hours_enabled')}
            disabled={submitting}
          />
        </div>
        {values.quiet_hours_enabled && (
          <div className="biomed-form-grid">
            <div className="biomed-form-group">
              <label className="biomed-form-label" htmlFor="notifications-quiet-start">
                Desde
              </label>
              <input
                id="notifications-quiet-start"
                type="time"
                className="biomed-form-input"
                value={toTimeInputValue(values.quiet_hours_start)}
                onChange={(e) =>
                  setValues((prev) => ({ ...prev, quiet_hours_start: fromTimeInputValue(e.target.value) }))
                }
                data-testid="notifications-quiet-start"
              />
            </div>
            <div className="biomed-form-group">
              <label className="biomed-form-label" htmlFor="notifications-quiet-end">
                Hasta
              </label>
              <input
                id="notifications-quiet-end"
                type="time"
                className="biomed-form-input"
                value={toTimeInputValue(values.quiet_hours_end)}
                onChange={(e) =>
                  setValues((prev) => ({ ...prev, quiet_hours_end: fromTimeInputValue(e.target.value) }))
                }
                data-testid="notifications-quiet-end"
              />
            </div>
          </div>
        )}
      </div>

      {generalError && (
        <p role="alert" className="biomed-form-error" data-testid="notifications-form-error-general">
          {generalError}
        </p>
      )}
      {savedAt && !generalError && (
        <p className="biomed-form-hint" data-testid="notifications-form-saved-at" aria-live="polite">
          <i className="fas fa-check" aria-hidden="true" /> Preferencias guardadas a las {savedAt}
        </p>
      )}

      <div className="biomed-form-actions">
        <button
          type="button"
          className="biomed-btn biomed-btn--outline"
          onClick={handleCancel}
          disabled={submitting}
          data-testid="notifications-form-cancel"
        >
          Cancelar
        </button>
        <button
          type="submit"
          className="biomed-btn biomed-btn--primary"
          disabled={submitting}
          data-testid="notifications-form-submit"
        >
          <i className="fas fa-save" aria-hidden="true" />
          {submitting ? 'Guardando…' : 'Guardar cambios'}
        </button>
      </div>
    </form>
  );
}

export function NotificationsSection() {
  const loadNotifications = useCallback(() => adminConfigClient.getNotifications(), []);

  return (
    <ConfigSection<NotificationPreference>
      load={loadNotifications}
      testId="notifications-section"
      loadingText="Cargando notificaciones…"
    >
      {(prefs) => (
        <div data-testid="notifications-section-content">
          <NotificationsContent initial={prefs} />
        </div>
      )}
    </ConfigSection>
  );
}
