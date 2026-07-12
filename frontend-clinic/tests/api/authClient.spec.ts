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
