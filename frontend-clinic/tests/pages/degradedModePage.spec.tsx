import { describe, expect, it } from 'vitest';
import { screen } from '@testing-library/react';
import { DegradedModePage } from '../../src/clinic/pages/DegradedModePage';
import { renderWithProviders } from '../testUtils';

describe('DegradedModePage', () => {
  it('renderiza el encabezado de modo degradado', () => {
    renderWithProviders(<DegradedModePage />);
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText(/Modo Degradado/)).toBeInTheDocument();
  });

  it('lista las instrucciones de análisis manual', () => {
    renderWithProviders(<DegradedModePage />);
    expect(screen.getByText(/análisis manual/)).toBeInTheDocument();
  });

  it('tiene un link de vuelta a la lista de muestras', () => {
    renderWithProviders(<DegradedModePage />);
    const link = screen.getByText(/Volver a la lista/);
    expect(link.closest('a')).toHaveAttribute('href', '/clinic/samples');
  });
});
