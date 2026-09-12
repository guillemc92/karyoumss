import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { KaryoImageToolbar } from '../../src/clinic/components/KaryoImageToolbar';
import { INITIAL_VIEWPORT, SCALE_MAX, SCALE_MIN } from '../../src/clinic/lib/viewport';

function setup(overrides = {}) {
  const dispatch = vi.fn();
  const viewport = { ...INITIAL_VIEWPORT, ...overrides };
  render(<KaryoImageToolbar viewport={viewport} dispatch={dispatch} />);
  return { dispatch };
}

describe('KaryoImageToolbar (P4)', () => {
  it('muestra el nivel de zoom', () => {
    setup({ scale: 1.5 });
    expect(screen.getByTestId('viewport-zoom-level')).toHaveTextContent('150%');
  });

  it('zoom in/out despachan las acciones', async () => {
    const { dispatch } = setup();
    await userEvent.click(screen.getByTestId('viewport-zoom-in'));
    await userEvent.click(screen.getByTestId('viewport-zoom-out'));
    expect(dispatch).toHaveBeenCalledWith({ type: 'zoomIn' });
    expect(dispatch).toHaveBeenCalledWith({ type: 'zoomOut' });
  });

  it('rotar izq/der despachan las acciones', async () => {
    const { dispatch } = setup();
    await userEvent.click(screen.getByTestId('viewport-rotate-left'));
    await userEvent.click(screen.getByTestId('viewport-rotate-right'));
    expect(dispatch).toHaveBeenCalledWith({ type: 'rotateLeft' });
    expect(dispatch).toHaveBeenCalledWith({ type: 'rotateRight' });
  });

  it('el toggle de mover refleja panMode y despacha togglePan', async () => {
    const { dispatch } = setup({ panMode: true });
    const btn = screen.getByTestId('viewport-pan');
    expect(btn).toHaveAttribute('aria-pressed', 'true');
    await userEvent.click(btn);
    expect(dispatch).toHaveBeenCalledWith({ type: 'togglePan' });
  });

  it('los sliders de brillo/contraste despachan con el valor', async () => {
    const { dispatch } = setup();
    const brightness = screen.getByTestId('viewport-brightness');
    // range input: fireChange vía userEvent no siempre; usamos change directo.
    brightness.setAttribute('value', '130');
    const { fireEvent } = await import('@testing-library/react');
    fireEvent.change(brightness, { target: { value: '130' } });
    expect(dispatch).toHaveBeenCalledWith({ type: 'setBrightness', value: 130 });
  });

  it('reset despacha reset', async () => {
    const { dispatch } = setup();
    await userEvent.click(screen.getByTestId('viewport-reset'));
    expect(dispatch).toHaveBeenCalledWith({ type: 'reset' });
  });

  it('zoom in deshabilitado al máximo, zoom out al mínimo', () => {
    const { rerender } = render(<KaryoImageToolbar viewport={{ ...INITIAL_VIEWPORT, scale: SCALE_MAX }} dispatch={vi.fn()} />);
    expect(screen.getByTestId('viewport-zoom-in')).toBeDisabled();
    rerender(<KaryoImageToolbar viewport={{ ...INITIAL_VIEWPORT, scale: SCALE_MIN }} dispatch={vi.fn()} />);
    expect(screen.getByTestId('viewport-zoom-out')).toBeDisabled();
  });
});
