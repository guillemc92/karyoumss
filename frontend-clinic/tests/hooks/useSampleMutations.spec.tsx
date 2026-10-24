import { describe, expect, it } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useCreateSample, useDeleteSample, useUpdateSample } from '../../src/clinic/hooks/useSampleMutations';

function wrapper({ children }: { children: ReactNode }) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}

describe('useSampleMutations', () => {
  it('useCreateSample crea una muestra', async () => {
    const { result } = renderHook(() => useCreateSample(), { wrapper });
    result.current.mutate({ chn_code: 'CHN-HOOK-001', patient_ref: 'ANON-HOOK' });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.chn_code).toBe('CHN-HOOK-001');
  });

  it('useUpdateSample actualiza patient_ref', async () => {
    const { result: createResult } = renderHook(() => useCreateSample(), { wrapper });
    createResult.current.mutate({ chn_code: 'CHN-HOOK-002', patient_ref: 'A' });
    await waitFor(() => expect(createResult.current.isSuccess).toBe(true));
    const id = createResult.current.data!.id;

    const { result } = renderHook(() => useUpdateSample(id), { wrapper });
    result.current.mutate({ patient_ref: 'B' });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.patient_ref).toBe('B');
  });

  it('useDeleteSample elimina una muestra', async () => {
    const { result: createResult } = renderHook(() => useCreateSample(), { wrapper });
    createResult.current.mutate({ chn_code: 'CHN-HOOK-003', patient_ref: 'A' });
    await waitFor(() => expect(createResult.current.isSuccess).toBe(true));
    const id = createResult.current.data!.id;

    const { result } = renderHook(() => useDeleteSample(), { wrapper });
    result.current.mutate(id);
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });
});
