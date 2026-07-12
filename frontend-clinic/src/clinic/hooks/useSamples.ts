import { useQuery } from '@tanstack/react-query';
import { samplesClient } from '../api/samplesClient';
import type { SampleFilters } from '../types/sample';

export const samplesQueryKey = (filters?: SampleFilters) => ['clinic', 'samples', filters ?? {}] as const;

export function useSamples(filters?: SampleFilters) {
  return useQuery({
    queryKey: samplesQueryKey(filters),
    queryFn: () => samplesClient.list(filters),
  });
}

export function useSample(id: string | undefined) {
  return useQuery({
    queryKey: ['clinic', 'sample', id] as const,
    queryFn: () => samplesClient.get(id as string),
    enabled: Boolean(id),
  });
}
