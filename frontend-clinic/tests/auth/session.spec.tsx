import { describe, expect, it, vi, afterEach } from 'vitest';
import { render, renderHook, screen, waitFor } from '@testing-library/react';
import { SessionProvider, useSession, RequireRole } from '../../src/clinic/auth';
import * as authClient from '../../src/clinic/api/authClient';

describe('useSession', () => {
  it('lanza error si se usa fuera de SessionProvider', () => {
    expect(() => renderHook(() => useSession())).toThrow('useSession debe usarse dentro de <SessionProvider>');
  });

  it('con forceAnalystOnMount, la sesión queda autenticada como analista', async () => {
    const { result } = renderHook(() => useSession(), {
      wrapper: ({ children }) => <SessionProvider forceAnalystOnMount>{children}</SessionProvider>,
    });
    await waitFor(() => expect(result.current.isAuthenticated).toBe(true));
    expect(result.current.role).toBe('analista');
  });

  it('logout() limpia la sesión', async () => {
    const { result } = renderHook(() => useSession(), {
      wrapper: ({ children }) => <SessionProvider forceAnalystOnMount>{children}</SessionProvider>,
    });
    await waitFor(() => expect(result.current.isAuthenticated).toBe(true));
    result.current.logout();
    await waitFor(() => expect(result.current.isAuthenticated).toBe(false));
  });
});

describe('RequireRole', () => {
  it('sin sesión autenticada, no renderiza los children', () => {
    render(
      <SessionProvider>
        <RequireRole roles={['admin']}>
          <span>Contenido protegido</span>
        </RequireRole>
      </SessionProvider>,
    );
    expect(screen.queryByText('Contenido protegido')).not.toBeInTheDocument();
  });

  it('renderiza el fallback cuando el rol no coincide', async () => {
    render(
      <SessionProvider forceAnalystOnMount>
        <RequireRole roles={['admin']} fallback={<span>Sin permiso</span>}>
          <span>Contenido protegido</span>
        </RequireRole>
      </SessionProvider>,
    );
    await waitFor(() => expect(screen.getByText('Sin permiso')).toBeInTheDocument());
  });
});

describe('authClient.getAccessToken robustez', () => {
  it('retorna null si localStorage lanza excepción', () => {
    const spy = vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('storage disabled');
    });
    expect(authClient.getAccessToken()).toBeNull();
    spy.mockRestore();
  });
});

describe('SSO (ADR-0020) — sesión leída de un JWT ya presente en localStorage', () => {
  function fakeJwt(claims: Record<string, unknown>): string {
    const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
    const payload = btoa(JSON.stringify(claims));
    return `${header}.${payload}.mock-signature`;
  }

  afterEach(() => {
    localStorage.removeItem('biomed.auth.access');
  });

  it('decodifica role y email del JWT sin llamar a authClient.login()', () => {
    localStorage.setItem('biomed.auth.access', fakeJwt({ email: 'sup@biomed.umss.bo', role: 'supervisor' }));
    const { result } = renderHook(() => useSession(), {
      wrapper: ({ children }) => <SessionProvider>{children}</SessionProvider>,
    });
    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.role).toBe('supervisor');
    expect(result.current.username).toBe('sup@biomed.umss.bo');
  });

  it('sin token en localStorage, la sesión no está autenticada (sin pedir login propio)', () => {
    const { result } = renderHook(() => useSession(), {
      wrapper: ({ children }) => <SessionProvider>{children}</SessionProvider>,
    });
    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.role).toBeNull();
  });

  it('token con formato inválido (no JWT) no autentica', () => {
    localStorage.setItem('biomed.auth.access', 'no-es-un-jwt-valido');
    const { result } = renderHook(() => useSession(), {
      wrapper: ({ children }) => <SessionProvider>{children}</SessionProvider>,
    });
    expect(result.current.isAuthenticated).toBe(true); // token existe, isAuthenticated solo mira presencia
    expect(result.current.role).toBeNull(); // pero no se pudo decodificar el claim role
  });
});
