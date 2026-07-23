import { useQuery } from '@tanstack/react-query';
import { karyotypeClient } from '../api/karyotypeClient';

export function useKaryotype(sampleId: string | undefined) {
  return useQuery({
    queryKey: ['clinic', 'karyotype', sampleId] as const,
    queryFn: () => karyotypeClient.get(sampleId as string),
    enabled: Boolean(sampleId),
    retry: false, // 404 NO_KARYOTYPE es un estado esperado, no un fallo a reintentar
  });
}
