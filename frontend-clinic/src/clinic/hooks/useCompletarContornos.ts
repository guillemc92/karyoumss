import { useEffect, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { karyotypeClient } from '../api/karyotypeClient';
import { faltanContornos } from '../lib/contornoMetafase';
import type { Karyotype } from '../types/karyotype';

/**
 * Pide los contornos que faltan al abrir un caso antiguo (DD-KARYO-007 T2).
 *
 * Los casos segmentados antes de T1 solo tienen cajas. Al abrirlos, se le pide
 * una vez al servidor que calcule las siluetas y se recarga el cariotipo.
 *
 * - **Una vez por caso**, no en cada recarga: si backend-ml no puede (503) o el
 *   caso está bloqueado (409), volver a pedirlo en cada refetch sería un bucle.
 *   Lo que no se pudo calcular se sigue viendo como caja (RN-07).
 * - Tras recortar, separar o unir, el servidor deja `contour = null` en el
 *   objeto tocado. Eso SÍ se vuelve a pedir: es otro estado del caso. Por eso la
 *   marca recuerda qué cromosomas faltaban, no solo el caso.
 * - Los errores se callan: sin silueta el editor pinta la caja, que es lo que se
 *   veía antes. No es algo que el analista tenga que resolver.
 */
export function useCompletarContornos(
  sampleId: string | undefined,
  karyotype: Karyotype | undefined,
  editable: boolean,
): void {
  const qc = useQueryClient();
  const pedidos = useRef(new Set<string>());

  useEffect(() => {
    if (!sampleId || !karyotype || !editable) return;
    if (!faltanContornos(karyotype.chromosomes)) return;
    const firma = `${sampleId}:${karyotype.chromosomes
      .filter((c) => c.is_active && !c.contour)
      .map((c) => c.id)
      .sort()
      .join(',')}`;
    if (pedidos.current.has(firma)) return;
    pedidos.current.add(firma);
    karyotypeClient.completeContours(sampleId).then(
      ({ completados }) => {
        if (completados > 0) {
          // Solo el cariotipo: la metafase no cambia y no hay evento nuevo.
          void qc.invalidateQueries({ queryKey: ['clinic', 'karyotype', sampleId], exact: true });
        }
      },
      () => {},
    );
  }, [sampleId, karyotype, editable, qc]);
}
