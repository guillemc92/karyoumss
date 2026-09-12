/**
 * KaryotypeViewer — grid read-only de cromosomas con semaforización (ADR-0021 P1).
 *
 * Render con SVG/CSS (no Konva todavía — ADR-0021 D4; Konva llega en P3 con
 * el drag & drop). Cada slot (1–22, X, Y) agrupa sus cromosomas; cada
 * cromosoma es un rectángulo SVG coloreado por su semáforo. Click selecciona.
 */
import type { Chromosome } from '../types/karyotype';
import { CHROMOSOME_SLOTS } from '../types/karyotype';

const SEMAPHORE_FILL: Record<string, string> = {
  green: '#1e8868',
  orange: '#d45100',
  red: '#E30613',
};

interface KaryotypeViewerProps {
  chromosomes: Chromosome[];
  selectedId: string | null;
  onSelect: (chromosome: Chromosome) => void;
}

function ChromosomeShape({
  chromosome,
  selected,
  onSelect,
}: {
  chromosome: Chromosome;
  selected: boolean;
  onSelect: (c: Chromosome) => void;
}) {
  const fill = SEMAPHORE_FILL[chromosome.semaphore];
  return (
    <button
      type="button"
      className={`karyo-chromo${selected ? ' karyo-chromo--selected' : ''}`}
      data-testid={`chromosome-${chromosome.id}`}
      data-semaphore={chromosome.semaphore}
      aria-pressed={selected}
      aria-label={`Cromosoma ${chromosome.predicted_class}, semáforo ${chromosome.semaphore}`}
      onClick={() => onSelect(chromosome)}
    >
      <svg viewBox="0 0 40 96" width="26" height="62" aria-hidden="true">
        {/* Silueta simplificada del cromosoma (2 brazos + centrómero). */}
        <rect x="14" y="2" width="12" height="40" rx="5" fill={fill} />
        <rect x="14" y="54" width="12" height="40" rx="5" fill={fill} />
        <rect x="12" y="42" width="16" height="12" rx="2" fill={fill} opacity="0.7" />
      </svg>
    </button>
  );
}

export function KaryotypeViewer({ chromosomes, selectedId, onSelect }: KaryotypeViewerProps) {
  // Agrupa por clase para el layout del cariograma (1–22, X, Y).
  const byClass = new Map<string, Chromosome[]>();
  for (const c of chromosomes) {
    const list = byClass.get(c.predicted_class) ?? [];
    list.push(c);
    byClass.set(c.predicted_class, list);
  }

  return (
    <div className="karyo-grid" data-testid="karyotype-viewer">
      {CHROMOSOME_SLOTS.map((slot) => {
        const group = (byClass.get(slot) ?? []).slice().sort((a, b) => a.position_index - b.position_index);
        return (
          <div className="karyo-slot" key={slot} data-testid={`karyo-slot-${slot}`}>
            <div className="karyo-slot__pair">
              {group.map((chromo) => (
                <ChromosomeShape
                  key={chromo.id}
                  chromosome={chromo}
                  selected={chromo.id === selectedId}
                  onSelect={onSelect}
                />
              ))}
            </div>
            <div className="karyo-slot__label">{slot}</div>
          </div>
        );
      })}
    </div>
  );
}
