import { useMutation, useQueryClient } from '@tanstack/react-query';
import { samplesClient } from '../api/samplesClient';
import type { SampleCreateRequest, SampleUpdateRequest } from '../types/sample';

export function useCreateSample() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (draft: SampleCreateRequest) => samplesClient.create(draft),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['clinic', 'samples'] });
    },
  });
}

export function useUpdateSample(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (patch: SampleUpdateRequest) => samplesClient.update(id, patch),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['clinic', 'samples'] });
      void queryClient.invalidateQueries({ queryKey: ['clinic', 'sample', id] });
    },
  });
}

export function useDeleteSample() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => samplesClient.softDelete(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['clinic', 'samples'] });
    },
  });
}
