import { describe, expect, it } from 'vitest';
import type { ReactNode } from 'react';
import { act, renderHook } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useKaryotypeActions } from '../../src/clinic/hooks/useKaryotypeActions';

/**
 * Una corrección refresca el cariotipo y la auditoría, pero NO la metafase.
 *
 * La clave de la metafase cuelga de la del cariotipo (['clinic', 'karyotype',
 * id, 'metaphase']). Invalidar por prefijo la volvía a descargar (~3 MB) tras
 * cada corrección y montaba de nuevo el editor, que perdía el zoom y la
 * herramienta activa. Lo cazó el E2E de DD-KARYO-007 T3 el 23/10.
 */
const SAMPLE = '00000000-0000-0000-0000-000000000442';
const CROMOSOMA = `${SAMPLE}-chr-18-0`;

function preparar() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  qc.setQueryData(['clinic', 'karyotype', SAMPLE], { id: 'k' });
  qc.setQueryData(['clinic', 'karyotype', SAMPLE, 'metaphase'], new Blob(['x']));
  qc.setQueryData(['clinic', 'audit', SAMPLE], []);
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
  return { qc, ...renderHook(() => useKaryotypeActions(SAMPLE), { wrapper }) };
}

const invalidada = (qc: QueryClient, key: unknown[]) => qc.getQueryState(key)?.isInvalidated;

describe('useKaryotypeActions — qué se refresca tras una corrección', () => {
  it('descartar refresca cariotipo y auditoría, no la metafase', async () => {
    const { qc, result } = preparar();
    await act(async () => {
      await result.current.rejectObject.mutateAsync({ chromosomeId: CROMOSOMA, motivo: 'otro' });
    });
    expect(invalidada(qc, ['clinic', 'karyotype', SAMPLE])).toBe(true);
    expect(invalidada(qc, ['clinic', 'audit', SAMPLE])).toBe(true);
    expect(invalidada(qc, ['clinic', 'karyotype', SAMPLE, 'metaphase'])).toBe(false);
  });

  it('añadir tampoco toca la metafase', async () => {
    const { qc, result } = preparar();
    await act(async () => {
      await result.current.addObject.mutateAsync({ bbox: { x: 1, y: 1, w: 20, h: 20 }, clase: '' });
    });
    expect(invalidada(qc, ['clinic', 'karyotype', SAMPLE])).toBe(true);
    expect(invalidada(qc, ['clinic', 'karyotype', SAMPLE, 'metaphase'])).toBe(false);
  });
});
