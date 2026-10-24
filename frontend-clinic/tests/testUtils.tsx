import type { ReactElement, ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { render } from '@testing-library/react';
import { SessionProvider } from '../src/clinic/auth';

interface RenderOptions {
  route?: string;
  /** Si true, fuerza sesión de rol admin (útil para ejercitar RequireRole). */
  asAdmin?: boolean;
  /** Si true, fuerza sesión de rol supervisor (flujo del Supervisor, S1). */
  asSupervisor?: boolean;
}

/** SSO (ADR-0020): SessionProvider decodifica role/email del payload del
 * JWT en 'biomed.auth.access' — un JWT falso con 3 segmentos alcanza
 * para tests (la firma no se verifica en el cliente). */
function fakeJwt(claims: Record<string, unknown>): string {
  const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
  const payload = btoa(JSON.stringify(claims));
  return `${header}.${payload}.mock-signature`;
}

export function renderWithProviders(ui: ReactElement, { route = '/clinic/samples', asAdmin = false, asSupervisor = false }: RenderOptions = {}) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });

  if (asAdmin) {
    localStorage.setItem('biomed.auth.access', fakeJwt({ email: 'demo_admin', role: 'admin' }));
  } else if (asSupervisor) {
    localStorage.setItem('biomed.auth.access', fakeJwt({ email: 'demo_sup', role: 'supervisor' }));
  }

  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <SessionProvider forceAnalystOnMount={!asAdmin && !asSupervisor}>
          <MemoryRouter initialEntries={[route]}>{children}</MemoryRouter>
        </SessionProvider>
      </QueryClientProvider>
    );
  }

  return render(ui, { wrapper: Wrapper });
}
