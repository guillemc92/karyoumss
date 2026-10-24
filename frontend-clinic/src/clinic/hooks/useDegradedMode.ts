/**
 * useDegradedMode — detecta si el pipeline de IA está caído y activa el modo
 * manual/degradado (P4, DD-KARYO-004, FSD-UC-007 §8).
 *
 * Consulta /pipeline/health/ cada 30s. Cuando la IA no está disponible,
 * propaga el estado como header `X-Biomed-Mode: degradado` (vía setClinicMode)
 * para que TODA acción manual quede marcada en el audit trail. Al restaurarse,
 * vuelve a 'auto' y expone `justRestored` para ofrecer volver a modo automático.
 */
import { useEffect, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { karyotypeClient } from '../api/karyotypeClient';
import { setClinicMode } from '../api/samplesClient';

const POLL_MS = 30_000;

export function useDegradedMode() {
  const { data } = useQuery({
    queryKey: ['clinic', 'pipeline-health'] as const,
    queryFn: () => karyotypeClient.pipelineHealth(),
    refetchInterval: POLL_MS,
    // staleTime bajo: además del poll de 30s, refresca al recuperar el foco
    // (permite reflejar rápido una caída/restauración de la IA).
    staleTime: 1_000,
  });

  const degraded = data ? !data.available : false;
  const wasDegraded = useRef(false);
  const [justRestored, setJustRestored] = useState(false);

  useEffect(() => {
    if (data === undefined) return;
    setClinicMode(degraded ? 'degradado' : 'auto');
    if (wasDegraded.current && !degraded) setJustRestored(true);
    wasDegraded.current = degraded;
  }, [degraded, data]);

  return { degraded, justRestored, dismissRestored: () => setJustRestored(false) };
}
