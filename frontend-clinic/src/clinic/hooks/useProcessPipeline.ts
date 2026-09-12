import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { samplesClient } from '../api/samplesClient';
import { ClinicApiException } from '../types/sample';

const TERMINAL_STATUSES = new Set(['READY', 'VALIDATED', 'REJECTED']);

export function useTriggerProcess(sampleId: string) {
  const queryClient = useQueryClient();
  const [degraded, setDegraded] = useState(false);

  const mutation = useMutation({
    mutationFn: (forceReprocess: boolean = false) => samplesClient.process(sampleId, forceReprocess),
    onSuccess: () => {
      setDegraded(false);
      void queryClient.invalidateQueries({ queryKey: ['clinic', 'sample', sampleId] });
    },
    onError: (err: unknown) => {
      if (err instanceof ClinicApiException && err.code === 'ML_DEGRADED') {
        setDegraded(true);
      }
    },
  });

  return { ...mutation, degraded, resetDegraded: () => setDegraded(false) };
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
