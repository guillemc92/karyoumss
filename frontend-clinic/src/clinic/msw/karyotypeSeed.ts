/**
 * Builder del cariotipo mock para MSW (ADR-0021 P1, DD-KARYO-001 §6).
 *
 * - Caso genérico (muestras del seed original): 46 cromosomas, 3 naranjas
 *   (18/5/13 < 0.85), el resto verde.
 * - 3 casos MetaClass reconstruidos (docs/reference/metaclass-metafases-
 *   reconstruidas.sql): complemento cromosómico real con anomalías
 *   (46,XX normal / 47,XY,+21 Down / 47,XXY Klinefelter). El/los cromosoma(s)
 *   anómalo(s) llegan naranja (confianza baja) + marcados como anomalía, para
 *   ejercitar el flujo de revisión sobre una anomalía real.
 */
import type { Chromosome, Karyotype, KaryotypeSummary } from '../types/karyotype';

const ORANGE: Record<string, string> = { '18': '0.720', '5': '0.800', '13': '0.840' };

interface MetaCase {
  iscn: string;
  sex: 'XX' | 'XY' | 'XXY';
  trisomy: number[]; // pares autosómicos con 3ª copia
}

/** Metafases reconstruidas del esquema MetaClass (script.sql). */
export const META_CASES: Record<string, MetaCase> = {
  '000000aa-0000-0000-0000-000000000101': { iscn: '46,XX', sex: 'XX', trisomy: [] },
  '000000aa-0000-0000-0000-000000000102': { iscn: '47,XY,+21', sex: 'XY', trisomy: [21] },
  '000000aa-0000-0000-0000-000000000103': { iscn: '47,XXY', sex: 'XXY', trisomy: [] },
};

function semaphoreOf(score: string | null): Chromosome['semaphore'] {
  if (score === null) return 'red';
  return parseFloat(score) >= 0.85 ? 'green' : 'orange';
}

function makeChromosome(sampleId: string, label: string, copy: number, score: string | null, order: number, anomaly = false): Chromosome {
  const sem = semaphoreOf(score);
  return {
    id: `${sampleId}-chr-${label}-${copy}`,
    predicted_class: label,
    position_index: copy,
    confidence_score: score,
    semaphore: sem,
    resolution_status: sem === 'orange' ? 'PENDING' : 'AUTO',
    xai_viewed: false,
    is_anomaly: anomaly,
    is_active: true,
    measures: { length_um: 5.2, centromeric_index: 0.42, band_count: 380, quality: 'alta' },
    bbox: { x: 0, y: 0, w: 40, h: 96 },
    order,
  };
}

function summarize(chromosomes: Chromosome[]): KaryotypeSummary {
  const summary: KaryotypeSummary = {
    total: chromosomes.length,
    green: chromosomes.filter((c) => c.semaphore === 'green').length,
    orange: chromosomes.filter((c) => c.semaphore === 'orange').length,
    red: chromosomes.filter((c) => c.semaphore === 'red').length,
    unresolved_orange: chromosomes.filter((c) => c.semaphore === 'orange' && c.resolution_status !== 'RESOLVED').length,
    is_blocked: false,
  };
  summary.is_blocked = summary.unresolved_orange > 0 || summary.red > 0;
  return summary;
}

function wrap(sampleId: string, chromosomes: Chromosome[]): Karyotype {
  return {
    id: `${sampleId}-karyotype`,
    sample_id: sampleId,
    sample_status: 'READY',
    model_version: 'u-net-v2.1+efficientnet-b3-v1.4',
    generated_at: '2026-04-10T09:30:00Z',
    summary: summarize(chromosomes),
    chromosomes,
  };
}

/** Caso MetaClass: complemento real con trisomías / complemento sexual XXY. */
function buildMetaCase(sampleId: string, c: MetaCase): Karyotype {
  const chromosomes: Chromosome[] = [];
  let order = 0;
  for (let n = 1; n <= 22; n++) {
    const label = String(n);
    chromosomes.push(makeChromosome(sampleId, label, 0, '0.960', order++));
    chromosomes.push(makeChromosome(sampleId, label, 1, '0.960', order++));
    if (c.trisomy.includes(n)) {
      // 3ª copia = anomalía numérica: naranja (baja confianza) + marcada.
      chromosomes.push(makeChromosome(sampleId, label, 2, '0.820', order++, true));
    }
  }
  if (c.sex === 'XX') {
    chromosomes.push(makeChromosome(sampleId, 'X', 0, '0.940', order++));
    chromosomes.push(makeChromosome(sampleId, 'X', 1, '0.940', order++));
  } else if (c.sex === 'XY') {
    chromosomes.push(makeChromosome(sampleId, 'X', 0, '0.940', order++));
    chromosomes.push(makeChromosome(sampleId, 'Y', 0, '0.940', order++));
  } else { // XXY (Klinefelter): X extra = anomalía
    chromosomes.push(makeChromosome(sampleId, 'X', 0, '0.940', order++));
    chromosomes.push(makeChromosome(sampleId, 'X', 1, '0.820', order++, true));
    chromosomes.push(makeChromosome(sampleId, 'Y', 0, '0.940', order++));
  }
  return wrap(sampleId, chromosomes);
}

/** Caso genérico: 46 cromosomas, 3 naranjas puntuales (18/5/13). */
function buildGeneric(sampleId: string): Karyotype {
  const chromosomes: Chromosome[] = [];
  let order = 0;
  for (let n = 1; n <= 22; n++) {
    const label = String(n);
    const orangeScore = ORANGE[label] ?? null;
    chromosomes.push(makeChromosome(sampleId, label, 0, orangeScore ?? '0.960', order++));
    chromosomes.push(makeChromosome(sampleId, label, 1, '0.960', order++));
  }
  chromosomes.push(makeChromosome(sampleId, 'X', 0, '0.940', order++));
  chromosomes.push(makeChromosome(sampleId, 'Y', 0, '0.940', order++));
  return wrap(sampleId, chromosomes);
}

export function buildMockKaryotype(sampleId: string): Karyotype {
  const metaCase = META_CASES[sampleId];
  return metaCase ? buildMetaCase(sampleId, metaCase) : buildGeneric(sampleId);
}
