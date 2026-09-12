/**
 * toolsClient — consultas en lenguaje natural (Módulo 6, tool calling).
 *
 * El modelo ELIGE la herramienta; el backend PRODUCE la respuesta contra la
 * base. El cliente solo transporta: nunca interpreta ni completa datos.
 *
 *   POST /api/clinic/tools/query/   {"pregunta": "..."}
 *   GET  /api/clinic/tools/query/   → catálogo publicado
 *
 * El POST **siempre responde 200**, incluso cuando ninguna herramienta aplica:
 * preguntar algo fuera de alcance no es un error del cliente. Por eso la UI
 * distingue por `camino`, no por status HTTP.
 */
import { clinicRequest, CLINIC_DEFAULT_BASE_URL } from './samplesClient';
import type { CatalogoResponse, ToolRespuesta } from '../types/tools';

export function createToolsClient(baseUrl: string = CLINIC_DEFAULT_BASE_URL) {
  return {
    /** Resuelve una pregunta. La latencia del camino LLM puede ser de minutos. */
    consultar(pregunta: string): Promise<ToolRespuesta> {
      return clinicRequest<ToolRespuesta>(baseUrl, '/tools/query/', {
        method: 'POST',
        body: { pregunta },
      });
    },

    /** Qué sabe responder el sistema. Se muestra antes de preguntar. */
    catalogo(): Promise<CatalogoResponse> {
      return clinicRequest<CatalogoResponse>(baseUrl, '/tools/query/', { method: 'GET' });
    },
  };
}

export type ToolsClient = ReturnType<typeof createToolsClient>;
export const toolsClient: ToolsClient = createToolsClient();
