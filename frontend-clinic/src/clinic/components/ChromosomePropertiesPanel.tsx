/**
 * Panel de propiedades del cromosoma seleccionado.
 * P1: read-only (clase, confianza, semáforo, medidas).
 * P2: acciones (Ver XAI / Aceptar / Marcar anomalía) — solo si se pasan los
 * callbacks. Sin ellos, el panel sigue siendo read-only (compat P1).
 */
import type { Chromosome } from '../types/karyotype';
import { CHROMOSOME_SLOTS, confidencePercent } from '../types/karyotype';

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
  // --- P3 (corrección manual, DD-KARYO-003) ---
  onReclassify?: (c: Chromosome, targetClass: string) => void;
  onSplit?: (c: Chromosome) => void;
  onResolveCross?: (c: Chromosome) => void;
  onJoinPick?: (c: Chromosome) => void;
  onJoinConfirm?: (c: Chromosome) => void;
  /** Primer fragmento marcado para unir (lo gestiona la página). */
  joinPick?: { id: string; label: string } | null;
}

export function ChromosomePropertiesPanel({
  chromosome,
  onViewXai,
  onResolve,
  onMarkAnomaly,
  busy = false,
  onReclassify,
  onSplit,
  onResolveCross,
  onJoinPick,
  onJoinConfirm,
  joinPick = null,
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
  const showP3 = Boolean(onReclassify || onSplit || onResolveCross || onJoinPick);
  const isOrange = chromosome.semaphore === 'orange';
  const isResolved = chromosome.resolution_status === 'RESOLVED';
  const isJoinPicked = joinPick?.id === chromosome.id;
  const canJoinConfirm = Boolean(joinPick) && !isJoinPicked;

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

      {showP3 && (
        <div className="karyo-actions" data-testid="chromosome-p3-actions">
          <strong>✏️ Corrección manual</strong>

          {onReclassify && (
            <label className="karyo-reclassify">
              <span>Mover a par</span>
              <select
                data-testid="reclassify-select"
                value={chromosome.predicted_class}
                disabled={busy}
                onChange={(e) => onReclassify(chromosome, e.target.value)}
              >
                {CHROMOSOME_SLOTS.map((slot) => (
                  <option key={slot} value={slot}>{slot}</option>
                ))}
              </select>
            </label>
          )}

          <div className="karyo-actions__row">
            {onSplit && (
              <button type="button" className="btn-outline" onClick={() => onSplit(chromosome)} disabled={busy} data-testid="action-split">
                ✂️ Separar (touching)
              </button>
            )}
            {onResolveCross && (
              <button type="button" className="btn-outline" onClick={() => onResolveCross(chromosome)} disabled={busy} data-testid="action-cross">
                ✳️ Resolver cruce
              </button>
            )}
            {onJoinConfirm && canJoinConfirm && (
              <button type="button" className="btn-primary" onClick={() => onJoinConfirm(chromosome)} disabled={busy} data-testid="action-join-confirm">
                🔗 Unir con par {joinPick?.label}
              </button>
            )}
            {onJoinPick && !canJoinConfirm && (
              <button
                type="button"
                className={isJoinPicked ? 'btn-primary' : 'btn-outline'}
                onClick={() => onJoinPick(chromosome)}
                disabled={busy}
                data-testid="action-join-pick"
              >
                {isJoinPicked ? '🔗 Marcado — elija el otro fragmento' : '🔗 Unir: marcar este fragmento'}
              </button>
            )}
          </div>
          <p className="karyo-props__hint" data-testid="reclassify-hint">
            Arrastre el cromosoma a otro par en el visor, o use "Mover a par" (override manual, BR-003).
          </p>
        </div>
      )}
    </div>
  );
}
