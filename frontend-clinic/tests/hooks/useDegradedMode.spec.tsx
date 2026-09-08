import { afterEach, describe, expect, it } from 'vitest';
import type { ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import { useDegradedMode } from '../../src/clinic/hooks/useDegradedMode';
import { setDegradedMode } from '../../src/clinic/msw/handlers';
import { getClinicMode, setClinicMode } from '../../src/clinic/api/samplesClient';

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

afterEach(() => setClinicMode('auto'));

describe('useDegradedMode (P4)', () => {
  it('con IA disponible reporta degraded=false y modo auto', async () => {
    const { result } = renderHook(() => useDegradedMode(), { wrapper });
    await waitFor(() => expect(result.current.degraded).toBe(false));
    expect(getClinicMode()).toBe('auto');
  });

  it('con IA caída reporta degraded=true y propaga modo degradado al cliente', async () => {
    setDegradedMode(true);
    const { result } = renderHook(() => useDegradedMode(), { wrapper });
    await waitFor(() => expect(result.current.degraded).toBe(true));
    expect(getClinicMode()).toBe('degradado');
  });
});
