import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { BBox, MotivoDescarte } from '../types/karyotype';
import { karyotypeClient } from '../api/karyotypeClient';

/** Acciones de P2 (XAI, resolver, anomalía, validar) + bitácora de auditoría.
 * Cada mutación invalida el cariotipo y el audit para refrescar el estado. */
export function useKaryotypeActions(sampleId: string | undefined) {
  const qc = useQueryClient();
  const invalidate = () => {
    // `exact`: la metafase cuelga de la misma clave (['clinic', 'karyotype', id,
    // 'metaphase']). Sin él, cada corrección volvía a descargar ~3 MB y montaba
    // de nuevo el editor, que perdía el zoom y la herramienta (visto el 23/10).
    qc.invalidateQueries({ queryKey: ['clinic', 'karyotype', sampleId], exact: true });
    qc.invalidateQueries({ queryKey: ['clinic', 'audit', sampleId] });
    // Lo que «Deshacer» desharía cambia con cada edición (D6).
    qc.invalidateQueries({ queryKey: ['clinic', 'undo', sampleId] });
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
  const recrop = useMutation({
    mutationFn: (v: { chromosomeId: string; bbox: BBox }) =>
      karyotypeClient.recrop(sampleId as string, v.chromosomeId, v.bbox),
    onSuccess: invalidate,
  });
  const split = useMutation({
    mutationFn: (v: { chromosomeId: string; linea: number[][] }) =>
      karyotypeClient.split(sampleId as string, v.chromosomeId, v.linea),
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

  // --- DD-KARYO-007 D5: corregir la segmentación sobre la metafase ---
  const rejectObject = useMutation({
    mutationFn: (v: { chromosomeId: string; motivo: MotivoDescarte }) =>
      karyotypeClient.rejectObject(sampleId as string, v.chromosomeId, v.motivo),
    onSuccess: invalidate,
  });
  const addObject = useMutation({
    mutationFn: (v: { bbox: BBox; clase: string }) =>
      karyotypeClient.addObject(sampleId as string, v.bbox, v.clase),
    onSuccess: invalidate,
  });

  const orient = useMutation({
    mutationFn: (v: { chromosomeId: string; giro: 0 | 180; volteo: boolean; ajuste: number }) =>
      karyotypeClient.orient(sampleId as string, v.chromosomeId, v.giro, v.volteo, v.ajuste),
    onSuccess: invalidate,
  });
  const undo = useMutation({
    mutationFn: () => karyotypeClient.undo(sampleId as string),
    onSuccess: invalidate,
  });

  return {
    viewXai, resolve, markAnomaly, validate, reclassify, recrop, split, join, resolveCross,
    rejectObject, addObject, undo, orient,
  };
}

/** Lo que «Deshacer» desharía ahora (DD-KARYO-007 D6). Solo en casos editables. */
export function useUltimaEdicion(sampleId: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: ['clinic', 'undo', sampleId] as const,
    queryFn: () => karyotypeClient.lastEdit(sampleId as string),
    enabled: Boolean(sampleId) && enabled,
    retry: false,
  });
}

export function useAuditTrail(sampleId: string | undefined, enabled = false) {
  return useQuery({
    queryKey: ['clinic', 'audit', sampleId] as const,
    queryFn: () => karyotypeClient.getAudit(sampleId as string),
    enabled: Boolean(sampleId) && enabled,
  });
}
