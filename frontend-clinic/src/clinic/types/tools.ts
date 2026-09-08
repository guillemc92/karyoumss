/**
 * Tipos del tool calling (Módulo 6). Espejo de `tool_router.Respuesta`.
 */

/** Cómo se resolvió la consulta. Es la evidencia que la UI debe mostrar. */
export type CaminoConsulta =
  | 'KEYWORD'    // palabra del catálogo: se ejecutó SIN llamar al modelo
  | 'LLM'        // el modelo eligió la herramienta
  | 'SIN_MATCH'; // ninguna aplica — no es un error

export interface HerramientaPublicada {
  herramienta: string;
  responde: string;
  fuente: string;   // tabla real
}

export interface ToolRespuesta {
  camino: CaminoConsulta;
  tool: string | null;
  source: string | null;      // de qué tabla salió el dato
  filas: Record<string, string>[];
  mensaje: string;
  motivo: string;             // por qué el modelo eligió (solo camino LLM)
  latency_ms: number;
  /** Solo en SIN_MATCH: qué SÍ se puede preguntar. */
  catalogo?: HerramientaPublicada[];
}

export interface CatalogoResponse {
  herramientas: HerramientaPublicada[];
}

/** Etiqueta legible del camino, para la insignia de procedencia. */
export const CAMINO_LABEL: Record<CaminoConsulta, string> = {
  KEYWORD: 'Sin IA — palabra del catálogo',
  LLM: 'El modelo eligió la herramienta',
  SIN_MATCH: 'Fuera de alcance',
};
