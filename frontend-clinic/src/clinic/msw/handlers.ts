/**
 * MSW handlers — simulan los 6 endpoints del bounded context Muestras clínico (SPEC-008 §2).
 * Reset por test: server.resetHandlers() en tests/setup.ts + resetMockData() para el estado mutable.
 */
import { http, HttpResponse } from 'msw';
import { initialSamples } from './seedData';
import { buildMockKaryotype } from './karyotypeSeed';
import type { SampleCreateRequest, SampleListItem, SampleRead, SampleUpdateRequest } from '../types/sample';
import type { SampleRegistrationData } from '../types/registration';

let samples: SampleRead[] = [...initialSamples];
let forceDegraded = false;

export function resetMockData(): void {
  samples = [...initialSamples];
  forceDegraded = false;
}

export function setDegradedMode(value: boolean): void {
  forceDegraded = value;
}

function toListItem(s: SampleRead): SampleListItem {
  return {
    id: s.id,
    chn_code: s.chn_code,
    patient_ref: s.patient_ref,
    status: s.status,
    analyst_name: s.analyst_name,
    has_karyotype: s.status === 'READY' || s.status === 'VALIDATED',
    created_at: s.created_at,
    updated_at: s.updated_at,
  };
}

const API = '/api/clinic';

/** SSO (ADR-0020): SessionProvider decodifica el payload del JWT para
 * leer role/email — el mock necesita un JWT con 3 segmentos reales
 * (header.payload.signature), no un string plano. La firma no se
 * verifica en el cliente, solo se decodifica, así que un valor
 * cualquiera alcanza para el segmento de firma. */
function fakeJwt(claims: Record<string, unknown>): string {
  const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
  const payload = btoa(JSON.stringify(claims));
  return `${header}.${payload}.mock-signature`;
}

