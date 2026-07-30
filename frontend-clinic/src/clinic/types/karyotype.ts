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
  is_anomaly: boolean;
  is_active: boolean; // P3: JOIN desactiva el fragmento absorbido (DD-KARYO-003)
  measures: ChromosomeMeasures;
  bbox: Record<string, number>;
  order: number;
}

/** Herramienta de corrección manual activa (P3). */
export type KaryoTool = 'select' | 'split' | 'join' | 'cross';

// --- P2 (ADR-0021 P2, ADR-0022, DD-KARYO-002) ---

/** Respuesta de POST /chromosomes/{id}/xai/ — heatmap Grad-CAM (mock en demo). */
export interface XaiResult {
  chromosome_id: string;
  predicted_class: string;
  confidence_score: string | null;
  heatmap_base64: string;
}

export type AuditEventType =
  | 'XAI_VIEWED' | 'ACCEPT_CHROMOSOME' | 'RECLASSIFY' | 'CORRECT_CLASS'
  | 'MARK_ANOMALY' | 'SPLIT' | 'JOIN' | 'RESOLVE_CROSS'
  | 'ANALYST_VALIDATED' | 'AUDIT_DECISION' | 'ISCN_OVERRIDE' | 'SIGN_REPORT'
  | 'NARRATIVE_GENERATED'; // ADR-0024: borrador redactado por el LLM

export type AuditMode = 'auto' | 'degradado';

export interface AuditEvent {
  id: string;
  event_type: AuditEventType;
  chromosome: string | null;
  actor: number;
  actor_name: string;
  payload: Record<string, unknown>;
  mode: AuditMode; // P4: 'degradado' si la acción se hizo sin IA (FSD-UC-007)
  created_at: string;
  previous_hash: string;
  current_hash: string;
}

/** Respuesta de GET /pipeline/health/ (P4, DD-KARYO-004). */
export interface PipelineHealth {
  available: boolean;
  mode: AuditMode;
}

/** Respuesta de POST /samples/{id}/validate/. */
export interface ValidateResult {
  sample_id: string;
  status: string;
}

/** Etiqueta legible por tipo de evento de auditoría (para el log). */
export const AUDIT_LABELS: Record<AuditEventType, string> = {
  XAI_VIEWED: 'Consultó explicabilidad (XAI)',
  ACCEPT_CHROMOSOME: 'Aceptó cromosoma',
  RECLASSIFY: 'Reclasificó',
  CORRECT_CLASS: 'Corrigió clase',
  MARK_ANOMALY: 'Marcó anomalía',
  SPLIT: 'Separó',
  JOIN: 'Unió',
  RESOLVE_CROSS: 'Resolvió cruce',
  ANALYST_VALIDATED: 'Validó el caso',
  AUDIT_DECISION: 'Decisión de auditoría',
  ISCN_OVERRIDE: 'Override ISCN',
  SIGN_REPORT: 'Firmó reporte',
  NARRATIVE_GENERATED: 'Generó borrador narrativo (IA)',
};

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
  sample_status: string; // estado clínico de la muestra (gating del panel supervisor)
  sample_iscn?: string;  // S3: nomenclatura ya generada, '' si aún no (ADR-0025)
  model_version: string;
  generated_at: string;
  summary: KaryotypeSummary;
  chromosomes: Chromosome[];
}

// --- Supervisor S1 (ADR-0023, DD-SUP-001) — auditoría del 5% ---

export type AuditDecision = 'PENDING' | 'CONFIRMED' | 'REJECTED';

export interface AuditReview {
  id: string;
  chromosome: string;
  predicted_class: string;
  confidence_score: string | null;
  semaphore: Semaphore;
  decision: AuditDecision;
  comment: string;
  reviewer: number | null;
  reviewer_name: string;
  decided_at: string | null;
  created_at: string;
}

export interface AuditReviewSummary {
  total: number;
  pending: number;
  confirmed: number;
  rejected: number;
}

export interface AuditReviewResponse {
  reviews: AuditReview[];
  summary: AuditReviewSummary;
}

/** % legible desde el confidence_score string ("0.720" → "72%"). */
export function confidencePercent(score: string | null): string {
  if (score === null) return '—';
  return `${Math.round(parseFloat(score) * 100)}%`;
}

// --- Supervisor S3 (motor ISCN, ADR-0023 D4 / ADR-0025) ---

export interface IscnResult {
  iscn_nomenclature: string;
  is_override: boolean;
  generated_at: string | null;
  status: string;
}

/** Salida tipada del LLM (ADR-0024 D4). `null` cuando el modelo no respondió. */
export interface NarrativeStructured {
  hallazgo: string;
  interpretacion: string;
  es_normal: boolean;
  anomalias_citadas: string[];
  nivel_confianza: 'alta' | 'media' | 'baja';
}

export interface NarrativeResult {
  generated: boolean;
  /** Motivo de la degradación cuando `generated` es false (RN-07). */
  reason: string | null;
  iscn_input: string;
  structured: NarrativeStructured | null;
  narrative_draft: string;
  model: string;
  generated_at: string | null;
  /** Siempre true: requiere revisión del Supervisor antes del informe (D3). */
  is_draft: boolean;
}
