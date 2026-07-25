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
