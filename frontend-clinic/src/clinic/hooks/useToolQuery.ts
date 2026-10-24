/**
 * useToolQuery — consultas en lenguaje natural (Módulo 6, tool calling).
 *
 * La mutación no reintenta: el camino LLM puede tardar minutos en CPU, y un
 * reintento automático duplicaría esa espera sin avisarle al usuario.
 */
import { useMutation, useQuery } from '@tanstack/react-query';
import { toolsClient } from '../api/toolsClient';

export function useToolQuery() {
  return useMutation({
    mutationFn: (pregunta: string) => toolsClient.consultar(pregunta),
    retry: false,
  });
}

/** Catálogo publicado: qué sabe responder el sistema. */
export function useToolCatalogo() {
  return useQuery({
    queryKey: ['clinic', 'tools', 'catalogo'] as const,
    queryFn: () => toolsClient.catalogo(),
    staleTime: 5 * 60 * 1000,   // el catálogo cambia con un deploy, no en runtime
  });
}
