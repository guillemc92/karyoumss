import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import * as authClient from '../../src/admin/auth/authClient';

const DEMO_ADMIN = { email: 'demo_admin@biomed.umss.bo', password: 'demo12345' };

describe('authClient (ADR-0017)', () => {
  beforeEach(() => {
    authClient.clearTokens();
  });
  afterEach(() => {
    authClient.clearTokens();
  });

  it('isAuthenticated es false sin tokens', () => {
    expect(authClient.isAuthenticated()).toBe(false);
  });

  it('login exitoso guarda tokens y devuelve role/email/full_name', async () => {
    const data = await authClient.login(DEMO_ADMIN.email, DEMO_ADMIN.password);
    expect(data.role).toBe('admin');
    expect(data.email).toBe(DEMO_ADMIN.email);
    expect(authClient.isAuthenticated()).toBe(true);
    expect(authClient.getAccessToken()).toBe(data.access);
  });

  it('login con credenciales inválidas lanza AuthApiException y no guarda tokens', async () => {
    await expect(authClient.login('no-existe@biomed.umss.bo', 'x')).rejects.toThrow();
    expect(authClient.isAuthenticated()).toBe(false);
  });

  it('me() sin token devuelve null sin hacer fetch', async () => {
    expect(await authClient.me()).toBeNull();
  });

  it('me() con token válido devuelve los datos del usuario', async () => {
    await authClient.login(DEMO_ADMIN.email, DEMO_ADMIN.password);
    const me = await authClient.me();
    expect(me?.email).toBe(DEMO_ADMIN.email);
    expect(me?.role).toBe('admin');
  });

  it('refresh() sin refresh token devuelve null', async () => {
    expect(await authClient.refresh()).toBeNull();
  });

  it('refresh() con token válido devuelve un nuevo access y lo persiste', async () => {
    await authClient.login(DEMO_ADMIN.email, DEMO_ADMIN.password);
    const before = authClient.getAccessToken();
    const newAccess = await authClient.refresh();
    expect(newAccess).not.toBeNull();
    expect(authClient.getAccessToken()).toBe(newAccess);
    expect(newAccess).not.toBe(before);
  });

  it('logout limpia los tokens locales', async () => {
    await authClient.login(DEMO_ADMIN.email, DEMO_ADMIN.password);
    await authClient.logout();
    expect(authClient.isAuthenticated()).toBe(false);
    expect(authClient.getAccessToken()).toBeNull();
  });

  it('refresh() tras logout falla y limpia tokens (blacklist real vía MSW)', async () => {
    await authClient.login(DEMO_ADMIN.email, DEMO_ADMIN.password);
    const refreshToken = authClient.getRefreshToken();
    await authClient.logout();
    // Reinyectamos el refresh ya blacklisteado para simular un intento posterior.
    localStorage.setItem('biomed.auth.refresh', refreshToken as string);
    expect(await authClient.refresh()).toBeNull();
    expect(authClient.isAuthenticated()).toBe(false);
  });

  it('decodeExp lee el claim exp de un JWT válido', async () => {
    const data = await authClient.login(DEMO_ADMIN.email, DEMO_ADMIN.password);
    const exp = authClient.decodeExp(data.access);
    expect(exp).not.toBeNull();
    expect(exp as number).toBeGreaterThan(Date.now() / 1000);
  });

  it('decodeExp devuelve null para un token malformado', () => {
    expect(authClient.decodeExp('no-es-un-jwt')).toBeNull();
  });
});