export const handlers = [
  http.post(`${API}/auth/login/`, async ({ request }) => {
    const body = (await request.json()) as { username: string; password: string };
    if (!body.username || !body.password) {
      return HttpResponse.json({ detail: 'Credenciales requeridas' }, { status: 400 });
    }
    const access = fakeJwt({ email: body.username, role: 'analista' });
    return HttpResponse.json({ access, refresh: 'mock-refresh-token' });
  }),

  http.post(`${API}/auth/refresh/`, () => {
    return HttpResponse.json({ access: 'mock-access-token-refreshed' });
  }),

  http.get(`${API}/samples/`, ({ request }) => {
    const url = new URL(request.url);
    let filtered = [...samples];
    const status = url.searchParams.get('status');
    const chnQuery = url.searchParams.get('chn_query');
    if (status) filtered = filtered.filter((s) => s.status === status);
    if (chnQuery) filtered = filtered.filter((s) => s.chn_code.toLowerCase().includes(chnQuery.toLowerCase()));
    return HttpResponse.json(filtered.map(toListItem));
  }),

  http.post(`${API}/samples/register/`, async ({ request }) => {
    const body = (await request.json()) as SampleRegistrationData;
    const chnCode = body.sample.chn_code;

    if (!chnCode) {
      return HttpResponse.json({ code: 'CHN_REQUIRED', detail: 'CHN requerido' }, { status: 400 });
    }
    if (!body.is_draft) {
      if (!/^CHN-\d{4}-\d{2}-\d{2}-\d{4}$/.test(chnCode)) {
        return HttpResponse.json({ code: 'INVALID_CHN_FORMAT', detail: 'Formato de CHN inválido' }, { status: 400 });
      }
      if (!body.patient.full_name) {
        return HttpResponse.json({ code: 'PATIENT_NAME_REQUIRED', detail: 'Nombre del paciente requerido' }, { status: 400 });
      }
      if (body.images.length < 3) {
        return HttpResponse.json({ code: 'INSUFFICIENT_IMAGES', detail: 'Se requieren al menos 3 imágenes' }, { status: 400 });
      }
    }
    if (samples.some((s) => s.chn_code === chnCode)) {
      return HttpResponse.json({ code: 'CHN_DUPLICATE', detail: 'CHN ya existe' }, { status: 409 });
    }

    const newSample: SampleRead = {
      id: crypto.randomUUID(),
      chn_code: chnCode,
      patient_ref: body.patient.full_name,
      image_path: '',
      status: body.is_draft ? 'DRAFT' : 'PROCESSING',
      analyst: 1,
      analyst_name: 'Dra. García',
      supervisor: null,
      supervisor_name: '',
      metadata: body.sample.gender === 'M' || body.sample.gender === 'F' ? { gender: body.sample.gender } : {},
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    samples = [newSample, ...samples];

    return HttpResponse.json(
      {
        id: newSample.id,
        chn_code: newSample.chn_code,
        sample_code: `BM-${Date.now()}`,
        status: body.is_draft ? 'DRAFT' : 'PENDING_AI',
        task_id: body.is_draft || forceDegraded ? null : 'mock-register-task-1',
        image_count: body.images.length,
        degraded: !body.is_draft && forceDegraded,
        created_at: newSample.created_at,
      },
      { status: 201 },
    );
  }),

  http.post(`${API}/samples/`, async ({ request }) => {
    const body = (await request.json()) as SampleCreateRequest;
    if (samples.some((s) => s.chn_code === body.chn_code)) {
      return HttpResponse.json({ code: 'CHN_DUPLICATE', detail: 'CHN ya existe' }, { status: 409 });
    }
    const newSample: SampleRead = {
      id: crypto.randomUUID(),
      chn_code: body.chn_code,
      patient_ref: body.patient_ref,
      image_path: body.image_path ?? '',
      status: 'PENDING_AI',
      analyst: 1,
      analyst_name: 'Dra. García',
      supervisor: null,
      supervisor_name: '',
      metadata: body.metadata ?? {},
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    samples = [newSample, ...samples];
    return HttpResponse.json(newSample, { status: 201 });
  }),

  http.get(`${API}/samples/:id/`, ({ params }) => {
    const sample = samples.find((s) => s.id === params.id);
    if (!sample) return HttpResponse.json({ code: 'NOT_FOUND' }, { status: 404 });
    return HttpResponse.json(sample);
  }),

  http.patch(`${API}/samples/:id/`, async ({ params, request }) => {
    const sample = samples.find((s) => s.id === params.id);
    if (!sample) return HttpResponse.json({ code: 'NOT_FOUND' }, { status: 404 });
    if (sample.status === 'VALIDATED') {
      return HttpResponse.json({ code: 'IMMUTABLE_AFTER_VALIDATED' }, { status: 409 });
    }
    const body = (await request.json()) as SampleUpdateRequest & Record<string, unknown>;
    const forbidden = ['status', 'chn_code', 'iscn_nomenclature', 'edits'].filter((k) => k in body);
    if (forbidden.length > 0) {
      return HttpResponse.json({ code: 'FIELD_NOT_ALLOWED', fields: forbidden }, { status: 400 });
    }
    if (body.patient_ref !== undefined) sample.patient_ref = body.patient_ref;
    if (body.metadata !== undefined) sample.metadata = body.metadata;
    sample.updated_at = new Date().toISOString();
    return HttpResponse.json(sample);
  }),

  http.delete(`${API}/samples/:id/`, ({ params }) => {
    const sample = samples.find((s) => s.id === params.id);
    if (!sample) return HttpResponse.json({ code: 'NOT_FOUND' }, { status: 404 });
    if (sample.status === 'VALIDATED') {
      return HttpResponse.json({ code: 'CANNOT_DELETE_VALIDATED' }, { status: 409 });
    }
    samples = samples.filter((s) => s.id !== params.id);
    return new HttpResponse(null, { status: 204 });
  }),

  http.post(`${API}/samples/:id/process/`, ({ params }) => {
    if (forceDegraded) {
      return HttpResponse.json(
        { code: 'ML_DEGRADED', detail: 'Pipeline no disponible', retry_after_seconds: 60 },
        { status: 503 },
      );
    }
    const sample = samples.find((s) => s.id === params.id);
    if (!sample) return HttpResponse.json({ code: 'NOT_FOUND' }, { status: 404 });
    if (sample.status === 'PROCESSING') {
      return HttpResponse.json({ code: 'ALREADY_PROCESSING' }, { status: 409 });
    }
    sample.status = 'PROCESSING';
    return HttpResponse.json({ sample_id: sample.id, task_id: 'mock-task-123', status: 'queued' }, { status: 202 });
  }),

  http.get(`${API}/samples/:id/status/`, ({ params }) => {
    const sample = samples.find((s) => s.id === params.id);
    if (!sample) return HttpResponse.json({ code: 'NOT_FOUND' }, { status: 404 });
    if (sample.status === 'PROCESSING') {
      sample.status = 'READY';
    }
    return HttpResponse.json({
      sample_id: sample.id,
      status: sample.status,
      progress: sample.status === 'READY' ? 1 : 0.5,
      chromosome_count: sample.status === 'READY' ? 46 : 0,
      confidence_avg: sample.status === 'READY' ? 0.92 : undefined,
    });
  }),

  // Cariotipo (ADR-0021 P1) — solo muestras READY/VALIDATED tienen cariotipo.
  http.get(`${API}/samples/:id/karyotype/`, ({ params }) => {
    const sample = samples.find((s) => s.id === params.id);
    if (!sample) {
      return HttpResponse.json({ code: 'NOT_FOUND', detail: 'Muestra no encontrada' }, { status: 404 });
    }
    if (sample.status !== 'READY' && sample.status !== 'VALIDATED') {
      return HttpResponse.json(
        { code: 'NO_KARYOTYPE', detail: 'La muestra aún no tiene cariotipo generado.' },
        { status: 404 },
      );
    }
    return HttpResponse.json(buildMockKaryotype(String(params.id)));
  }),
];
