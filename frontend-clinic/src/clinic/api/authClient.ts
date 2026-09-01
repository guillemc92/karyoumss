/**
 * SSO (ADR-0020, DD-SSO-001 §4.2-4.3): backend-admin es la ÚNICA
 * autoridad de JWT del sistema. El login real ocurre en frontend-admin;
 * este módulo YA NO llama a /api/clinic/auth/login/ (endpoint eliminado,
 * ver backend-clinic/clinic_backend/urls.py). login()/refresh() se
 * mantienen SOLO para el modo demo MSW (forceAnalystOnMount), que simula
 * una sesión sin depender de un backend-admin real corriendo — MSW
 * intercepta estas llamadas con datos de fixture (ver src/clinic/msw/handlers.ts).
 *
 * getAccessToken()/isAuthenticated() sí son el camino real: leen
 * 'biomed.auth.access', el mismo storage que frontend-admin escribe tras
 * el login único (mismo origen, compartido vía Caddyfile.dev en dev).
 */
import { ClinicApiException } from '../types/sample';

const API_BASE = import.meta.env.VITE_CLINIC_API_BASE ?? '/api/clinic';

/** Storage de sesión REAL, compartido con frontend-admin (SSO). */
const SESSION_ACCESS_KEY = 'biomed.auth.access';
/** Storage legacy, solo usado por login()/refresh() en modo demo MSW. */
const ACCESS_KEY = 'biomed.clinic.access';
const REFRESH_KEY = 'biomed.clinic.refresh';

export interface LoginResponse {
  access: string;
  refresh: string;
}

/** Solo para modo demo MSW — no llama al backend real (endpoint eliminado). */
export async function login(username: string, password: string): Promise<LoginResponse> {
  const res = await fetch(`${API_BASE}/auth/login/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) {
    throw new ClinicApiException('Credenciales inválidas', res.status, 'LOGIN_FAILED');
  }
  const data: LoginResponse = await res.json();
  // Modo demo MSW: escribe también en el storage de sesión real para que
  // el resto del flujo (getAccessToken) funcione sin distinguir MSW/real.
  localStorage.setItem(SESSION_ACCESS_KEY, data.access);
  localStorage.setItem(ACCESS_KEY, data.access);
  localStorage.setItem(REFRESH_KEY, data.refresh);
  return data;
}

/** Solo para modo demo MSW. */
export async function refresh(): Promise<string | null> {
  const refreshToken = localStorage.getItem(REFRESH_KEY);
  if (!refreshToken) return null;
  const res = await fetch(`${API_BASE}/auth/refresh/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh: refreshToken }),
  });
  if (!res.ok) {
    logout();
    return null;
  }
  const data = await res.json();
  localStorage.setItem(SESSION_ACCESS_KEY, data.access);
  localStorage.setItem(ACCESS_KEY, data.access);
  return data.access;
}

export function logout(): void {
  localStorage.removeItem(SESSION_ACCESS_KEY);
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

/** Camino real (SSO): lee el JWT de sesión que frontend-admin escribió. */
export function getAccessToken(): string | null {
  try {
    return localStorage.getItem(SESSION_ACCESS_KEY);
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Renovación de la sesión SSO
//
// El refresco automático vivía SOLO en el AuthProvider de frontend-admin, que
// es otra aplicación: al navegar a /clinic/ la página se recarga, ese
// temporizador muere, y aquí el token se leía sin renovarse nunca. A los 30
// minutos (ACCESS_TOKEN_LIFETIME en backend-admin) todo respondía
// «El token dado no es válido para ningún tipo de token».
//
// No se emite un token nuevo aquí: se llama al endpoint de backend-admin, que
// sigue siendo la única autoridad de JWT (ADR-0020). El refresh token se lee
// del storage compartido, que es legible porque Caddy sirve ambas SPA desde el
// mismo origen (DD-SSO-001 §4.1).
// ---------------------------------------------------------------------------

/** Storage de refresco REAL, escrito por frontend-admin en el login único. */
const SESSION_REFRESH_KEY = 'biomed.auth.refresh';

/** Base del backend-admin, NO de /api/clinic: la autoridad de JWT es admin. */
const AUTH_BASE = (import.meta.env.VITE_AUTH_API_BASE as string | undefined) ?? '/api/auth';

/** Segundos de margen para renovar antes de que el token expire de verdad. */
export const MARGEN_RENOVACION_SEGUNDOS = 60;

/** Lee el `exp` del JWT sin verificar firma (la valida el backend). */
export function decodeExp(token: string): number | null {
  const claims = decodeJwtPayload(token);
  return typeof claims?.exp === 'number' ? claims.exp : null;
}

function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const payload = token.split('.')[1];
    return JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/')));
  } catch {
    return null;
  }
}

/**
 * Renueva el access token contra backend-admin.
 * Devuelve el token nuevo, o null si no hay refresh o el backend lo rechaza.
 */
export async function renovarSesion(): Promise<string | null> {
  let refreshToken: string | null = null;
  try {
    refreshToken = localStorage.getItem(SESSION_REFRESH_KEY);
  } catch {
    return null;
  }
  if (!refreshToken) return null;

  let res: Response;
  try {
    res = await fetch(`${AUTH_BASE}/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh: refreshToken }),
    });
  } catch {
    // Caída de red: no se cierra la sesión, se reintentará en el próximo ciclo.
    return null;
  }
  if (!res.ok) return null;

  const data = await res.json();
  if (typeof data?.access !== 'string') return null;
  try {
    localStorage.setItem(SESSION_ACCESS_KEY, data.access);
    // La rotación de refresh está activada en backend-admin: si viene uno
    // nuevo, el viejo deja de servir y hay que guardarlo.
    if (typeof data.refresh === 'string') {
      localStorage.setItem(SESSION_REFRESH_KEY, data.refresh);
    }
  } catch {
    return null;
  }
  return data.access;
}

export function isAuthenticated(): boolean {
  return getAccessToken() !== null;
}
