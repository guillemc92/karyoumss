/**
 * authClient — wrapper HTTP del login unificado (ADR-0017, SPEC-010).
 *
 * Endpoints:
 *   POST /api/auth/login/    {email, password} → {access, refresh, role, email, full_name}
 *   POST /api/auth/logout/   {refresh} → 205 (blacklist)
 *   POST /api/auth/refresh/  {refresh} → {access, refresh}
 *   GET  /api/auth/me/       Authorization: Bearer <access> → {email, role, full_name, username}
 */
import { AuthApiException, type LoginResponse, type MeResponse } from './types';

const API_BASE = (import.meta.env.VITE_AUTH_API_BASE as string | undefined) ?? '/api/auth';

const ACCESS_KEY = 'biomed.auth.access';
const REFRESH_KEY = 'biomed.auth.refresh';

function safeGet(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function safeSet(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    // localStorage no disponible (modo privado / SSR / tests) — ignorar
  }
}

function safeRemove(key: string): void {
  try {
    localStorage.removeItem(key);
  } catch {
    // ignorar
  }
}

export function getAccessToken(): string | null {
  return safeGet(ACCESS_KEY);
}

export function getRefreshToken(): string | null {
  return safeGet(REFRESH_KEY);
}

export function isAuthenticated(): boolean {
  return getAccessToken() !== null;
}

export function clearTokens(): void {
  safeRemove(ACCESS_KEY);
  safeRemove(REFRESH_KEY);
}

function storeTokens(access: string, refresh: string): void {
  safeSet(ACCESS_KEY, access);
  safeSet(REFRESH_KEY, refresh);
}

export async function login(email: string, password: string): Promise<LoginResponse> {
  const res = await fetch(`${API_BASE}/login/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    throw new AuthApiException('Credenciales inválidas', res.status);
  }
  const data: LoginResponse = await res.json();
  storeTokens(data.access, data.refresh);
  return data;
}

export async function refresh(): Promise<string | null> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return null;
  const res = await fetch(`${API_BASE}/refresh/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh: refreshToken }),
  });
  if (!res.ok) {
    clearTokens();
    return null;
  }
  const data = await res.json();
  safeSet(ACCESS_KEY, data.access);
  if (data.refresh) safeSet(REFRESH_KEY, data.refresh);
  return data.access as string;
}

export async function logout(): Promise<void> {
  const access = getAccessToken();
  const refreshToken = getRefreshToken();
  if (access && refreshToken) {
    try {
      await fetch(`${API_BASE}/logout/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${access}`,
        },
        body: JSON.stringify({ refresh: refreshToken }),
      });
    } catch {
      // Logout es best-effort del lado servidor (blacklist) — el cliente
      // siempre limpia sus tokens locales, incluso si la request falla.
    }
  }
  clearTokens();
}

export async function me(): Promise<MeResponse | null> {
  const access = getAccessToken();
  if (!access) return null;
  const res = await fetch(`${API_BASE}/me/`, {
    headers: { Authorization: `Bearer ${access}` },
  });
  if (!res.ok) return null;
  return res.json();
}

/** Decodifica el claim `exp` (segundos epoch) de un JWT sin verificar la firma. */
export function decodeExp(token: string): number | null {
  try {
    const payload = token.split('.')[1];
    const json = JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/')));
    return typeof json.exp === 'number' ? json.exp : null;
  } catch {
    return null;
  }
}
