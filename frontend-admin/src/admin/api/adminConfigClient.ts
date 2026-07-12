/**
 * adminConfigClient — wrapper HTTP para el bounded context config.
 *
 * DD-ADMIN-002 §2 — P1: GET/PATCH /api/admin/me/profile/.
 *
 * P2–P6 añadirán métodos para security, models, notifications,
 * integrations, appearance. P0 ya tenía config_health (no expuesto
 * al cliente, smoke check interno).
 *
 * Reutiliza el patrón de adminClient.ts: token DRF en localStorage,
 * parseo de errores con discriminador `kind`, AbortSignal opcional.
 * La diferencia con adminClient es que la base URL sigue siendo
 * `/api/admin` (mismo backend) y los endpoints son distintos.
 */
import {
  AdminApiError,
  AdminApiException,
} from '../types/adminUser';
import {
  AdminProfile,
  AdminProfileUpdate,
} from '../types/config';

const DEFAULT_BASE_URL =
  (import.meta.env.VITE_ADMIN_API_BASE as string | undefined) ?? '/api/admin';

const TOKEN_STORAGE_KEY = 'biomed.admin.token';

function safeReadToken(): string | null {
  if (typeof window === 'undefined') return null;
  try {
    return window.localStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE';
  body?: unknown;
  signal?: AbortSignal;
}

function buildUrl(base: string, path: string): string {
  const cleanBase = base.endsWith('/') ? base.slice(0, -1) : base;
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return `${cleanBase}${cleanPath}`;
}

async function parseError(status: number, payload: unknown): Promise<AdminApiError> {
  const detail =
    typeof payload === 'object' && payload !== null && 'detail' in payload
      ? String((payload as { detail: unknown }).detail)
      : '';

  if (status === 401) return { kind: 'unauthorized', message: detail || 'No autenticado' };
  if (status === 403) return { kind: 'forbidden', message: detail || 'Acceso denegado' };
  if (status === 404) return { kind: 'not_found', message: detail || 'Recurso no encontrado' };
  if (status === 409) return { kind: 'conflict', message: detail || 'Conflicto', detail };
  if (status === 400) {
    const fieldErrors: Record<string, string[]> = {};
    if (typeof payload === 'object' && payload !== null) {
      for (const [k, v] of Object.entries(payload)) {
        if (k === 'detail') continue;
        if (Array.isArray(v)) fieldErrors[k] = v.map(String);
        else if (typeof v === 'string') fieldErrors[k] = [v];
      }
    }
    return {
      kind: 'validation',
      message: detail || 'Datos inválidos',
      fieldErrors,
    };
  }
  if (status >= 500) {
    return { kind: 'server', message: detail || 'Error del servidor', status };
  }
  return { kind: 'unknown', message: detail || `HTTP ${status}`, status };
}

async function request<T>(base: string, path: string, opts: RequestOptions = {}): Promise<T> {
  const url = buildUrl(base, path);
  const headers: Record<string, string> = { Accept: 'application/json' };
  const token = safeReadToken();
  if (token) headers['Authorization'] = `Token ${token}`;
  let body: BodyInit | undefined;
  if (opts.body !== undefined) {
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(opts.body);
  }

  let res: Response;
  try {
    res = await fetch(url, {
      method: opts.method ?? 'GET',
      headers,
      body,
      signal: opts.signal,
    });
  } catch (err) {
    const network: AdminApiError = {
      kind: 'network',
      message: err instanceof Error ? err.message : 'Fallo de red',
    };
    throw new AdminApiException(network);
  }

  if (res.status === 204) return undefined as T;

  let payload: unknown = null;
  const text = await res.text();
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = { detail: text };
    }
  }

  if (!res.ok) {
    const apiError = await parseError(res.status, payload);
    throw new AdminApiException(apiError);
  }
  return payload as T;
}

/**
 * Factory para inyectar base URL en tests (MSW usa el mismo path relativo).
 *
 * P1: solo getProfile / updateProfile. P2–P6 añadirán más métodos.
 */
export function createAdminConfigClient(baseUrl: string = DEFAULT_BASE_URL) {
  return {
    baseUrl,

    /** GET /api/admin/me/profile/  → detalle (crea si no existe). */
    getProfile(opts?: { signal?: AbortSignal }): Promise<AdminProfile> {
      return request<AdminProfile>(baseUrl, '/me/profile/', {
        method: 'GET',
        signal: opts?.signal,
      });
    },

    /** PATCH /api/admin/me/profile/  → edición parcial. */
    updateProfile(patch: AdminProfileUpdate): Promise<AdminProfile> {
      return request<AdminProfile>(baseUrl, '/me/profile/', {
        method: 'PATCH',
        body: patch,
      });
    },
  };
}

export type AdminConfigClient = ReturnType<typeof createAdminConfigClient>;

/** Cliente por defecto; los tests pueden sustituirlo por createAdminConfigClient('/api/admin'). */
export const adminConfigClient: AdminConfigClient = createAdminConfigClient();
