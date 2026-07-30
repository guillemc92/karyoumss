/**
 * karyotypeClient — wrapper HTTP del visor de cariotipo (ADR-0021 P1).
 *
 * Reutiliza la infra de samplesClient (auth JWT + parseo de errores).
 * P1: solo GET. P2/P3 agregarán resolver naranjas, XAI y reclasificación.
 *
 * Errores esperados:
 *   401 → JWT ausente/expirado
 *   403 → NOT_OWNER (analista no dueño de la muestra)
 *   404 → NOT_FOUND (muestra) / NO_KARYOTYPE (sin cariotipo generado aún)
 */
import { clinicRequest, CLINIC_DEFAULT_BASE_URL } from './samplesClient';
import type {
  AuditEvent, AuditReview, AuditReviewResponse, Chromosome, IscnResult, Karyotype,
  NarrativeResult, PipelineHealth, ValidateResult, XaiResult,
} from '../types/karyotype';

export function createKaryotypeClient(baseUrl: string = CLINIC_DEFAULT_BASE_URL) {
  return {
    baseUrl,
    /** GET /api/clinic/samples/{sampleId}/karyotype/ */
    get(sampleId: string): Promise<Karyotype> {
      return clinicRequest<Karyotype>(baseUrl, `/samples/${sampleId}/karyotype/`, { method: 'GET' });
    },

    // --- P2 ---

    /** POST /chromosomes/{cid}/xai/ — heatmap Grad-CAM + registra XAI_VIEWED (BR-004). */
    viewXai(sampleId: string, chromosomeId: string): Promise<XaiResult> {
      return clinicRequest<XaiResult>(baseUrl, `/samples/${sampleId}/chromosomes/${chromosomeId}/xai/`, { method: 'POST' });
    },
    /** POST /chromosomes/{cid}/resolve/ — resuelve naranja (409 XAI_REQUIRED si no vio XAI). */
    resolveChromosome(sampleId: string, chromosomeId: string): Promise<Chromosome> {
      return clinicRequest<Chromosome>(baseUrl, `/samples/${sampleId}/chromosomes/${chromosomeId}/resolve/`, { method: 'POST' });
    },
    /** POST /chromosomes/{cid}/anomaly/ — marca anomalía estructural (M). */
    markAnomaly(sampleId: string, chromosomeId: string): Promise<Chromosome> {
      return clinicRequest<Chromosome>(baseUrl, `/samples/${sampleId}/chromosomes/${chromosomeId}/anomaly/`, { method: 'POST' });
    },
    /** POST /samples/{id}/validate/ — pasar a supervisor (409 CASE_BLOCKED si hay naranjas). */
    validateCase(sampleId: string): Promise<ValidateResult> {
      return clinicRequest<ValidateResult>(baseUrl, `/samples/${sampleId}/validate/`, { method: 'POST' });
    },
    /** GET /samples/{id}/audit/ — bitácora append-only. */
    getAudit(sampleId: string): Promise<AuditEvent[]> {
      return clinicRequest<AuditEvent[]>(baseUrl, `/samples/${sampleId}/audit/`, { method: 'GET' });
    },

    // --- P3 (corrección manual, DD-KARYO-003) ---

    /** POST /chromosomes/{cid}/reclassify/ — mover a otro slot (CORRECT_CLASS). */
    reclassify(sampleId: string, chromosomeId: string, targetClass: string): Promise<Chromosome> {
      return clinicRequest<Chromosome>(baseUrl, `/samples/${sampleId}/chromosomes/${chromosomeId}/reclassify/`, {
        method: 'POST',
        body: { target_class: targetClass },
      });
    },
    /** POST /chromosomes/{cid}/split/ — separar touching (crea 2º cromosoma). */
    split(sampleId: string, chromosomeId: string): Promise<Chromosome> {
      return clinicRequest<Chromosome>(baseUrl, `/samples/${sampleId}/chromosomes/${chromosomeId}/split/`, { method: 'POST' });
    },
    /** POST /chromosomes/{cid}/join/ — unir `otherId` en `chromosomeId`. */
    join(sampleId: string, chromosomeId: string, otherId: string): Promise<Chromosome> {
      return clinicRequest<Chromosome>(baseUrl, `/samples/${sampleId}/chromosomes/${chromosomeId}/join/`, {
        method: 'POST',
        body: { other_id: otherId },
      });
    },
    /** POST /chromosomes/{cid}/cross/ — resolver cruce (individualiza). */
    resolveCross(sampleId: string, chromosomeId: string): Promise<Chromosome> {
      return clinicRequest<Chromosome>(baseUrl, `/samples/${sampleId}/chromosomes/${chromosomeId}/cross/`, { method: 'POST' });
    },

    // --- P4 (modo degradado, DD-KARYO-004) ---

    /** GET /pipeline/health/ — disponibilidad de la IA (para el modo degradado). */
    pipelineHealth(): Promise<PipelineHealth> {
      return clinicRequest<PipelineHealth>(baseUrl, '/pipeline/health/', { method: 'GET' });
    },

    // --- Supervisor S1 (auditoría del 5%, DD-SUP-001) ---

    /** GET /samples/{id}/audit-review/ — selección del 5% + resumen. */
    getAuditReview(sampleId: string): Promise<AuditReviewResponse> {
      return clinicRequest<AuditReviewResponse>(baseUrl, `/samples/${sampleId}/audit-review/`, { method: 'GET' });
    },
    /** POST /audit-review/{cid}/decide/ — Confirmar/Rechazar un cromosoma auditado. */
    decideAudit(sampleId: string, chromosomeId: string, decision: 'CONFIRMED' | 'REJECTED', comment = ''): Promise<AuditReview> {
      return clinicRequest<AuditReview>(baseUrl, `/samples/${sampleId}/audit-review/${chromosomeId}/decide/`, {
        method: 'POST',
        body: { decision, comment },
      });
    },

    // --- Supervisor S2 (firma MFA, DD-SUP-002) ---

    /** POST /samples/{id}/sign/ — firma MFA del Supervisor. */
    signReport(sampleId: string, mfaCode: string): Promise<{ sample_id: string; status: string; signed_at: string }> {
      return clinicRequest(baseUrl, `/samples/${sampleId}/sign/`, { method: 'POST', body: { mfa_code: mfaCode } });
    },

    // --- Supervisor S3 (motor ISCN + narrativa, ADR-0025 / ADR-0024) ---

    /**
     * POST /samples/{id}/iscn/ — genera la nomenclatura y pasa el caso a REPORTED.
     *
     * Sin `override`, la calcula la función pura del backend sobre el conteo
     * validado. Con `override`, el Supervisor impone su string y debe justificarlo:
     * queda auditado (ISCN_OVERRIDE). RN-04: no hay PATCH sobre el campo.
     */
    generateIscn(sampleId: string, override = '', justification = ''): Promise<IscnResult> {
      return clinicRequest<IscnResult>(baseUrl, `/samples/${sampleId}/iscn/`, {
        method: 'POST',
        body: override ? { override, justification } : {},
      });
    },

    /**
     * POST /samples/{id}/narrative/ — borrador narrativo asistido por LLM.
     *
     * Devuelve 200 con `generated: false` si el modelo no responde o alucina:
     * la narrativa nunca bloquea la emisión del informe (RN-07).
     */
    generateNarrative(sampleId: string, iscn = ''): Promise<NarrativeResult> {
      return clinicRequest<NarrativeResult>(baseUrl, `/samples/${sampleId}/narrative/`, {
        method: 'POST',
        body: iscn ? { iscn } : {},
      });
    },
  };
}

export type KaryotypeClient = ReturnType<typeof createKaryotypeClient>;
export const karyotypeClient: KaryotypeClient = createKaryotypeClient();
