/**
 * useAuditReview — auditoría del 5% del Supervisor (S1, DD-SUP-001).
 * Carga la selección determinista + expone la mutación de decisión.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { karyotypeClient } from '../api/karyotypeClient';

export function useAuditReview(sampleId: string | undefined, enabled = false) {
  return useQuery({
    queryKey: ['clinic', 'audit-review', sampleId] as const,
    queryFn: () => karyotypeClient.getAuditReview(sampleId as string),
    enabled: Boolean(sampleId) && enabled,
  });
}

export function useAuditDecide(sampleId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { chromosomeId: string; decision: 'CONFIRMED' | 'REJECTED'; comment?: string }) =>
      karyotypeClient.decideAudit(sampleId as string, v.chromosomeId, v.decision, v.comment ?? ''),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['clinic', 'audit-review', sampleId] });
      qc.invalidateQueries({ queryKey: ['clinic', 'audit', sampleId] });
    },
  });
}

/** Firma MFA del Supervisor (S2). Invalida el cariotipo para reflejar SIGNED. */
export function useSignReport(sampleId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (mfaCode: string) => karyotypeClient.signReport(sampleId as string, mfaCode),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['clinic', 'karyotype', sampleId] });
      qc.invalidateQueries({ queryKey: ['clinic', 'audit', sampleId] });
    },
  });
}

// --- Supervisor S3 (ISCN + narrativa) ---

/**
 * Genera la nomenclatura ISCN (ADR-0025). Invalida el cariotipo para reflejar
 * el paso a REPORTED, y la auditoría porque un override emite ISCN_OVERRIDE.
 */
export function useGenerateIscn(sampleId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { override?: string; justification?: string } = {}) =>
      karyotypeClient.generateIscn(sampleId as string, v.override ?? '', v.justification ?? ''),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['clinic', 'karyotype', sampleId] });
      qc.invalidateQueries({ queryKey: ['clinic', 'audit', sampleId] });
    },
  });
}

/**
 * Genera el borrador narrativo con el LLM (ADR-0024).
 *
 * No lanza cuando el modelo falla: el backend responde 200 con
 * `generated: false`, y la UI muestra el motivo sin bloquear el informe (RN-07).
 */
export function useGenerateNarrative(sampleId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (iscn?: string) => karyotypeClient.generateNarrative(sampleId as string, iscn ?? ''),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['clinic', 'audit', sampleId] });
    },
  });
}
