import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { AuthProvider } from '../../src/admin/auth/AuthContext';
import { PrivateRoute } from '../../src/admin/auth/PrivateRoute';
import * as authClient from '../../src/admin/auth/authClient';
import { getRedirectForRole } from '../../src/admin/auth/roleRedirect';

function Protected() {
  return <div data-testid="protected">contenido protegido</div>;
}

function LoginStub() {
  return <div data-testid="login-stub">login</div>;
}

function renderAt(path: string, allowedRoles: Array<'admin' | 'analista' | 'supervisor'>) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginStub />} />
          <Route
            path="/*"
            element={
              <PrivateRoute allowedRoles={allowedRoles}>
                <Protected />
              </PrivateRoute>
            }
          />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe('PrivateRoute (ADR-0017)', () => {
  const originalLocation = window.location;

  beforeEach(() => {
    authClient.clearTokens();
    // roleRedirect usa window.location.href para navegar fuera de la SPA
    // (cross-app). jsdom no implementa navigation real; lo stubbeamos para
    // observar el intento SIN romper la resolución de URLs relativas que
    // fetch/MSW necesitan (por eso href arranca en un origin válido, no '').
    // @ts-expect-error -- reemplazo deliberado para test
    delete window.location;
    // @ts-expect-error -- stub mínimo
    window.location = { href: 'http://localhost:3000/' };
  });

  afterEach(() => {
    authClient.clearTokens();
    window.location = originalLocation;
  });

  it('sin sesión redirige a /login', async () => {
    renderAt('/', ['admin']);
    await waitFor(() => expect(screen.getByTestId('login-stub')).toBeInTheDocument());
    expect(screen.queryByTestId('protected')).not.toBeInTheDocument();
  });

  it('con sesión y rol permitido renderiza el contenido protegido', async () => {
    await authClient.login('demo_admin@biomed.umss.bo', 'demo12345');
    renderAt('/', ['admin']);
    await waitFor(() => expect(screen.getByTestId('protected')).toBeInTheDocument());
  });

  it('con sesión pero rol no permitido (con destino externo) navega fuera vía roleRedirect', async () => {
    // demo_supervisor no está en allowedRoles=['admin'] → roleRedirect da un
    // destino no-nulo → PrivateRoute navega afuera en vez de mostrar el
    // contenido protegido de esta SPA.
    //
    // Se compara contra el destino que devuelve roleRedirect, no contra un
    // literal: ese valor lo fija `VITE_SUPERVISOR_LEGACY_URL` desde un `.env`
    // local y gitignored. Afirmar el literal hacía que la prueba fallara en la
    // máquina del desarrollador y pasara en cualquier otra.
    const destino = getRedirectForRole('supervisor') as string;
    await authClient.login('demo_supervisor@biomed.umss.bo', 'demo12345');
    renderAt('/', ['admin']);
    await waitFor(() => expect(window.location.href).toContain(destino));
    expect(screen.queryByTestId('protected')).not.toBeInTheDocument();
  });

  it('con sesión pero rol no permitido sin destino externo (admin) redirige a /login', async () => {
    await authClient.login('demo_admin@biomed.umss.bo', 'demo12345');
    renderAt('/', ['supervisor']);
    await waitFor(() => expect(screen.getByTestId('login-stub')).toBeInTheDocument());
    expect(screen.queryByTestId('protected')).not.toBeInTheDocument();
  });
});
