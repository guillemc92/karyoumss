/**
 * adminClient — wrapper HTTP para el bounded context admin.
 *
 * Endpoints (ADR-0013 + AUTH_BRIDGE.md):
 *   GET    /api/admin/users/                  listar activos
 *   POST   /api/admin/users/                  crear
 *   GET    /api/admin/users/{id}/             detalle
 *   PATCH  /api/admin/users/{id}/             actualizar (parcial)
 *   DELETE /api/admin/users/{id}/             soft-delete (idempotente)
 *   GET    /api/admin/users/{id}/history      log de auditoría
 *   POST   /api/admin/auth/exchange           canjear FastAPI JWT por Token Django
 *
 * Respuestas de error esperadas del backend (apps/users/views.py):
 *   400 → validación (DRF default + ValidationError custom)
 *   401 → Token ausente / inválido / expirado
 *   403 → rol distinto de 'admin' (IsAdminRole en mutaciones)
 *   404 → AdminUser no existe o ya está soft-deleted
 *   409 → email duplicado (unique index admin_users_email_lower_unique_idx)
 *   5xx → inesperado
 */
import {
  AdminApiError,
  AdminApiException,
  AdminUser,
  AdminUserDraft,
  AdminUserUpdate,
  AuditLogEntry,
} from '../types/adminUser';

const DEFAULT_BASE_URL =
  (import.meta.env.VITE_ADMIN_API_BASE as string | undefined) ?? '/api/admin';

const TOKEN_STORAGE_KEY = 'biomed.admin.token';

function safeReadToken(): string | null {
  if (typeof window === 'undefined') return null;
  const storage = window.localStorage;
  try {
    return storage.getItem(TOKEN_STORAGE_KEY);
  } catch (_err) {
    return null;
  }
}

function safeWriteToken(token: string | null): void {
  if (typeof window === 'undefined') return;
  const storage = window.localStorage;
  try {
    if (token === null) {
      storage.removeItem(TOKEN_STORAGE_KEY);
    } else {
      storage.setItem(TOKEN_STORAGE_KEY, token);
    }
  } catch (_err) {
    // storage no disponible (modo privado, etc.) — ignorar deliberadamente
  }
}

/** Lee el token DRF del localStorage. Reemplazable por cookie httpOnly cuando exista F7. */
export function getAuthToken(): string | null {
  return safeReadToken();
}

export function setAuthToken(token: string | null): void {
  safeWriteToken(token);
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE';
  body?: unknown;
  query?: Record<string, string | number | undefined>;
  signal?: AbortSignal;
}

function buildUrl(
  base: string,
  path: string,
  query?: Record<string, string | number | undefined>,
): string {
  const cleanBase = base.endsWith('/') ? base.slice(0, -1) : base;
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  const url = `${cleanBase}${cleanPath}`;
  if (query === undefined) return url;
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(query)) {
    const defined = v !== undefined && v !== null && v !== '';
    if (defined) qs.set(k, String(v));
  }
  const s = qs.toString();
  return s.length > 0 ? `${url}?${s}` : url;
}

async function parseError(
  status: number,
  payload: unknown,
): Promise<AdminApiError> {
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
  const url = buildUrl(base, path, opts.query);
  const headers: Record<string, string> = {
    Accept: 'application/json',
  };
  const token = getAuthToken();
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

  // 204 No Content (no debería ocurrir, pero defenderse)
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

/** Factory para inyectar base URL en tests (MSW usa el mismo path relativo). */
export function createAdminClient(baseUrl: string = DEFAULT_BASE_URL) {
  return {
    baseUrl,
    list(): Promise<AdminUser[]> {
      return request<AdminUser[]>(baseUrl, '/users/', { method: 'GET' });
    },
    get(id: string): Promise<AdminUser> {
      return request<AdminUser>(baseUrl, `/users/${id}/`, { method: 'GET' });
    },
    create(draft: AdminUserDraft): Promise<AdminUser> {
      return request<AdminUser>(baseUrl, '/users/', { method: 'POST', body: draft });
    },
    update(id: string, patch: AdminUserUpdate): Promise<AdminUser> {
      return request<AdminUser>(baseUrl, `/users/${id}/`, { method: 'PATCH', body: patch });
    },
    softDelete(id: string): Promise<void> {
      return request<void>(baseUrl, `/users/${id}/`, { method: 'DELETE' });
    },
    history(id: string, query?: Record<string, string | number | undefined>): Promise<AuditLogEntry[]> {
      return request<AuditLogEntry[]>(baseUrl, `/users/${id}/history`, { method: 'GET', query });
    },
    /** F0 / F7: canjea un JWT de FastAPI por un Token Django. */
    async exchangeFastApiJwt(fastapiJwt: string): Promise<string> {
      const res = await request<{ token: string }>(baseUrl, '/auth/exchange', {
        method: 'POST',
        body: { fastapi_jwt: fastapiJwt },
      });
      setAuthToken(res.token);
      return res.token;
    },
    logout(): void {
      setAuthToken(null);
    },
  };
}

export type AdminClient = ReturnType<typeof createAdminClient>;

/** Cliente por defecto; los tests pueden sustituirlo por createAdminClient('/api/admin'). */
export const adminClient: AdminClient = createAdminClient();