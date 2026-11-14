import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { samplesClient } from '../api/samplesClient';
import { ClinicApiException } from '../types/sample';

const TERMINAL_STATUSES = new Set(['READY', 'VALIDATED', 'REJECTED']);

/** Si el backend dice ML_BUSY sin segundos, se espera el tope de backend-ml. */
export const ESPERA_POR_OMISION_S = 25;

export function useTriggerProcess(sampleId: string) {
  const queryClient = useQueryClient();
  const [degraded, setDegraded] = useState(false);
  // DD-OBS-001 D8: segundos de espera cuando el motor está ocupado; null si no.
  const [busySeconds, setBusySeconds] = useState<number | null>(null);

  const mutation = useMutation({
    mutationFn: (forceReprocess: boolean = false) => samplesClient.process(sampleId, forceReprocess),
    onMutate: () => {
      setBusySeconds(null);
    },
    onSuccess: () => {
      setDegraded(false);
      void queryClient.invalidateQueries({ queryKey: ['clinic', 'sample', sampleId] });
    },
    onError: (err: unknown) => {
      if (!(err instanceof ClinicApiException)) return;
      if (err.code === 'ML_BUSY') {
        // El motor está sano y ocupado: NO es el modo degradado.
        setBusySeconds(err.retryAfterSeconds ?? ESPERA_POR_OMISION_S);
      } else if (err.code === 'ML_DEGRADED') {
        setDegraded(true);
      }
    },
  });

  return {
    ...mutation,
    degraded,
    resetDegraded: () => setDegraded(false),
    busySeconds,
    resetBusy: () => setBusySeconds(null),
  };
}

/** RN-07: polling cada 2s hasta que el status sea terminal (READY/VALIDATED/REJECTED). */
export function useStatusPolling(sampleId: string, enabled: boolean) {
  return useQuery({
    queryKey: ['clinic', 'sample-status', sampleId] as const,
    queryFn: () => samplesClient.getStatus(sampleId),
    enabled: enabled && Boolean(sampleId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status && TERMINAL_STATUSES.has(status)) return false;
      return 2000;
    },
  });
}
