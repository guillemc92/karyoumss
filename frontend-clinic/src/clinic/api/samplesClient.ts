/**
 * samplesClient — wrapper HTTP para el bounded context Muestras clínico (ADR-0015).
 *
 * Endpoints (SPEC-008 §2):
 *   GET    /api/clinic/samples/                listar con filtros + paginación
 *   POST   /api/clinic/samples/                crear
 *   GET    /api/clinic/samples/{id}/           detalle
 *   PATCH  /api/clinic/samples/{id}/           editar patient_ref (RN-04)
 *   DELETE /api/clinic/samples/{id}/           soft-delete (admin only)
 *   POST   /api/clinic/samples/{id}/process/   encolar pipeline
 *   GET    /api/clinic/samples/{id}/status/    polling
 *
 * Errores esperados:
 *   400 → validación / campo RN-04 no permitido
 *   401 → JWT ausente / inválido / expirado
 *   403 → NOT_OWNER / ADMIN_ONLY
 *   404 → muestra no existe / soft-deleted
 *   409 → CHN_DUPLICATE / ALREADY_PROCESSING / IMMUTABLE_AFTER_VALIDATED
 *   503 → ML_DEGRADED (RN-07)
 */
import { getAccessToken } from './authClient';
import {
  ClinicApiException,
  type ProcessResponse,
  type SampleCreateRequest,
  type SampleFilters,
  type SampleListItem,
  type SampleRead,
  type SampleUpdateRequest,
  type StatusResponse,
} from '../types/sample';

const DEFAULT_BASE_URL = (import.meta.env.VITE_CLINIC_API_BASE as string | undefined) ?? '/api/clinic';

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE';
  body?: unknown;
  query?: Record<string, string | number | undefined>;
}

function buildUrl(base: string, path: string, query?: Record<string, string | number | undefined>): string {
  const cleanBase = base.endsWith('/') ? base.slice(0, -1) : base;
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  const url = `${cleanBase}${cleanPath}`;
  if (query === undefined) return url;
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(query)) {
    if (v !== undefined && v !== null && v !== '') qs.set(k, String(v));
  }
  const s = qs.toString();
  return s.length > 0 ? `${url}?${s}` : url;
}

async function request<T>(base: string, path: string, opts: RequestOptions = {}): Promise<T> {
  const url = buildUrl(base, path, opts.query);
  const headers: Record<string, string> = { Accept: 'application/json' };
  const token = getAccessToken();
  if (token) headers['Authorization'] = `Bearer ${token}`;

  let body: BodyInit | undefined;
  if (opts.body !== undefined) {
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(opts.body);
  }

  let res: Response;
  try {
    res = await fetch(url, { method: opts.method ?? 'GET', headers, body });
  } catch (err) {
    throw new ClinicApiException(err instanceof Error ? err.message : 'Fallo de red', 0, 'NETWORK_ERROR');
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
    const detail =
      typeof payload === 'object' && payload !== null && 'detail' in payload
        ? String((payload as { detail: unknown }).detail)
        : `HTTP ${res.status}`;
    const code =
      typeof payload === 'object' && payload !== null && 'code' in payload
        ? String((payload as { code: unknown }).code)
        : undefined;
    throw new ClinicApiException(detail, res.status, code);
  }
  return payload as T;
}

export function createSamplesClient(baseUrl: string = DEFAULT_BASE_URL) {
  return {
    baseUrl,
    list(filters?: SampleFilters): Promise<SampleListItem[]> {
      return request<SampleListItem[]>(baseUrl, '/samples/', { method: 'GET', query: filters as Record<string, string | number | undefined> });
    },
    get(id: string): Promise<SampleRead> {
      return request<SampleRead>(baseUrl, `/samples/${id}/`, { method: 'GET' });
    },
    create(draft: SampleCreateRequest): Promise<SampleRead> {
      return request<SampleRead>(baseUrl, '/samples/', { method: 'POST', body: draft });
    },
    update(id: string, patch: SampleUpdateRequest): Promise<SampleRead> {
      return request<SampleRead>(baseUrl, `/samples/${id}/`, { method: 'PATCH', body: patch });
    },
    softDelete(id: string): Promise<void> {
      return request<void>(baseUrl, `/samples/${id}/`, { method: 'DELETE' });
    },
    process(id: string, forceReprocess = false): Promise<ProcessResponse> {
      return request<ProcessResponse>(baseUrl, `/samples/${id}/process/`, {
        method: 'POST',
        body: { force_reprocess: forceReprocess },
      });
    },
    getStatus(id: string): Promise<StatusResponse> {
      return request<StatusResponse>(baseUrl, `/samples/${id}/status/`, { method: 'GET' });
    },
  };
}

export type SamplesClient = ReturnType<typeof createSamplesClient>;
export const samplesClient: SamplesClient = createSamplesClient();
