import { describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { render } from '@testing-library/react';
import { DegradedBanner } from '../../src/clinic/components/DegradedBanner';

function renderBanner(props: Partial<React.ComponentProps<typeof DegradedBanner>> = {}) {
  return render(
    <MemoryRouter>
      <DegradedBanner {...props} />
    </MemoryRouter>,
  );
}

describe('DegradedBanner', () => {
  it('renderiza el mensaje de pipeline no disponible', () => {
    renderBanner();
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText(/Pipeline de IA no disponible/)).toBeInTheDocument();
  });

  it('click en Reintentar llama onRetry', async () => {
    const onRetry = vi.fn();
    renderBanner({ onRetry });
    await userEvent.click(screen.getByText('↻ Reintentar'));
    expect(onRetry).toHaveBeenCalled();
  });

  it('click en cerrar llama onDismiss', async () => {
    const onDismiss = vi.fn();
    renderBanner({ onDismiss });
    await userEvent.click(screen.getByLabelText('Cerrar'));
    expect(onDismiss).toHaveBeenCalled();
  });
});
