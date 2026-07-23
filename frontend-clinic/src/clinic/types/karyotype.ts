/**
 * Tipos del visor de cariotipo (ADR-0021 P1, DD-KARYO-001).
 *
 * Espejo de backend-clinic KaryotypeSerializer/ChromosomeSerializer.
 * confidence_score llega como string (DecimalField de DRF), no number.
 */

export type Semaphore = 'green' | 'orange' | 'red';
export type ChromosomeResolution = 'AUTO' | 'PENDING' | 'RESOLVED';

/** Clases de cromosoma: '1'..'22', 'X', 'Y'. */
export const CHROMOSOME_SLOTS: string[] = [
  ...Array.from({ length: 22 }, (_, i) => String(i + 1)),
  'X',
  'Y',
];

export interface ChromosomeMeasures {
  length_um?: number;
  centromeric_index?: number;
  band_count?: number;
  quality?: string;
}

export interface Chromosome {
  id: string;
  predicted_class: string;
  position_index: number;
  confidence_score: string | null; // Decimal como string; null = fallo → rojo
  semaphore: Semaphore;
  resolution_status: ChromosomeResolution;
  xai_viewed: boolean;
  measures: ChromosomeMeasures;
  bbox: Record<string, number>;
  order: number;
}

export interface KaryotypeSummary {
  total: number;
  green: number;
  orange: number;
  red: number;
  unresolved_orange: number;
  is_blocked: boolean;
}

export interface Karyotype {
  id: string;
  sample_id: string;
  model_version: string;
  generated_at: string;
  summary: KaryotypeSummary;
  chromosomes: Chromosome[];
}

/** % legible desde el confidence_score string ("0.720" → "72%"). */
export function confidencePercent(score: string | null): string {
  if (score === null) return '—';
  return `${Math.round(parseFloat(score) * 100)}%`;
}
