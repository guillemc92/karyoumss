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
import { textoDeDetalle } from './detalleError';
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

/**
 * Modo del sistema (FSD-UC-007, DD-KARYO-004): 'degradado' cuando el pipeline de
 * IA está caído. Es un estado cross-cutting — se propaga como header
 * `X-Biomed-Mode` en TODA petición clínica para que el backend marque las
 * acciones manuales en el audit trail, sin ensuciar el body de cada endpoint.
 * `useDegradedMode` lo actualiza; los tests pueden setearlo directamente.
 */
let clinicMode: 'auto' | 'degradado' = 'auto';
export function setClinicMode(mode: 'auto' | 'degradado'): void {
  clinicMode = mode;
}
export function getClinicMode(): 'auto' | 'degradado' {
  return clinicMode;
}

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

/** Cabeceras de TODA petición clínica: modo del sistema y token. Compartidas
 * por `request` y `requestBlob` para que la autenticación no pueda divergir
 * entre las dos. */
function cabeceras(accept: string): Record<string, string> {
  const headers: Record<string, string> = { Accept: accept, 'X-Biomed-Mode': clinicMode };
  const token = getAccessToken();
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return headers;
}

async function enviar(url: string, init: RequestInit): Promise<Response> {
  try {
    return await fetch(url, init);
  } catch (err) {
    throw new ClinicApiException(err instanceof Error ? err.message : 'Fallo de red', 0, 'NETWORK_ERROR');
  }
}

function parsear(text: string): unknown {
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return { detail: text };
  }
}

/** Convierte una respuesta de error del backend en `ClinicApiException` con su
 * `code` (NOT_OWNER, NO_METAPHASE_IMAGE…), que es lo que deciden las pantallas. */
function errorDe(res: Response, payload: unknown): ClinicApiException {
  const detail =
    typeof payload === 'object' && payload !== null && 'detail' in payload
      ? textoDeDetalle((payload as { detail: unknown }).detail, `HTTP ${res.status}`)
      : `HTTP ${res.status}`;
  const code =
    typeof payload === 'object' && payload !== null && 'code' in payload
      ? String((payload as { code: unknown }).code)
      : undefined;
  return new ClinicApiException(detail, res.status, code);
}

async function request<T>(base: string, path: string, opts: RequestOptions = {}): Promise<T> {
  const url = buildUrl(base, path, opts.query);
  const headers = cabeceras('application/json');

  let body: BodyInit | undefined;
  if (opts.body !== undefined) {
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(opts.body);
  }

  const res = await enviar(url, { method: opts.method ?? 'GET', headers, body });
  if (res.status === 204) return undefined as T;

  const payload = parsear(await res.text());
  if (!res.ok) throw errorDe(res, payload);
  return payload as T;
}

/**
 * GET de un recurso binario (DD-KARYO-006: la metafase). Existe porque un
 * `<img src>` no puede enviar el token: la imagen se pide con las mismas
 * cabeceras que el resto y se entrega como `Blob`. Los errores llegan en JSON,
 * así que se convierten igual que en `request`.
 */
async function requestBlob(base: string, path: string): Promise<Blob> {
  const res = await enviar(buildUrl(base, path), { method: 'GET', headers: cabeceras('image/*') });
  if (!res.ok) throw errorDe(res, parsear(await res.text()));
  return res.blob();
}

/** Reutilizable por otros clients del bounded context clínico (ej.
 * karyotypeClient) — misma infra de auth JWT + parseo de errores. */
export {
  request as clinicRequest,
  requestBlob as clinicRequestBlob,
  DEFAULT_BASE_URL as CLINIC_DEFAULT_BASE_URL,
};

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
