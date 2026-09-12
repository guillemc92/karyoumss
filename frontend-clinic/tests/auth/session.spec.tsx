import { describe, expect, it, vi, afterEach } from 'vitest';
import { act, render, renderHook, screen, waitFor } from '@testing-library/react';
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

// ---------------------------------------------------------------------------
// Renovación automática dentro del SPA clínico
//
// El temporizador de refresco vivía solo en el AuthProvider de frontend-admin.
// Al navegar a /clinic/ la página se recarga y ese temporizador desaparece, así
// que la sesión moría a los 30 minutos en mitad del trabajo. Esto cubre el
// temporizador propio del clínico.
// ---------------------------------------------------------------------------

function tokenQueExpiraEn(segundos: number): string {
  const exp = Math.floor(Date.now() / 1000) + segundos;
  const payload = btoa(JSON.stringify({ exp, role: 'analista', email: 'a@umss.bo' }));
  return `cabecera.${payload}.firma`;
}

describe('renovación automática de la sesión (SSO)', () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it('renueva el token antes de que expire, sin que el usuario haga nada', async () => {
    vi.useFakeTimers();
    localStorage.setItem('biomed.auth.access', tokenQueExpiraEn(1800));
    const renovar = vi.spyOn(authClient, 'renovarSesion')
      .mockResolvedValue(tokenQueExpiraEn(1800));

    renderHook(() => useSession(), {
      wrapper: ({ children }) => <SessionProvider>{children}</SessionProvider>,
    });

    expect(renovar).not.toHaveBeenCalled();
    // 30 min menos el margen de 60 s.
    await vi.advanceTimersByTimeAsync((1800 - 60) * 1000 + 10);
    expect(renovar).toHaveBeenCalled();
  });

  it('si falla la renovación pero al token le queda vida, NO echa al usuario', async () => {
    vi.useFakeTimers();
    localStorage.setItem('biomed.auth.access', tokenQueExpiraEn(1800));
    const renovar = vi.spyOn(authClient, 'renovarSesion').mockResolvedValue(null);

    const { result } = renderHook(() => useSession(), {
      wrapper: ({ children }) => <SessionProvider>{children}</SessionProvider>,
    });

    // `waitFor` gira sobre temporizadores REALES: con los falsos se cuelga.
    // `advanceTimersByTimeAsync` ya vacía los microtasks, así que basta con
    // envolverlo en act() y comprobar el estado directamente.
    await act(async () => {
      await vi.advanceTimersByTimeAsync((1800 - 60) * 1000 + 10);
    });
    expect(renovar).toHaveBeenCalled();
    // Un corte de red no es una sesión muerta: al token le quedan 60 s.
    expect(result.current.isAuthenticated).toBe(true);

    // Y reintenta en vez de rendirse.
    renovar.mockClear();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(31_000);
    });
    expect(renovar).toHaveBeenCalled();
  });

  it('cuando el token ya caducó y la renovación falla, cierra la sesión', async () => {
    vi.useFakeTimers();
    localStorage.setItem('biomed.auth.access', tokenQueExpiraEn(-10));
    vi.spyOn(authClient, 'renovarSesion').mockResolvedValue(null);

    const { result } = renderHook(() => useSession(), {
      wrapper: ({ children }) => <SessionProvider>{children}</SessionProvider>,
    });
    expect(result.current.isAuthenticated).toBe(true);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(50);
    });
    expect(result.current.isAuthenticated).toBe(false);
  });

  it('sin token no programa nada: no se llama a la red en la pantalla de login', async () => {
    vi.useFakeTimers();
    const renovar = vi.spyOn(authClient, 'renovarSesion');
    renderHook(() => useSession(), {
      wrapper: ({ children }) => <SessionProvider>{children}</SessionProvider>,
    });
    await vi.advanceTimersByTimeAsync(60 * 60 * 1000);
    expect(renovar).not.toHaveBeenCalled();
  });

  it('con un token ya caducado renueva de inmediato, no espera media hora', async () => {
    vi.useFakeTimers();
    localStorage.setItem('biomed.auth.access', tokenQueExpiraEn(-10));
    const renovar = vi.spyOn(authClient, 'renovarSesion')
      .mockResolvedValue(tokenQueExpiraEn(1800));

    renderHook(() => useSession(), {
      wrapper: ({ children }) => <SessionProvider>{children}</SessionProvider>,
    });
    await vi.advanceTimersByTimeAsync(10);
    expect(renovar).toHaveBeenCalled();
  });
});
