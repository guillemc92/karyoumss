import { describe, expect, it } from 'vitest';
import {
  INITIAL_VIEWPORT,
  stageScale,
  SCALE_MAX,
  SCALE_MIN,
  cssFilter,
  viewportReducer,
  zoomPercent,
} from '../../src/clinic/lib/viewport';

describe('viewport — reducer puro de herramientas de imagen (DD-KARYO-004)', () => {
  it('zoomIn/zoomOut cambian la escala en pasos', () => {
    const z1 = viewportReducer(INITIAL_VIEWPORT, { type: 'zoomIn' });
    expect(z1.scale).toBe(1.25);
    const z0 = viewportReducer(z1, { type: 'zoomOut' });
    expect(z0.scale).toBe(1);
  });

  it('zoom respeta los límites [SCALE_MIN, SCALE_MAX]', () => {
    let s = INITIAL_VIEWPORT;
    for (let i = 0; i < 20; i++) s = viewportReducer(s, { type: 'zoomIn' });
    expect(s.scale).toBe(SCALE_MAX);
    for (let i = 0; i < 40; i++) s = viewportReducer(s, { type: 'zoomOut' });
    expect(s.scale).toBe(SCALE_MIN);
  });

  it('rotateLeft/rotateRight normalizan el ángulo a [0,360)', () => {
    expect(viewportReducer(INITIAL_VIEWPORT, { type: 'rotateRight' }).rotation).toBe(15);
    expect(viewportReducer(INITIAL_VIEWPORT, { type: 'rotateLeft' }).rotation).toBe(345);
  });

  it('setBrightness/setContrast se acotan a [50,150]', () => {
    expect(viewportReducer(INITIAL_VIEWPORT, { type: 'setBrightness', value: 999 }).brightness).toBe(150);
    expect(viewportReducer(INITIAL_VIEWPORT, { type: 'setContrast', value: 0 }).contrast).toBe(50);
    expect(viewportReducer(INITIAL_VIEWPORT, { type: 'setBrightness', value: 120 }).brightness).toBe(120);
  });

  it('pan acumula el offset', () => {
    const s1 = viewportReducer(INITIAL_VIEWPORT, { type: 'pan', dx: 10, dy: -5 });
    const s2 = viewportReducer(s1, { type: 'pan', dx: 3, dy: 5 });
    expect(s2).toMatchObject({ offsetX: 13, offsetY: 0 });
  });

  it('togglePan alterna el modo mover', () => {
    expect(viewportReducer(INITIAL_VIEWPORT, { type: 'togglePan' }).panMode).toBe(true);
  });

  it('reset vuelve al estado inicial', () => {
    let s = viewportReducer(INITIAL_VIEWPORT, { type: 'zoomIn' });
    s = viewportReducer(s, { type: 'rotateRight' });
    s = viewportReducer(s, { type: 'pan', dx: 50, dy: 50 });
    expect(viewportReducer(s, { type: 'reset' })).toEqual(INITIAL_VIEWPORT);
  });

  it('acción desconocida devuelve el mismo estado', () => {
    // @ts-expect-error acción inválida a propósito
    expect(viewportReducer(INITIAL_VIEWPORT, { type: 'nope' })).toBe(INITIAL_VIEWPORT);
  });

  it('zoomPercent y cssFilter formatean correctamente', () => {
    expect(zoomPercent(1)).toBe('100%');
    expect(zoomPercent(1.5)).toBe('150%');
    expect(cssFilter({ brightness: 120, contrast: 90 })).toBe('brightness(120%) contrast(90%)');
  });
});

describe('voltear — transformación de vista', () => {
  it('el espejo horizontal alterna y no toca el resto del estado', () => {
    const volteado = viewportReducer(INITIAL_VIEWPORT, { type: 'flipHorizontal' });

    expect(volteado.flipX).toBe(true);
    expect(volteado.flipY).toBe(false);
    expect(volteado.scale).toBe(INITIAL_VIEWPORT.scale);
    expect(volteado.rotation).toBe(INITIAL_VIEWPORT.rotation);
  });

  it('voltear dos veces vuelve al original', () => {
    const ida = viewportReducer(INITIAL_VIEWPORT, { type: 'flipVertical' });
    const vuelta = viewportReducer(ida, { type: 'flipVertical' });

    expect(vuelta.flipY).toBe(false);
  });

  it('stageScale devuelve escala con signo sin perder el zoom', () => {
    const conZoom = { scale: 2, flipX: true, flipY: false };

    expect(stageScale(conZoom)).toEqual({ x: -2, y: 2 });
  });

  it('sin voltear, stageScale es la escala tal cual', () => {
    expect(stageScale({ scale: 1.5, flipX: false, flipY: false })).toEqual({ x: 1.5, y: 1.5 });
  });

  it('restablecer deshace también el volteo', () => {
    const volteado = viewportReducer(
      viewportReducer(INITIAL_VIEWPORT, { type: 'flipHorizontal' }),
      { type: 'flipVertical' },
    );

    const limpio = viewportReducer(volteado, { type: 'reset' });

    expect(limpio.flipX).toBe(false);
    expect(limpio.flipY).toBe(false);
  });
});
