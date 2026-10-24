import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Toast } from '../../src/clinic/components/Toast';

describe('Toast', () => {
  it('renderiza el mensaje', () => {
    render(<Toast message="Muestra creada" onDismiss={vi.fn()} />);
    expect(screen.getByText('Muestra creada')).toBeInTheDocument();
  });

  it('click en cerrar llama onDismiss', async () => {
    const onDismiss = vi.fn();
    render(<Toast message="X" onDismiss={onDismiss} />);
    await userEvent.click(screen.getByLabelText('Cerrar'));
    expect(onDismiss).toHaveBeenCalled();
  });

  it('se autodescarta después de autoDismissMs', async () => {
    vi.useFakeTimers();
    const onDismiss = vi.fn();
    render(<Toast message="X" onDismiss={onDismiss} autoDismissMs={1000} />);
    vi.advanceTimersByTime(1000);
    expect(onDismiss).toHaveBeenCalled();
    vi.useRealTimers();
  });

  it('aplica data-kind según el tipo', () => {
    render(<Toast message="Error" kind="error" onDismiss={vi.fn()} />);
    expect(screen.getByRole('status')).toHaveAttribute('data-kind', 'error');
  });
});
