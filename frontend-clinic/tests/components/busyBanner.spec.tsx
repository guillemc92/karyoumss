import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen } from '@testing-library/react';
import { BusyBanner } from '../../src/clinic/components/BusyBanner';

describe('BusyBanner', () => {
  beforeEach(() => { vi.useFakeTimers(); });
  afterEach(() => { vi.useRealTimers(); });

  it('es un aviso, no una alerta, y dice que la muestra no cambió', () => {
    render(<BusyBanner seconds={25} onRetry={() => {}} />);
    const aviso = screen.getByRole('status');
    expect(aviso).toHaveTextContent('procesando otro caso');
    expect(aviso).toHaveTextContent('Su muestra no cambió');
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('cuenta hacia atrás un segundo cada segundo', () => {
    render(<BusyBanner seconds={3} onRetry={() => {}} />);
    expect(screen.getByRole('status')).toHaveTextContent('reintentar en 3 s');
    act(() => { vi.advanceTimersByTime(1000); });
    expect(screen.getByRole('status')).toHaveTextContent('reintentar en 2 s');
    act(() => { vi.advanceTimersByTime(1000); });
    expect(screen.getByRole('status')).toHaveTextContent('reintentar en 1 s');
  });

  it('al llegar a cero dice que ya puede reintentar, y no baja de cero', () => {
    render(<BusyBanner seconds={2} onRetry={() => {}} />);
    act(() => { vi.advanceTimersByTime(2000); });
    expect(screen.getByRole('status')).toHaveTextContent('Ya puede reintentar');
    act(() => { vi.advanceTimersByTime(5000); });
    expect(screen.getByRole('status')).toHaveTextContent('Ya puede reintentar');
    expect(screen.getByRole('status')).not.toHaveTextContent('-');
  });

  it('una espera nueva reinicia la cuenta', () => {
    const { rerender } = render(<BusyBanner seconds={2} onRetry={() => {}} />);
    act(() => { vi.advanceTimersByTime(2000); });
    rerender(<BusyBanner seconds={9} onRetry={() => {}} />);
    expect(screen.getByRole('status')).toHaveTextContent('reintentar en 9 s');
  });

  it('Reintentar se puede pulsar sin esperar a que acabe la cuenta', () => {
    const onRetry = vi.fn();
    render(<BusyBanner seconds={25} onRetry={onRetry} />);
    fireEvent.click(screen.getByText('↻ Reintentar'));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it('sin onDismiss no hay botón de cerrar', () => {
    render(<BusyBanner seconds={25} onRetry={() => {}} />);
    expect(screen.queryByLabelText('Cerrar')).not.toBeInTheDocument();
  });

  it('con onDismiss, Cerrar lo llama', () => {
    const onDismiss = vi.fn();
    render(<BusyBanner seconds={25} onRetry={() => {}} onDismiss={onDismiss} />);
    fireEvent.click(screen.getByLabelText('Cerrar'));
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });
});
