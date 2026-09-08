/**
 * AppearanceSection — vista de la sección "Visualización" del bounded
 * context config (DD-ADMIN-002 P6, ADR-0014).
 *
 * Recurso único PATCH-able (mismo patrón que ProfileSection): 4 selects
 * (tema, densidad, idioma, tamaño de fuente), diff contra el último
 * estado confirmado antes de guardar.
 *
 * El HTML legado (`configuracion.html` líneas 1146-1177) mostraba 3
 * toggles de comportamiento del visor de cariotipo ("modo oscuro en el
 * visor", "mostrar confidence scores", "auto-validar pares") que NO
 * pertenecen al modelo real `AppearancePreference` (tema/densidad/
 * idioma/fuente de la UI admin, no del visor clínico) — se implementa
 * fiel al contrato del DD, no al mockup.
 *
 * DD §7.4 pide aplicar el tema con `document.documentElement.dataset
 * .theme`. Se aplica acá al cargar y al guardar (gesto funcional real,
 * consistente con el DD), pero el sistema de theming CSS completo
 * (hojas de estilo para `[data-theme="dark"]`) está fuera de alcance
 * de este DD — no se fabrica una apariencia oscura que no existe.
 */
import { FormEvent, useCallback, useEffect, useState } from 'react';
import { ConfigSection } from './ConfigSection';
import { AdminApiException } from '../types/adminUser';
import { adminConfigClient } from '../api/adminConfigClient';
import {
  AppearancePreference,
  AppearancePreferenceUpdate,
  Density,
  FontSize,
  Language,
  Theme,
} from '../types/config';

const THEME_OPTIONS: { value: Theme; label: string }[] = [
  { value: 'light', label: 'Claro' },
  { value: 'dark', label: 'Oscuro' },
  { value: 'auto', label: 'Automático (sistema)' },
];

const DENSITY_OPTIONS: { value: Density; label: string }[] = [
  { value: 'compact', label: 'Compacto' },
  { value: 'comfortable', label: 'Cómodo' },
  { value: 'spacious', label: 'Espacioso' },
];

const LANGUAGE_OPTIONS: { value: Language; label: string }[] = [
  { value: 'es', label: 'Español' },
  { value: 'en', label: 'English' },
  { value: 'pt', label: 'Português' },
];

const FONT_SIZE_OPTIONS: { value: FontSize; label: string }[] = [
  { value: 'sm', label: 'Pequeño' },
  { value: 'md', label: 'Mediano' },
  { value: 'lg', label: 'Grande' },
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

/** DD-ADMIN-002 §7.4. El CSS que consume `[data-theme]` está fuera de
 * alcance de este DD; el atributo se setea igual para que un futuro
 * sistema de theming pueda engancharse sin cambios en este componente. */
function applyAppearance(prefs: Pick<AppearancePreference, 'theme' | 'language'>) {
  document.documentElement.dataset.theme = prefs.theme;
  document.documentElement.lang = prefs.language;
}

type EditableFields = Omit<AppearancePreference, 'id' | 'updated_at'>;

function pickEditable(pref: AppearancePreference): EditableFields {
  const { id: _id, updated_at: _updatedAt, ...rest } = pref;
  return rest;
}

function AppearanceContent({ initial }: { initial: AppearancePreference }) {
  const [baseline, setBaseline] = useState<EditableFields>(() => pickEditable(initial));
  const [values, setValues] = useState<EditableFields>(() => pickEditable(initial));
  const [submitting, setSubmitting] = useState(false);
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<string | null>(null);

  useEffect(() => {
    applyAppearance(initial);
    // Solo al montar: refleja la preferencia ya confirmada por el backend.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleSubmit(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    setGeneralError(null);
    setSavedAt(null);

    const patch: AppearancePreferenceUpdate = {};
    (Object.keys(values) as (keyof EditableFields)[]).forEach((key) => {
      if (values[key] !== baseline[key]) {
        (patch as Record<string, unknown>)[key] = values[key];
      }
    });

    setSubmitting(true);
    try {
      if (Object.keys(patch).length > 0) {
        const updated = await adminConfigClient.updateAppearance(patch);
        const next = pickEditable(updated);
        setValues(next);
        setBaseline(next);
        applyAppearance(updated);
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
    <form onSubmit={handleSubmit} noValidate data-testid="appearance-form">
      <div className="biomed-form-section">
        <div className="biomed-form-section-title">Tema y visualización</div>
        <div className="biomed-form-grid">
          <div className="biomed-form-group">
            <label className="biomed-form-label" htmlFor="appearance-theme">
              Tema
            </label>
            <select
              id="appearance-theme"
              className="biomed-form-input"
              value={values.theme}
              onChange={(e) => setValues((prev) => ({ ...prev, theme: e.target.value as Theme }))}
              data-testid="appearance-input-theme"
            >
              {THEME_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
          <div className="biomed-form-group">
            <label className="biomed-form-label" htmlFor="appearance-density">
              Densidad
            </label>
            <select
              id="appearance-density"
              className="biomed-form-input"
              value={values.density}
              onChange={(e) => setValues((prev) => ({ ...prev, density: e.target.value as Density }))}
              data-testid="appearance-input-density"
            >
              {DENSITY_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
          <div className="biomed-form-group">
            <label className="biomed-form-label" htmlFor="appearance-language">
              Idioma
            </label>
            <select
              id="appearance-language"
              className="biomed-form-input"
              value={values.language}
              onChange={(e) => setValues((prev) => ({ ...prev, language: e.target.value as Language }))}
              data-testid="appearance-input-language"
            >
              {LANGUAGE_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
          <div className="biomed-form-group">
            <label className="biomed-form-label" htmlFor="appearance-font-size">
              Tamaño de fuente
            </label>
            <select
              id="appearance-font-size"
              className="biomed-form-input"
              value={values.font_size}
              onChange={(e) => setValues((prev) => ({ ...prev, font_size: e.target.value as FontSize }))}
              data-testid="appearance-input-font-size"
            >
              {FONT_SIZE_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {generalError && (
        <p role="alert" className="biomed-form-error" data-testid="appearance-form-error-general">
          {generalError}
        </p>
      )}
      {savedAt && !generalError && (
        <p className="biomed-form-hint" data-testid="appearance-form-saved-at" aria-live="polite">
          <i className="fas fa-check" aria-hidden="true" /> Preferencias guardadas a las {savedAt}
        </p>
      )}

      <div className="biomed-form-actions">
        <button
          type="button"
          className="biomed-btn biomed-btn--outline"
          onClick={handleCancel}
          disabled={submitting}
          data-testid="appearance-form-cancel"
        >
          Cancelar
        </button>
        <button
          type="submit"
          className="biomed-btn biomed-btn--primary"
          disabled={submitting}
          data-testid="appearance-form-submit"
        >
          <i className="fas fa-save" aria-hidden="true" />
          {submitting ? 'Guardando…' : 'Guardar cambios'}
        </button>
      </div>
    </form>
  );
}

export function AppearanceSection() {
  const loadAppearance = useCallback(() => adminConfigClient.getAppearance(), []);

  return (
    <ConfigSection<AppearancePreference>
      load={loadAppearance}
      testId="appearance-section"
      loadingText="Cargando visualización…"
    >
      {(prefs) => (
        <div data-testid="appearance-section-content">
          <AppearanceContent initial={prefs} />
        </div>
      )}
    </ConfigSection>
  );
}
