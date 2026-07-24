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
import type { AuditEvent, Chromosome, Karyotype, ValidateResult, XaiResult } from '../types/karyotype';

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
  };
}

export type KaryotypeClient = ReturnType<typeof createKaryotypeClient>;
export const karyotypeClient: KaryotypeClient = createKaryotypeClient();
