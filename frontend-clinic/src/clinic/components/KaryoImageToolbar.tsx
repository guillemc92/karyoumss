/**
 * KaryoImageToolbar — herramientas de imagen del cariograma (P4, DD-KARYO-004
 * §3.1). Barra superior del visor: zoom, pan, rotar, brillo, contraste, reset.
 * Espejo de la toolbar del prototipo `correccion de cariotipo.html`.
 *
 * No lleva estado propio: emite acciones al reducer `viewport` de la página.
 */
import type { Dispatch } from 'react';
import type { ViewportAction, ViewportState } from '../lib/viewport';
import { SCALE_MAX, SCALE_MIN, zoomPercent } from '../lib/viewport';

interface Props {
  viewport: ViewportState;
  dispatch: Dispatch<ViewportAction>;
  /** Deshabilita todo (p.ej. mientras carga o si el caso está validado). */
  disabled?: boolean;
}

export function KaryoImageToolbar({ viewport, dispatch, disabled = false }: Props) {
  return (
    <div className="karyo-imagebar" data-testid="karyo-imagebar" role="toolbar" aria-label="Herramientas de imagen">
      <div className="karyo-imagebar__group">
        <button type="button" className="tool-icon" data-testid="viewport-zoom-out"
          onClick={() => dispatch({ type: 'zoomOut' })} disabled={disabled || viewport.scale <= SCALE_MIN}
          title="Alejar" aria-label="Alejar">🔍−</button>
        <span className="karyo-imagebar__zoom" data-testid="viewport-zoom-level">{zoomPercent(viewport.scale)}</span>
        <button type="button" className="tool-icon" data-testid="viewport-zoom-in"
          onClick={() => dispatch({ type: 'zoomIn' })} disabled={disabled || viewport.scale >= SCALE_MAX}
          title="Acercar" aria-label="Acercar">🔍+</button>
      </div>

      <div className="karyo-imagebar__group">
        <button type="button" className={`tool-icon${viewport.panMode ? ' tool-icon--active' : ''}`} data-testid="viewport-pan"
          onClick={() => dispatch({ type: 'togglePan' })} disabled={disabled}
          aria-pressed={viewport.panMode} title="Mover (arrastrar el lienzo)" aria-label="Mover">✥</button>
        <button type="button" className="tool-icon" data-testid="viewport-rotate-left"
          onClick={() => dispatch({ type: 'rotateLeft' })} disabled={disabled} title="Rotar izquierda" aria-label="Rotar izquierda">↺</button>
        <button type="button" className="tool-icon" data-testid="viewport-rotate-right"
          onClick={() => dispatch({ type: 'rotateRight' })} disabled={disabled} title="Rotar derecha" aria-label="Rotar derecha">↻</button>
        {/* Voltear es transformación de VISTA: no altera la orientación
            guardada de ningún cromosoma. Por convención ISCN el brazo corto (p)
            se dibuja arriba, y comparar un cromosoma capturado al revés es más
            fácil volteando el lienzo que girando la cabeza. */}
        <button type="button" className={`tool-icon${viewport.flipX ? ' tool-icon--active' : ''}`} data-testid="viewport-flip-h"
          onClick={() => dispatch({ type: 'flipHorizontal' })} disabled={disabled}
          aria-pressed={viewport.flipX} title="Voltear horizontal (solo la vista)" aria-label="Voltear horizontal">⇄</button>
        <button type="button" className={`tool-icon${viewport.flipY ? ' tool-icon--active' : ''}`} data-testid="viewport-flip-v"
          onClick={() => dispatch({ type: 'flipVertical' })} disabled={disabled}
          aria-pressed={viewport.flipY} title="Voltear vertical (solo la vista)" aria-label="Voltear vertical">⇅</button>
      </div>

      <label className="karyo-imagebar__slider">
        ☀ <input type="range" min={50} max={150} value={viewport.brightness} data-testid="viewport-brightness"
          disabled={disabled} onChange={(e) => dispatch({ type: 'setBrightness', value: Number(e.target.value) })}
          aria-label="Brillo" />
      </label>
      <label className="karyo-imagebar__slider">
        ◐ <input type="range" min={50} max={150} value={viewport.contrast} data-testid="viewport-contrast"
          disabled={disabled} onChange={(e) => dispatch({ type: 'setContrast', value: Number(e.target.value) })}
          aria-label="Contraste" />
      </label>

      <button type="button" className="btn-outline" data-testid="viewport-reset"
        onClick={() => dispatch({ type: 'reset' })} disabled={disabled} title="Restablecer vista">Restablecer</button>
    </div>
  );
}
