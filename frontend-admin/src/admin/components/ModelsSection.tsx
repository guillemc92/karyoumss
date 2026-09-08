/**
 * ModelsSection — vista de la sección "Modelo IA" del bounded context
 * config (DD-ADMIN-002 P3, ADR-0014).
 *
 * A diferencia de ProfileSection (recurso único PATCH-able) y
 * SecuritySection (acciones independientes), acá conviven:
 *  - Un recurso editable por lote (`ModelConfig`, singleton): todos los
 *    cambios de esta sección se juntan y se confirman con un único botón
 *    "Guardar configuración", igual que el HTML original.
 *  - Datos de solo lectura (`ModelMetric`, append-only): última métrica +
 *    histórico para el sparkline. Se cargan aparte y su falla no bloquea
 *    la edición de la configuración (degradación elegante, RN-07).
 *
 * Los dos modelos reales del pipeline son U-Net (segmentación) +
 * EfficientNet-B3 (clasificación) — nunca Mask R-CNN/ResNet50 (AGENTS §9).
 * La sección "Entrenamiento y validación" del HTML legado mostraba datos
 * ficticios (incluyendo "ResNet-152 + Attention", contradiciendo la
 * arquitectura real) — acá se deja como placeholder deshabilitado, tal
 * como especifica DD-ADMIN-002 §4.6 punto 4 ("no entra en este DD").
 */
import { FormEvent, useCallback, useEffect, useState } from 'react';
import { ConfigSection } from './ConfigSection';
import { StatusToggle } from './StatusToggle';
import { AdminApiException } from '../types/adminUser';
import { adminConfigClient } from '../api/adminConfigClient';
import {
  AnalysisMode,
  LogLevel,
  ModelConfig,
  ModelConfigUpdate,
  ModelMetric,
} from '../types/config';

const ANALYSIS_MODE_OPTIONS: { value: AnalysisMode; label: string }[] = [
  { value: 'fast', label: 'Rápido (prioriza velocidad)' },
  { value: 'balanced', label: 'Balanceado' },
  { value: 'accurate', label: 'Precisión máxima (más lento)' },
];

