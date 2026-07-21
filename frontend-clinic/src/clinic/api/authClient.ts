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

export function isAuthenticated(): boolean {
  return getAccessToken() !== null;
}
