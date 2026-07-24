import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { karyotypeClient } from '../api/karyotypeClient';

/** Acciones de P2 (XAI, resolver, anomalía, validar) + bitácora de auditoría.
 * Cada mutación invalida el cariotipo y el audit para refrescar el estado. */
export function useKaryotypeActions(sampleId: string | undefined) {
  const qc = useQueryClient();
  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['clinic', 'karyotype', sampleId] });
    qc.invalidateQueries({ queryKey: ['clinic', 'audit', sampleId] });
  };

  const viewXai = useMutation({
    mutationFn: (chromosomeId: string) => karyotypeClient.viewXai(sampleId as string, chromosomeId),
    onSuccess: invalidate,
  });
  const resolve = useMutation({
    mutationFn: (chromosomeId: string) => karyotypeClient.resolveChromosome(sampleId as string, chromosomeId),
    onSuccess: invalidate,
  });
  const markAnomaly = useMutation({
    mutationFn: (chromosomeId: string) => karyotypeClient.markAnomaly(sampleId as string, chromosomeId),
    onSuccess: invalidate,
  });
  const validate = useMutation({
    mutationFn: () => karyotypeClient.validateCase(sampleId as string),
    onSuccess: invalidate,
  });

  // --- P3 (corrección manual, DD-KARYO-003) ---
  const reclassify = useMutation({
    mutationFn: (v: { chromosomeId: string; targetClass: string }) =>
      karyotypeClient.reclassify(sampleId as string, v.chromosomeId, v.targetClass),
    onSuccess: invalidate,
  });
  const split = useMutation({
    mutationFn: (chromosomeId: string) => karyotypeClient.split(sampleId as string, chromosomeId),
    onSuccess: invalidate,
  });
  const join = useMutation({
    mutationFn: (v: { keepId: string; otherId: string }) =>
      karyotypeClient.join(sampleId as string, v.keepId, v.otherId),
    onSuccess: invalidate,
  });
  const resolveCross = useMutation({
    mutationFn: (chromosomeId: string) => karyotypeClient.resolveCross(sampleId as string, chromosomeId),
    onSuccess: invalidate,
  });

  return { viewXai, resolve, markAnomaly, validate, reclassify, split, join, resolveCross };
}

export function useAuditTrail(sampleId: string | undefined, enabled = false) {
  return useQuery({
    queryKey: ['clinic', 'audit', sampleId] as const,
    queryFn: () => karyotypeClient.getAudit(sampleId as string),
    enabled: Boolean(sampleId) && enabled,
  });
}