const LOG_LEVEL_OPTIONS: { value: LogLevel; label: string }[] = [
  { value: 'WARNING', label: 'Mínimo' },
  { value: 'INFO', label: 'Normal' },
  { value: 'DEBUG', label: 'Detallado' },
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

function pct(decimalStr: string): string {
  return `${(parseFloat(decimalStr) * 100).toFixed(1)}%`;
}

/** Sparkline SVG inline (DD §4.6: "sin lib de charting, ~30 LOC"). */
function Sparkline({ values }: { values: number[] }) {
  const width = 240;
  const height = 48;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const points = values.map((v, i) => {
    const x = (i / (values.length - 1)) * width;
    const y = height - ((v - min) / range) * height;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const [lastX, lastY] = points[points.length - 1].split(',');
  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      data-testid="models-sparkline"
      role="img"
      aria-label="Tendencia de precisión"
    >
      <polyline points={points.join(' ')} fill="none" stroke="#003770" strokeWidth={2} />
      <circle cx={lastX} cy={lastY} r={3} fill="#003770" />
    </svg>
  );
}

interface ModelsContentProps {
  initialConfig: ModelConfig;
}

function ModelsContent({ initialConfig }: ModelsContentProps) {
  const [config, setConfig] = useState(initialConfig);
  const [unetEnabled, setUnetEnabled] = useState(initialConfig.unet_enabled);
  const [classifierEnabled, setClassifierEnabled] = useState(initialConfig.classifier_enabled);
  const [confidence, setConfidence] = useState(() => Math.round(parseFloat(initialConfig.confidence_threshold) * 100));
  const [sensitivity, setSensitivity] = useState(() => Math.round(parseFloat(initialConfig.detection_sensitivity) * 100));
  const [analysisMode, setAnalysisMode] = useState<AnalysisMode>(initialConfig.analysis_mode);
  const [logLevel, setLogLevel] = useState<LogLevel>(initialConfig.log_level);
  const [submitting, setSubmitting] = useState(false);
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<string | null>(null);

  const [metrics, setMetrics] = useState<ModelMetric[]>([]);
  const [latest, setLatest] = useState<ModelMetric | undefined>(undefined);
  const [metricsError, setMetricsError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [list, last] = await Promise.all([
          adminConfigClient.getMetrics(30),
          adminConfigClient.getLatestMetric(),
        ]);
        if (!cancelled) {
          setMetrics(list);
          setLatest(last);
        }
      } catch (err) {
        if (!cancelled) setMetricsError(errorMessageFromUnknown(err));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  function hydrateFrom(source: ModelConfig) {
    setUnetEnabled(source.unet_enabled);
    setClassifierEnabled(source.classifier_enabled);
    setConfidence(Math.round(parseFloat(source.confidence_threshold) * 100));
    setSensitivity(Math.round(parseFloat(source.detection_sensitivity) * 100));
    setAnalysisMode(source.analysis_mode);
    setLogLevel(source.log_level);
  }

  async function handleSubmit(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    setGeneralError(null);
    setSavedAt(null);

    const patch: ModelConfigUpdate = {};
    if (unetEnabled !== config.unet_enabled) patch.unet_enabled = unetEnabled;
    if (classifierEnabled !== config.classifier_enabled) patch.classifier_enabled = classifierEnabled;
    const confidenceDecimal = confidence / 100;
    if (confidenceDecimal.toFixed(3) !== parseFloat(config.confidence_threshold).toFixed(3)) {
      patch.confidence_threshold = confidenceDecimal;
    }
    const sensitivityDecimal = sensitivity / 100;
    if (sensitivityDecimal.toFixed(3) !== parseFloat(config.detection_sensitivity).toFixed(3)) {
      patch.detection_sensitivity = sensitivityDecimal;
    }
    if (analysisMode !== config.analysis_mode) patch.analysis_mode = analysisMode;
    if (logLevel !== config.log_level) patch.log_level = logLevel;

    setSubmitting(true);
    try {
      if (Object.keys(patch).length > 0) {
        const updated = await adminConfigClient.updateActiveModel(patch);
        setConfig(updated);
        hydrateFrom(updated);
      }
      setSavedAt(new Date().toLocaleTimeString());
    } catch (err) {
      setGeneralError(errorMessageFromUnknown(err));
    } finally {
      setSubmitting(false);
    }
  }

  function handleReset() {
    hydrateFrom(config);
    setGeneralError(null);
    setSavedAt(null);
  }

  return (
    <div data-testid="models-section-content">
      {config.compliance_warning && (
        <p
          role="alert"
          className="biomed-banner biomed-banner--warning"
          data-testid="models-compliance-banner"
        >
          <i className="fas fa-triangle-exclamation" aria-hidden="true" />
          El umbral de confianza está por debajo de 0.85 (RN-02). El sistema
          seguirá operando pero los reportes requerirán validación manual
          adicional.
        </p>
      )}

      <form onSubmit={handleSubmit} noValidate data-testid="models-form">
        <div className="biomed-form-section">
          <div className="biomed-form-section-title">Modelos disponibles</div>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
              gap: 16,
            }}
          >
            <div className="biomed-history-item" data-testid="models-card-unet" style={{ padding: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <strong>U-Net (segmentación)</strong>
                <StatusToggle active={unetEnabled} onChange={setUnetEnabled} disabled={submitting} />
              </div>
              <span className="biomed-history-item__meta">Versión {config.unet_version}</span>
            </div>
            <div className="biomed-history-item" data-testid="models-card-classifier" style={{ padding: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <strong>EfficientNet-B3 (clasificación)</strong>
                <StatusToggle active={classifierEnabled} onChange={setClassifierEnabled} disabled={submitting} />
              </div>
              <span className="biomed-history-item__meta">Versión {config.classifier_version}</span>
            </div>
          </div>
        </div>

        <div className="biomed-form-section">
          <div className="biomed-form-section-title">Parámetros de clasificación</div>
          <div className="biomed-form-grid">
            <div className="biomed-form-group">
              <label className="biomed-form-label" htmlFor="models-confidence">
                Umbral de confianza mínima
              </label>
              <input
                id="models-confidence"
                type="range"
                min={0}
                max={100}
                value={confidence}
                onChange={(e) => setConfidence(Number(e.target.value))}
                data-testid="models-input-confidence"
              />
              <small className="biomed-form-hint" data-testid="models-confidence-value">
                {confidence}%
              </small>
            </div>
            <div className="biomed-form-group">
              <label className="biomed-form-label" htmlFor="models-sensitivity">
                Sensibilidad de detección
              </label>
              <input
                id="models-sensitivity"
                type="range"
                min={0}
                max={100}
                value={sensitivity}
                onChange={(e) => setSensitivity(Number(e.target.value))}
                data-testid="models-input-sensitivity"
              />
              <small className="biomed-form-hint" data-testid="models-sensitivity-value">
                {sensitivity}%
              </small>
            </div>
            <div className="biomed-form-group">
              <label className="biomed-form-label" htmlFor="models-analysis-mode">
                Modo de análisis
              </label>
              <select
                id="models-analysis-mode"
                className="biomed-form-input"
                value={analysisMode}
                onChange={(e) => setAnalysisMode(e.target.value as AnalysisMode)}
                data-testid="models-input-analysis-mode"
              >
                {ANALYSIS_MODE_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="biomed-form-group">
              <label className="biomed-form-label" htmlFor="models-log-level">
                Nivel de logging
              </label>
              <select
                id="models-log-level"
                className="biomed-form-input"
                value={logLevel}
                onChange={(e) => setLogLevel(e.target.value as LogLevel)}
                data-testid="models-input-log-level"
              >
                {LOG_LEVEL_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        <div className="biomed-form-section">
          <div className="biomed-form-section-title">Métricas de precisión</div>
          {metricsError && (
            <p role="alert" className="biomed-form-error" data-testid="models-metrics-error">
              {metricsError}
            </p>
          )}
          {!metricsError && !latest && (
            <p className="biomed-form-hint" data-testid="models-metrics-empty">
              Sin snapshots de métricas todavía.
            </p>
          )}
          {latest && (
            <>
              <div className="biomed-form-grid">
                <div>
                  <span className="biomed-history-item__meta">Precisión global</span>
                  <br />
                  <strong data-testid="models-metric-precision">{pct(latest.precision_overall)}</strong>
                </div>
                <div>
                  <span className="biomed-history-item__meta">Sensibilidad</span>
                  <br />
                  <strong data-testid="models-metric-recall">{pct(latest.recall_overall)}</strong>
                </div>
                <div>
                  <span className="biomed-history-item__meta">F1-Score</span>
                  <br />
                  <strong data-testid="models-metric-f1">{parseFloat(latest.f1_overall).toFixed(3)}</strong>
                </div>
                <div>
                  <span className="biomed-history-item__meta">Muestras evaluadas</span>
                  <br />
                  <strong data-testid="models-metric-samples">
                    {latest.samples_evaluated.toLocaleString('es-BO')}
                  </strong>
                </div>
              </div>
              {metrics.length >= 2 && (
                <div style={{ marginTop: 12 }}>
                  <span className="biomed-history-item__meta">
                    Tendencia de precisión (últimos {metrics.length} snapshots)
                  </span>
                  <Sparkline values={metrics.slice().reverse().map((m) => parseFloat(m.precision_overall))} />
                </div>
              )}
            </>
          )}
        </div>

        <div className="biomed-form-section">
          <div className="biomed-form-section-title">Entrenamiento y validación</div>
          <p className="biomed-form-hint">
            El pipeline de reentrenamiento se gestiona fuera de este panel (fuera de alcance de DD-ADMIN-002 P3).
          </p>
          <button
            type="button"
            className="biomed-btn biomed-btn--outline"
            disabled
            data-testid="models-retrain-cta"
          >
            <i className="fas fa-rotate" aria-hidden="true" /> Iniciar reentrenamiento
          </button>
        </div>

        <div className="biomed-form-section">
          <div className="biomed-form-section-title">Rendimiento del sistema</div>
          {latest ? (
            <div className="biomed-form-grid">
              <div>
                <span className="biomed-history-item__meta">Latencia p50</span>
                <br />
                <strong data-testid="models-latency-p50">{latest.latency_p50_ms} ms</strong>
              </div>
              <div>
                <span className="biomed-history-item__meta">Latencia p95</span>
                <br />
                <strong data-testid="models-latency-p95">{latest.latency_p95_ms} ms</strong>
              </div>
              <div>
                <span className="biomed-history-item__meta">Latencia p99</span>
                <br />
                <strong data-testid="models-latency-p99">{latest.latency_p99_ms} ms</strong>
              </div>
            </div>
          ) : (
            <p className="biomed-form-hint">Sin datos de rendimiento todavía.</p>
          )}
        </div>

        {generalError && (
          <p role="alert" className="biomed-form-error" data-testid="models-form-error-general">
            {generalError}
          </p>
        )}
        {savedAt && !generalError && (
          <p className="biomed-form-hint" data-testid="models-form-saved-at" aria-live="polite">
            <i className="fas fa-check" aria-hidden="true" /> Configuración guardada a las {savedAt}
          </p>
        )}

        <div className="biomed-form-actions">
          <button
            type="button"
            className="biomed-btn biomed-btn--outline"
            onClick={handleReset}
            disabled={submitting}
            data-testid="models-form-reset"
          >
            Restaurar valores por defecto
          </button>
          <button
            type="submit"
            className="biomed-btn biomed-btn--primary"
            disabled={submitting}
            data-testid="models-form-submit"
          >
            <i className="fas fa-save" aria-hidden="true" />
            {submitting ? 'Guardando…' : 'Guardar configuración'}
          </button>
        </div>
      </form>
    </div>
  );
}

export function ModelsSection() {
  const loadConfig = useCallback(() => adminConfigClient.getActiveModel(), []);

  return (
    <ConfigSection<ModelConfig> load={loadConfig} testId="models-section" loadingText="Cargando modelo IA…">
      {(config) => <ModelsContent initialConfig={config} />}
    </ConfigSection>
  );
}
