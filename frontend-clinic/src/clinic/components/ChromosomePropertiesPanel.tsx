/**
 * Panel de propiedades del cromosoma seleccionado (ADR-0021 P1).
 * Read-only: clase, confianza, semáforo y medidas. Las acciones de
 * clasificación (Aceptar/Reclasificar) llegan en P2/P3.
 */
import type { Chromosome } from '../types/karyotype';
import { confidencePercent } from '../types/karyotype';

const SEMAPHORE_LABEL: Record<string, string> = {
  green: 'Verde — alta confianza',
  orange: 'Naranja — requiere revisión',
  red: 'Rojo — clasificación fallida',
};

export function ChromosomePropertiesPanel({ chromosome }: { chromosome: Chromosome | null }) {
  if (!chromosome) {
    return (
      <div className="karyo-props" data-testid="chromosome-props-empty">
        <strong>🧬 Cromosoma seleccionado</strong>
        <p className="karyo-props__hint">Seleccione un cromosoma en el visor.</p>
      </div>
    );
  }

  const m = chromosome.measures ?? {};
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
    </div>
  );
}
