import { describe, expect, it, vi } from 'vitest';
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
