import type { ReactElement, ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { render } from '@testing-library/react';
import { SessionProvider } from '../src/clinic/auth';

interface RenderOptions {
  route?: string;
  /** Si true, fuerza sesión de rol admin (útil para ejercitar RequireRole). */
  asAdmin?: boolean;
}

export function renderWithProviders(ui: ReactElement, { route = '/clinic/samples', asAdmin = false }: RenderOptions = {}) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });

  if (asAdmin) {
    localStorage.setItem('biomed.clinic.access', 'mock-access-token');
    localStorage.setItem('biomed.clinic.refresh', 'mock-refresh-token');
    localStorage.setItem('biomed.clinic.role', 'admin');
    localStorage.setItem('biomed.clinic.username', 'demo_admin');
  }

  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <SessionProvider forceAnalystOnMount={!asAdmin}>
          <MemoryRouter initialEntries={[route]}>{children}</MemoryRouter>
        </SessionProvider>
      </QueryClientProvider>
    );
  }

  return render(ui, { wrapper: Wrapper });
}
