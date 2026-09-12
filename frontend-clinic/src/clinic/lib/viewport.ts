/**
 * viewport — estado y reducer PURO de las herramientas de imagen del cariograma
 * (P4, DD-KARYO-004 §3.1). Sin React/Konva: 100% testeable en jsdom.
 *
 * scale/rotation/offset se aplican al Stage de Konva; brightness/contrast al
 * contenedor del canvas vía CSS filter (los cromosomas son vectoriales — aún
 * no hay imagen de metafase real, ADR-0007).
 */
export interface ViewportState {
  scale: number;
  rotation: number; // grados
  offsetX: number;
  offsetY: number;
  brightness: number; // %
  contrast: number; // %
  panMode: boolean; // "Mover": arrastra el lienzo en vez de reclasificar
  /**
   * Espejo del lienzo. Es una transformación de VISTA, no del dato: no cambia
   * la orientación guardada de ningún cromosoma ni deja evento de auditoría.
   *
   * Sirve para leer: por convención ISCN el brazo corto (p) se dibuja arriba, y
   * un cromosoma capturado al revés se compara mejor volteando la vista que
   * girando la cabeza. Voltear un cromosoma *concreto* de forma persistente
   * sería una operación de dato, con su endpoint y su traza.
   */
  flipX: boolean;
  flipY: boolean;
}

export const SCALE_MIN = 0.5;
export const SCALE_MAX = 3;
export const SCALE_STEP = 0.25;
export const ROTATE_STEP = 15;
export const FILTER_MIN = 50;
export const FILTER_MAX = 150;

export const INITIAL_VIEWPORT: ViewportState = {
  scale: 1,
  rotation: 0,
  offsetX: 0,
  offsetY: 0,
  brightness: 100,
  contrast: 100,
  panMode: false,
  flipX: false,
  flipY: false,
};

export type ViewportAction =
  | { type: 'zoomIn' }
  | { type: 'zoomOut' }
  | { type: 'rotateLeft' }
  | { type: 'rotateRight' }
  | { type: 'setBrightness'; value: number }
  | { type: 'setContrast'; value: number }
  | { type: 'pan'; dx: number; dy: number }
  | { type: 'togglePan' }
  | { type: 'flipHorizontal' }
  | { type: 'flipVertical' }
  | { type: 'reset' };

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));
/** Normaliza un ángulo a [0, 360). */
const norm = (deg: number) => ((deg % 360) + 360) % 360;
/** Redondea a 2 decimales (evita deriva de coma flotante en el scale). */
const round2 = (v: number) => Math.round(v * 100) / 100;

export function viewportReducer(state: ViewportState, action: ViewportAction): ViewportState {
  switch (action.type) {
    case 'zoomIn':
      return { ...state, scale: round2(clamp(state.scale + SCALE_STEP, SCALE_MIN, SCALE_MAX)) };
    case 'zoomOut':
      return { ...state, scale: round2(clamp(state.scale - SCALE_STEP, SCALE_MIN, SCALE_MAX)) };
    case 'rotateLeft':
      return { ...state, rotation: norm(state.rotation - ROTATE_STEP) };
    case 'rotateRight':
      return { ...state, rotation: norm(state.rotation + ROTATE_STEP) };
    case 'setBrightness':
      return { ...state, brightness: clamp(Math.round(action.value), FILTER_MIN, FILTER_MAX) };
    case 'setContrast':
      return { ...state, contrast: clamp(Math.round(action.value), FILTER_MIN, FILTER_MAX) };
    case 'pan':
      return { ...state, offsetX: state.offsetX + action.dx, offsetY: state.offsetY + action.dy };
    case 'togglePan':
      return { ...state, panMode: !state.panMode };
    case 'flipHorizontal':
      return { ...state, flipX: !state.flipX };
    case 'flipVertical':
      return { ...state, flipY: !state.flipY };
    case 'reset':
      return { ...INITIAL_VIEWPORT };
    default:
      return state;
  }
}

/** Porcentaje de zoom para el indicador (1 → "100%"). */
export function zoomPercent(scale: number): string {
  return `${Math.round(scale * 100)}%`;
}

/** String de CSS filter para brillo/contraste. */
export function cssFilter(state: Pick<ViewportState, 'brightness' | 'contrast'>): string {
  return `brightness(${state.brightness}%) contrast(${state.contrast}%)`;
}

/**
 * Escala con signo para el Stage de Konva: -1 en un eje lo dibuja en espejo.
 * Se combina con `scale` para no perder el zoom al voltear.
 */
export function stageScale(state: Pick<ViewportState, 'scale' | 'flipX' | 'flipY'>) {
  return {
    x: state.scale * (state.flipX ? -1 : 1),
    y: state.scale * (state.flipY ? -1 : 1),
  };
}
