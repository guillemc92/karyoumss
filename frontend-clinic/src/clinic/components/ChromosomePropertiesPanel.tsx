/**
 * Panel de propiedades del cromosoma seleccionado.
 * P1: read-only (clase, confianza, semáforo, medidas).
 * P2: acciones (Ver XAI / Aceptar / Marcar anomalía) — solo si se pasan los
 * callbacks. Sin ellos, el panel sigue siendo read-only (compat P1).
 */
import type { Chromosome } from '../types/karyotype';
import { confidencePercent } from '../types/karyotype';

const SEMAPHORE_LABEL: Record<string, string> = {
  green: 'Verde — alta confianza',
  orange: 'Naranja — requiere revisión',
  red: 'Rojo — clasificación fallida',
};

interface Actions {
  onViewXai?: (c: Chromosome) => void;
  onResolve?: (c: Chromosome) => void;
  onMarkAnomaly?: (c: Chromosome) => void;
  busy?: boolean;
}

export function ChromosomePropertiesPanel({
  chromosome,
  onViewXai,
  onResolve,
  onMarkAnomaly,
  busy = false,
}: { chromosome: Chromosome | null } & Actions) {
  if (!chromosome) {
    return (
      <div className="karyo-props" data-testid="chromosome-props-empty">
        <strong>🧬 Cromosoma seleccionado</strong>
        <p className="karyo-props__hint">Seleccione un cromosoma en el visor.</p>
      </div>
    );
  }

  const m = chromosome.measures ?? {};
  const showActions = Boolean(onViewXai || onResolve || onMarkAnomaly);
  const isOrange = chromosome.semaphore === 'orange';
  const isResolved = chromosome.resolution_status === 'RESOLVED';

  return (
    <div className="karyo-props" data-testid="chromosome-props">
      <strong>🧬 Cromosoma seleccionado</strong>
      <p className="karyo-props__title" data-testid="props-class">
        Par {chromosome.predicted_class}
        <span className={`karyo-dot karyo-dot--${chromosome.semaphore}`} aria-hidden="true" />
        <span data-testid="props-confidence">{confidencePercent(chromosome.confidence_score)}</span>
      </p>
      <p className="karyo-props__semaphore" data-testid="props-semaphore">
        {SEMAPHORE_LABEL[chromosome.semaphore]}
        {isResolved && ' · ✅ Resuelto'}
        {chromosome.is_anomaly && ' · 🏷️ Anomalía (M)'}
      </p>

      <div className="karyo-measures">
        <strong>📏 Medidas</strong>
        <div className="karyo-measures__grid">
          <div><span>Longitud</span><br /><b data-testid="props-length">{m.length_um ?? '—'} µm</b></div>
          <div><span>Índice centromérico</span><br /><b>{m.centromeric_index ?? '—'}</b></div>
          <div><span>Bandas visibles</span><br /><b>{m.band_count ?? '—'}</b></div>
          <div><span>Calidad</span><br /><b>{m.quality ?? '—'}</b></div>
        </div>
      </div>

      {showActions && (
        <div className="karyo-actions" data-testid="chromosome-actions">
          <strong>🔄 Acciones</strong>
          <div className="karyo-actions__row">
            {onViewXai && isOrange && !isResolved && (
              <button
                type="button"
                className="btn-outline"
                onClick={() => onViewXai(chromosome)}
                disabled={busy}
                data-testid="action-xai"
              >
                🔍 Ver explicabilidad (XAI)
              </button>
            )}
            {onResolve && isOrange && !isResolved && (
              <button
                type="button"
                className="btn-primary"
                onClick={() => onResolve(chromosome)}
                disabled={busy || !chromosome.xai_viewed}
                title={chromosome.xai_viewed ? '' : 'Debe consultar la explicabilidad (XAI) antes de aceptar'}
                data-testid="action-resolve"
              >
                ✓ Aceptar
              </button>
            )}
            {onMarkAnomaly && !chromosome.is_anomaly && (
              <button
                type="button"
                className="btn-outline"
                onClick={() => onMarkAnomaly(chromosome)}
                disabled={busy}
                data-testid="action-anomaly"
              >
                🏷️ Marcar anomalía (M)
              </button>
            )}
          </div>
          {onResolve && isOrange && !isResolved && !chromosome.xai_viewed && (
            <p className="karyo-props__hint" data-testid="xai-required-hint">
              Debe consultar la explicabilidad (XAI) antes de aceptar (BR-004).
            </p>
          )}
        </div>
      )}
    </div>
  );
}
