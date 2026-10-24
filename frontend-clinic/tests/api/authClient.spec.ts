import { describe, expect, it, beforeEach, vi } from 'vitest';
import * as authClient from '../../src/clinic/api/authClient';

beforeEach(() => {
  localStorage.clear();
});

describe('authClient', () => {
  it('login() guarda access y refresh en localStorage', async () => {
    const result = await authClient.login('demo_analista', 'demo12345');
    expect(result.access).toBeTruthy();
    expect(localStorage.getItem('biomed.clinic.access')).toBe(result.access);
    expect(localStorage.getItem('biomed.clinic.refresh')).toBe(result.refresh);
  });

  it('login() con credenciales vacías lanza excepción', async () => {
    await expect(authClient.login('', '')).rejects.toMatchObject({ status: 400 });
  });

  it('isAuthenticated() es false sin token', () => {
    expect(authClient.isAuthenticated()).toBe(false);
  });

  it('isAuthenticated() es true tras login', async () => {
    await authClient.login('demo_analista', 'demo12345');
    expect(authClient.isAuthenticated()).toBe(true);
  });

  it('logout() limpia los tokens', async () => {
    await authClient.login('demo_analista', 'demo12345');
    authClient.logout();
    expect(authClient.getAccessToken()).toBeNull();
  });

  it('refresh() sin refresh token guardado retorna null', async () => {
    const result = await authClient.refresh();
    expect(result).toBeNull();
  });

  it('refresh() con refresh token válido actualiza access', async () => {
    await authClient.login('demo_analista', 'demo12345');
    const newAccess = await authClient.refresh();
    expect(newAccess).toBeTruthy();
  });

  it('refresh() con refresh token inválido hace logout y retorna null', async () => {
    localStorage.setItem('biomed.clinic.access', 'stale-access');
    localStorage.setItem('biomed.clinic.refresh', 'stale-refresh');
    const spy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: 'Token inválido' }), { status: 401 }),
    );
    const result = await authClient.refresh();
    expect(result).toBeNull();
    expect(authClient.getAccessToken()).toBeNull();
    spy.mockRestore();
  });
});

// ---------------------------------------------------------------------------
// Renovación de la sesión SSO
//
// El refresco automático solo existía en frontend-admin, que es otra
// aplicación. Al entrar al SPA clínico su temporizador desaparecía y el token
// caducaba a los 30 minutos: «El token dado no es válido para ningún tipo de
// token». Estas pruebas cubren el camino que faltaba.
// ---------------------------------------------------------------------------

/** Construye un JWT de mentira con el `exp` pedido (solo se lee el payload). */
function tokenConExp(expSegundos: number): string {
  const payload = btoa(JSON.stringify({ exp: expSegundos, role: 'analista' }));
  return `cabecera.${payload}.firma`;
}

describe('renovarSesion (SSO, ADR-0020)', () => {
  it('sin refresh en el storage compartido devuelve null y no llama a la red', async () => {
    const spy = vi.spyOn(globalThis, 'fetch');
    expect(await authClient.renovarSesion()).toBeNull();
    expect(spy).not.toHaveBeenCalled();
    spy.mockRestore();
  });

  it('llama a backend-admin, NO a /api/clinic: la autoridad de JWT es admin', async () => {
    localStorage.setItem('biomed.auth.refresh', 'refresh-vigente');
    const spy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify({ access: 'access-nuevo' }), { status: 200 }),
    );
    await authClient.renovarSesion();
    expect(String(spy.mock.calls[0][0])).toBe('/api/auth/refresh/');
    spy.mockRestore();
  });

  it('guarda el access nuevo en el storage compartido', async () => {
    localStorage.setItem('biomed.auth.refresh', 'refresh-vigente');
    const spy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify({ access: 'access-nuevo' }), { status: 200 }),
    );
    expect(await authClient.renovarSesion()).toBe('access-nuevo');
    expect(authClient.getAccessToken()).toBe('access-nuevo');
    spy.mockRestore();
  });

  it('si el backend rota el refresh, guarda el nuevo: el viejo deja de servir', async () => {
    localStorage.setItem('biomed.auth.refresh', 'refresh-viejo');
    const spy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify({ access: 'a2', refresh: 'refresh-rotado' }), { status: 200 }),
    );
    await authClient.renovarSesion();
    expect(localStorage.getItem('biomed.auth.refresh')).toBe('refresh-rotado');
    spy.mockRestore();
  });

  it('con refresh caducado devuelve null y NO borra el access vigente', async () => {
    localStorage.setItem('biomed.auth.access', 'access-actual');
    localStorage.setItem('biomed.auth.refresh', 'refresh-caducado');
    const spy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: 'Token inválido' }), { status: 401 }),
    );
    expect(await authClient.renovarSesion()).toBeNull();
    // Quien decide cerrar sesión es el SessionProvider, no este cliente.
    expect(authClient.getAccessToken()).toBe('access-actual');
    spy.mockRestore();
  });

  it('una caída de red devuelve null sin lanzar: se reintenta en el próximo ciclo', async () => {
    localStorage.setItem('biomed.auth.refresh', 'refresh-vigente');
    const spy = vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new Error('sin red'));
    await expect(authClient.renovarSesion()).resolves.toBeNull();
    spy.mockRestore();
  });

  it('una respuesta 200 sin campo access no se da por buena', async () => {
    localStorage.setItem('biomed.auth.refresh', 'refresh-vigente');
    const spy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify({ vacio: true }), { status: 200 }),
    );
    expect(await authClient.renovarSesion()).toBeNull();
    spy.mockRestore();
  });
});

describe('decodeExp', () => {
  it('lee el exp del token', () => {
    expect(authClient.decodeExp(tokenConExp(1800000000))).toBe(1800000000);
  });

  it('devuelve null si el token no es un JWT', () => {
    expect(authClient.decodeExp('no-es-un-jwt')).toBeNull();
  });

  it('devuelve null si el payload no trae exp', () => {
    const sinExp = `cabecera.${btoa(JSON.stringify({ role: 'analista' }))}.firma`;
    expect(authClient.decodeExp(sinExp)).toBeNull();
  });
});
