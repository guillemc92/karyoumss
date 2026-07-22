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
  ChangePasswordInput,
  ModelConfig,
  ModelConfigUpdate,
  ModelMetric,
  NotificationPreference,
  NotificationPreferenceUpdate,
  TwoFactorSetup,
  TwoFactorToggleResult,
} from '../types/config';

const DEFAULT_BASE_URL =
  (import.meta.env.VITE_ADMIN_API_BASE as string | undefined) ?? '/api/admin';

const TOKEN_STORAGE_KEY = 'biomed.admin.token';
/** JWT de sesión del login unificado (ADR-0017) — ver adminClient.ts
 * para el mismo patrón y su justificación completa. */
const SESSION_ACCESS_KEY = 'biomed.auth.access';

function safeReadToken(): string | null {
  if (typeof window === 'undefined') return null;
  try {
    return window.localStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

function safeReadSessionAccess(): string | null {
  if (typeof window === 'undefined') return null;
  try {
    return window.localStorage.getItem(SESSION_ACCESS_KEY);
  } catch {
    return null;
  }
}

/** Prioridad: JWT de sesión (Bearer) primero, token de exchange F0 (Token) como fallback. */
function buildAuthHeader(): string | null {
  const sessionAccess = safeReadSessionAccess();
  if (sessionAccess) return `Bearer ${sessionAccess}`;
  const exchangeToken = safeReadToken();
  if (exchangeToken) return `Token ${exchangeToken}`;
  return null;
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
  const authHeader = buildAuthHeader();
  if (authHeader) headers['Authorization'] = authHeader;
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

    /** POST /api/admin/me/password/  → rota la contraseña (P2). */
    changePassword(input: ChangePasswordInput): Promise<void> {
      return request<void>(baseUrl, '/me/password/', {
        method: 'POST',
        body: input,
      });
    },

    /** POST /api/admin/me/2fa/setup/  → genera secret TOTP + QR (P2). */
    setup2FA(): Promise<TwoFactorSetup> {
      return request<TwoFactorSetup>(baseUrl, '/me/2fa/setup/', {
        method: 'POST',
      });
    },

    /** POST /api/admin/me/2fa/toggle/  → activa/desactiva 2FA (P2). */
    toggle2FA(enabled: boolean, code: string): Promise<TwoFactorToggleResult> {
      return request<TwoFactorToggleResult>(baseUrl, '/me/2fa/toggle/', {
        method: 'POST',
        body: { enabled, code },
      });
    },

    /** GET /api/admin/models/active/  → configuración activa (P3, crea singleton si no existe). */
    getActiveModel(opts?: { signal?: AbortSignal }): Promise<ModelConfig> {
      return request<ModelConfig>(baseUrl, '/models/active/', {
        method: 'GET',
        signal: opts?.signal,
      });
    },

    /** PATCH /api/admin/models/active/  → edición parcial (P3). */
    updateActiveModel(patch: ModelConfigUpdate): Promise<ModelConfig> {
      return request<ModelConfig>(baseUrl, '/models/active/', {
        method: 'PATCH',
        body: patch,
      });
    },

    /** GET /api/admin/models/metrics/?days=N  → histórico filtrado (P3). */
    getMetrics(days = 30, opts?: { signal?: AbortSignal }): Promise<ModelMetric[]> {
      return request<ModelMetric[]>(baseUrl, `/models/metrics/?days=${days}`, {
        method: 'GET',
        signal: opts?.signal,
      });
    },

    /** GET /api/admin/models/metrics/latest/  → último snapshot, undefined si no hay ninguno (204). */
    getLatestMetric(opts?: { signal?: AbortSignal }): Promise<ModelMetric | undefined> {
      return request<ModelMetric | undefined>(baseUrl, '/models/metrics/latest/', {
        method: 'GET',
        signal: opts?.signal,
      });
    },

    /** GET /api/admin/me/notifications/  → detalle (crea si no existe). */
    getNotifications(opts?: { signal?: AbortSignal }): Promise<NotificationPreference> {
      return request<NotificationPreference>(baseUrl, '/me/notifications/', {
        method: 'GET',
        signal: opts?.signal,
      });
    },

    /** PATCH /api/admin/me/notifications/  → edición parcial (P4). */
    updateNotifications(patch: NotificationPreferenceUpdate): Promise<NotificationPreference> {
      return request<NotificationPreference>(baseUrl, '/me/notifications/', {
        method: 'PATCH',
        body: patch,
      });
    },
  };
}

export type AdminConfigClient = ReturnType<typeof createAdminConfigClient>;

/** Cliente por defecto; los tests pueden sustituirlo por createAdminConfigClient('/api/admin'). */
export const adminConfigClient: AdminConfigClient = createAdminConfigClient();
