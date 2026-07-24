/**
 * Builder del cariotipo mock para MSW (ADR-0021 P1, DD-KARYO-001 §6).
 * Espejo del management command seed_karyotype del backend: 46 cromosomas,
 * 3 naranjas (18/5/13 < 0.85), el resto verde.
 */
import type { Chromosome, Karyotype, KaryotypeSummary } from '../types/karyotype';

const ORANGE: Record<string, string> = { '18': '0.720', '5': '0.800', '13': '0.840' };

function semaphoreOf(score: string | null): Chromosome['semaphore'] {
  if (score === null) return 'red';
  return parseFloat(score) >= 0.85 ? 'green' : 'orange';
}

export function buildMockKaryotype(sampleId: string): Karyotype {
  const chromosomes: Chromosome[] = [];
  let order = 0;

  const push = (label: string, copy: number, score: string | null) => {
    const sem = semaphoreOf(score);
    chromosomes.push({
      id: `${sampleId}-chr-${label}-${copy}`,
      predicted_class: label,
      position_index: copy,
      confidence_score: score,
      semaphore: sem,
      resolution_status: sem === 'orange' ? 'PENDING' : 'AUTO',
      xai_viewed: false,
      is_anomaly: false,
      is_active: true,
      measures: { length_um: 5.2, centromeric_index: 0.42, band_count: 380, quality: 'alta' },
      bbox: { x: 0, y: 0, w: 40, h: 96 },
      order: order++,
    });
  };

  for (let n = 1; n <= 22; n++) {
    const label = String(n);
    const orangeScore = ORANGE[label] ?? null;
    // Solo una copia baja de confianza (3 naranjas puntuales, no 3 pares).
    push(label, 0, orangeScore ?? '0.960');
    push(label, 1, '0.960');
  }
  push('X', 0, '0.940');
  push('Y', 0, '0.940');

  const summary: KaryotypeSummary = {
    total: chromosomes.length,
    green: chromosomes.filter((c) => c.semaphore === 'green').length,
    orange: chromosomes.filter((c) => c.semaphore === 'orange').length,
    red: chromosomes.filter((c) => c.semaphore === 'red').length,
    unresolved_orange: chromosomes.filter((c) => c.semaphore === 'orange' && c.resolution_status !== 'RESOLVED').length,
    is_blocked: false,
  };
  summary.is_blocked = summary.unresolved_orange > 0 || summary.red > 0;

  return {
    id: `${sampleId}-karyotype`,
    sample_id: sampleId,
    sample_status: 'READY', // el handler lo sobreescribe con el estado real de la muestra
    model_version: 'u-net-v2.1+efficientnet-b3-v1.4',
    generated_at: '2026-04-10T09:30:00Z',
    summary,
    chromosomes,
  };
}
