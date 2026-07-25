/**
 * MSW handlers — simulan los 6 endpoints del bounded context Muestras clínico (SPEC-008 §2).
 * Reset por test: server.resetHandlers() en tests/setup.ts + resetMockData() para el estado mutable.
 */
import { http, HttpResponse } from 'msw';
import { initialSamples } from './seedData';
import { buildMockKaryotype } from './karyotypeSeed';
import type { SampleCreateRequest, SampleListItem, SampleRead, SampleUpdateRequest } from '../types/sample';
import type { SampleRegistrationData } from '../types/registration';
import type { AuditEvent, AuditEventType, AuditReview, Chromosome, Karyotype } from '../types/karyotype';
import { CHROMOSOME_SLOTS } from '../types/karyotype';

let samples: SampleRead[] = [...initialSamples];
let forceDegraded = false;

// Estado mutable del cariotipo por sample (P2): permite que el flujo
// ver XAI → aceptar → validar persista entre requests en el demo.
const karyotypes: Record<string, Karyotype> = {};
const auditTrails: Record<string, AuditEvent[]> = {};
// Supervisor S1: selección del 5% + decisiones, mutable por sample.
const auditReviews: Record<string, AuditReview[]> = {};

/** Selección determinista del 5% (espejo del backend): pool >0.86, min 1. */
function getOrBuildAuditReviews(sampleId: string): AuditReview[] {
  if (auditReviews[sampleId]) return auditReviews[sampleId];
  const k = getOrBuildKaryotype(sampleId);
  const pool = k.chromosomes
    .filter((c) => c.is_active && c.confidence_score !== null && parseFloat(c.confidence_score) > 0.86)
    .sort((a, b) => a.id.localeCompare(b.id));
  const n = pool.length ? Math.max(1, Math.ceil(0.05 * pool.length)) : 0;
  auditReviews[sampleId] = pool.slice(0, n).map((c, i) => ({
    id: `${sampleId}-rev-${i}`,
    chromosome: c.id,
    predicted_class: c.predicted_class,
    confidence_score: c.confidence_score,
    semaphore: c.semaphore,
    decision: 'PENDING',
    comment: '',
    reviewer: null,
    reviewer_name: '',
    decided_at: null,
    created_at: new Date().toISOString(),
  }));
  return auditReviews[sampleId];
}

function auditReviewSummary(sampleId: string) {
  const rs = auditReviews[sampleId] ?? [];
  return {
    total: rs.length,
    pending: rs.filter((r) => r.decision === 'PENDING').length,
    confirmed: rs.filter((r) => r.decision === 'CONFIRMED').length,
    rejected: rs.filter((r) => r.decision === 'REJECTED').length,
  };
}

// Supervisor S2: contador de fallos de MFA por sample (mock del lockout).
const signFails: Record<string, number> = {};
const MOCK_MFA_CODE = '123456';

function getOrBuildKaryotype(sampleId: string): Karyotype {
  if (!karyotypes[sampleId]) karyotypes[sampleId] = buildMockKaryotype(sampleId);
  return karyotypes[sampleId];
}

function recomputeSummary(k: Karyotype): void {
  // P3: los fragmentos absorbidos por JOIN (is_active=false) no cuentan.
  const activos = k.chromosomes.filter((c) => c.is_active);
  const orange = activos.filter((c) => c.semaphore === 'orange');
  const red = activos.filter((c) => c.semaphore === 'red');
  const unresolved = orange.filter((c) => c.resolution_status !== 'RESOLVED');
  k.summary = {
    total: activos.length,
    green: activos.filter((c) => c.semaphore === 'green').length,
    orange: orange.length,
    red: red.length,
    unresolved_orange: unresolved.length,
    is_blocked: unresolved.length > 0 || red.length > 0,
  };
}

/** Case-lock (DD-KARYO-003 §2.2): tras validar, el analista no puede editar. */
function sampleLocked(sampleId: string): boolean {
  const s = samples.find((x) => x.id === sampleId);
  return s?.status === 'ANALYST_VALIDATED' || s?.status === 'VALIDATED';
}

/** P4: el modo degradado viaja en el header X-Biomed-Mode (DD-KARYO-004). */
function modeOf(request: Request): 'auto' | 'degradado' {
  return request.headers.get('X-Biomed-Mode') === 'degradado' ? 'degradado' : 'auto';
}

function pushAudit(sampleId: string, eventType: AuditEventType, chromosomeId: string | null, mode: 'auto' | 'degradado' = 'auto'): void {
  const chain = auditTrails[sampleId] ?? (auditTrails[sampleId] = []);
  const prev = chain.length ? chain[chain.length - 1].current_hash : '';
  chain.push({
    id: `${sampleId}-ev-${chain.length}`,
    event_type: eventType,
    chromosome: chromosomeId,
    mode,
    actor: 1,
    actor_name: 'Analista Demo',
    payload: {},
    created_at: new Date().toISOString(),
    previous_hash: prev,
    current_hash: `mockhash-${chain.length}-${eventType}`,
  });
}

export function resetMockData(): void {
  // Copia PROFUNDA: varios handlers mutan `sample.status` (process, validate);
  // sin clonar los objetos, la mutación persistiría en initialSamples y
  // filtraría estado entre tests (aislamiento roto).
  samples = initialSamples.map((s) => ({ ...s }));
  forceDegraded = false;
  try {
    sessionStorage?.removeItem('biomed.degraded');
    for (let i = sessionStorage.length - 1; i >= 0; i--) {
      const key = sessionStorage.key(i);
      if (key?.startsWith('biomed.status.')) sessionStorage.removeItem(key);
    }
  } catch { /* no-op */ }
  for (const k of Object.keys(karyotypes)) delete karyotypes[k];
  for (const k of Object.keys(auditTrails)) delete auditTrails[k];
  for (const k of Object.keys(auditReviews)) delete auditReviews[k];
  for (const k of Object.keys(signFails)) delete signFails[k];
}

/** Demo/E2E: fuerza el estado clínico de una muestra (p.ej. ANALYST_VALIDATED
 * para el flujo del Supervisor S1). Persiste en sessionStorage para sobrevivir
 * un reload; `applyStatusOverrides` lo re-aplica en el bootstrap. */
export function setSampleStatus(sampleId: string, status: SampleRead['status']): void {
  const s = samples.find((x) => x.id === sampleId);
  if (s) s.status = status;
  try { sessionStorage?.setItem(`biomed.status.${sampleId}`, status); } catch { /* no-op */ }
}

/** Re-aplica los overrides de estado persistidos (llamado en el bootstrap MSW). */
export function applyStatusOverrides(): void {
  try {
    for (let i = 0; i < sessionStorage.length; i++) {
      const key = sessionStorage.key(i);
      if (key?.startsWith('biomed.status.')) {
        const id = key.slice('biomed.status.'.length);
        const s = samples.find((x) => x.id === id);
        if (s) s.status = sessionStorage.getItem(key) as SampleRead['status'];
      }
    }
  } catch { /* sessionStorage no disponible */ }
}

/** Persistente para que el modo degradado sobreviva un reload (demo/E2E). */
function degradedFlag(): boolean {
  try {
    return typeof sessionStorage !== 'undefined' && sessionStorage.getItem('biomed.degraded') === '1';
  } catch {
    return false;
  }
}

export function setDegradedMode(value: boolean): void {
  forceDegraded = value;
  try {
    if (typeof sessionStorage !== 'undefined') {
      if (value) sessionStorage.setItem('biomed.degraded', '1');
      else sessionStorage.removeItem('biomed.degraded');
    }
  } catch { /* sessionStorage no disponible */ }
}

/** El pipeline está degradado si se forzó en runtime o vía el flag persistente. */
function isDegraded(): boolean {
  return forceDegraded || degradedFlag();
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
    const withKaryotype = ['READY', 'VALIDATED', 'ANALYST_VALIDATED', 'SIGNED', 'REPORTED'];
    if (!withKaryotype.includes(sample.status)) {
      return HttpResponse.json(
        { code: 'NO_KARYOTYPE', detail: 'La muestra aún no tiene cariotipo generado.' },
        { status: 404 },
      );
    }
    const k = getOrBuildKaryotype(String(params.id));
    k.sample_status = sample.status; // gating del panel del supervisor (S1)
    return HttpResponse.json(k);
  }),

  // Cariotipo P2 (ADR-0021 P2, ADR-0022) — XAI, resolver, anomalía, validar, audit.
  http.post(`${API}/samples/:id/chromosomes/:cid/xai/`, ({ params, request }) => {
    const k = getOrBuildKaryotype(String(params.id));
    const chromo = k.chromosomes.find((c) => c.id === params.cid);
    if (!chromo) return HttpResponse.json({ code: 'CHROMOSOME_NOT_FOUND' }, { status: 404 });
    chromo.xai_viewed = true;
    pushAudit(String(params.id), 'XAI_VIEWED', chromo.id, modeOf(request));
    return HttpResponse.json({
      chromosome_id: chromo.id,
      predicted_class: chromo.predicted_class,
      confidence_score: chromo.confidence_score,
      heatmap_base64: 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==',
    });
  }),

  http.post(`${API}/samples/:id/chromosomes/:cid/resolve/`, ({ params, request }) => {
    const k = getOrBuildKaryotype(String(params.id));
    const chromo = k.chromosomes.find((c) => c.id === params.cid);
    if (!chromo) return HttpResponse.json({ code: 'CHROMOSOME_NOT_FOUND' }, { status: 404 });
    if (chromo.semaphore !== 'orange') {
      return HttpResponse.json({ code: 'NOT_ORANGE', detail: 'Solo los naranja requieren resolución.' }, { status: 400 });
    }
    if (!chromo.xai_viewed) {
      return HttpResponse.json({ code: 'XAI_REQUIRED', detail: 'Debe consultar XAI antes de resolver.' }, { status: 409 });
    }
    chromo.resolution_status = 'RESOLVED';
    recomputeSummary(k);
    pushAudit(String(params.id), 'ACCEPT_CHROMOSOME', chromo.id, modeOf(request));
    return HttpResponse.json(chromo);
  }),

  http.post(`${API}/samples/:id/chromosomes/:cid/anomaly/`, ({ params, request }) => {
    const k = getOrBuildKaryotype(String(params.id));
    const chromo = k.chromosomes.find((c) => c.id === params.cid);
    if (!chromo) return HttpResponse.json({ code: 'CHROMOSOME_NOT_FOUND' }, { status: 404 });
    chromo.is_anomaly = true;
    pushAudit(String(params.id), 'MARK_ANOMALY', chromo.id, modeOf(request));
    return HttpResponse.json(chromo);
  }),

  http.post(`${API}/samples/:id/validate/`, ({ params, request }) => {
    const k = getOrBuildKaryotype(String(params.id));
    recomputeSummary(k);
    if (k.summary.unresolved_orange > 0 || k.summary.red > 0) {
      return HttpResponse.json(
        { code: 'CASE_BLOCKED', detail: 'Resuelva todos los cromosomas naranja antes de continuar.' },
        { status: 409 },
      );
    }
    const sample = samples.find((s) => s.id === params.id);
    if (sample) sample.status = 'ANALYST_VALIDATED';
    pushAudit(String(params.id), 'ANALYST_VALIDATED', null, modeOf(request));
    return HttpResponse.json({ sample_id: String(params.id), status: 'ANALYST_VALIDATED' });
  }),

  http.get(`${API}/samples/:id/audit/`, ({ params }) => {
    return HttpResponse.json(auditTrails[String(params.id)] ?? []);
  }),

  // Cariotipo P3 (ADR-0021 P3, DD-KARYO-003) — corrección manual.
  http.post(`${API}/samples/:id/chromosomes/:cid/reclassify/`, async ({ params, request }) => {
    const sid = String(params.id);
    if (sampleLocked(sid)) return HttpResponse.json({ code: 'CASE_LOCKED', detail: 'Caso validado' }, { status: 409 });
    const k = getOrBuildKaryotype(sid);
    const chromo = k.chromosomes.find((c) => c.id === params.cid);
    if (!chromo) return HttpResponse.json({ code: 'CHROMOSOME_NOT_FOUND' }, { status: 404 });
    const body = (await request.json()) as { target_class?: string };
    const target = body.target_class ?? '';
    if (!CHROMOSOME_SLOTS.includes(target)) {
      return HttpResponse.json({ code: 'INVALID_CLASS', detail: 'Clase inválida' }, { status: 400 });
    }
    if (target === chromo.predicted_class) {
      return HttpResponse.json({ code: 'SAME_CLASS', detail: 'Clase igual a la actual' }, { status: 400 });
    }
    chromo.predicted_class = target;
    chromo.resolution_status = 'RESOLVED';
    recomputeSummary(k);
    pushAudit(sid, 'CORRECT_CLASS', chromo.id, modeOf(request));
    return HttpResponse.json(chromo);
  }),

  http.post(`${API}/samples/:id/chromosomes/:cid/split/`, ({ params, request }) => {
    const sid = String(params.id);
    if (sampleLocked(sid)) return HttpResponse.json({ code: 'CASE_LOCKED', detail: 'Caso validado' }, { status: 409 });
    const k = getOrBuildKaryotype(sid);
    const chromo = k.chromosomes.find((c) => c.id === params.cid);
    if (!chromo) return HttpResponse.json({ code: 'CHROMOSOME_NOT_FOUND' }, { status: 404 });
    const w = chromo.bbox.w ?? 0;
    const x = chromo.bbox.x ?? 0;
    chromo.bbox = { ...chromo.bbox, x, w: w / 2 };
    const nextIndex = Math.max(...k.chromosomes.filter((c) => c.predicted_class === chromo.predicted_class).map((c) => c.position_index)) + 1;
    const created: Chromosome = {
      ...chromo,
      id: `${chromo.id}-split-${nextIndex}`,
      position_index: nextIndex,
      bbox: { ...chromo.bbox, x: x + w / 2, w: w / 2 },
      order: k.chromosomes.length,
    };
    k.chromosomes.push(created);
    recomputeSummary(k);
    pushAudit(sid, 'SPLIT', chromo.id, modeOf(request));
    return HttpResponse.json(created, { status: 201 });
  }),

  http.post(`${API}/samples/:id/chromosomes/:cid/join/`, async ({ params, request }) => {
    const sid = String(params.id);
    if (sampleLocked(sid)) return HttpResponse.json({ code: 'CASE_LOCKED', detail: 'Caso validado' }, { status: 409 });
    const k = getOrBuildKaryotype(sid);
    const keep = k.chromosomes.find((c) => c.id === params.cid);
    if (!keep) return HttpResponse.json({ code: 'CHROMOSOME_NOT_FOUND' }, { status: 404 });
    const body = (await request.json()) as { other_id?: string };
    if (body.other_id === keep.id) return HttpResponse.json({ code: 'JOIN_SELF', detail: 'Mismo cromosoma' }, { status: 400 });
    const absorbed = k.chromosomes.find((c) => c.id === body.other_id);
    if (!absorbed) return HttpResponse.json({ code: 'CHROMOSOME_NOT_FOUND' }, { status: 404 });
    absorbed.is_active = false;
    const x0 = Math.min(keep.bbox.x ?? 0, absorbed.bbox.x ?? 0);
    const x1 = Math.max((keep.bbox.x ?? 0) + (keep.bbox.w ?? 0), (absorbed.bbox.x ?? 0) + (absorbed.bbox.w ?? 0));
    keep.bbox = { ...keep.bbox, x: x0, w: x1 - x0 };
    recomputeSummary(k);
    pushAudit(sid, 'JOIN', keep.id, modeOf(request));
    return HttpResponse.json(keep);
  }),

  http.post(`${API}/samples/:id/chromosomes/:cid/cross/`, ({ params, request }) => {
    const sid = String(params.id);
    if (sampleLocked(sid)) return HttpResponse.json({ code: 'CASE_LOCKED', detail: 'Caso validado' }, { status: 409 });
    const k = getOrBuildKaryotype(sid);
    const chromo = k.chromosomes.find((c) => c.id === params.cid);
    if (!chromo) return HttpResponse.json({ code: 'CHROMOSOME_NOT_FOUND' }, { status: 404 });
    chromo.resolution_status = 'RESOLVED';
    recomputeSummary(k);
    pushAudit(sid, 'RESOLVE_CROSS', chromo.id, modeOf(request));
    return HttpResponse.json(chromo);
  }),

  // Cariotipo P4 (ADR-0021 P4, DD-KARYO-004) — salud del pipeline (modo degradado).
  http.get(`${API}/pipeline/health/`, () => {
    const degraded = isDegraded();
    return HttpResponse.json({ available: !degraded, mode: degraded ? 'degradado' : 'auto' });
  }),

  // Supervisor S1 (ADR-0023, DD-SUP-001) — auditoría del 5%.
  http.get(`${API}/samples/:id/audit-review/`, ({ params }) => {
    const sid = String(params.id);
    const reviews = getOrBuildAuditReviews(sid);
    return HttpResponse.json({ reviews, summary: auditReviewSummary(sid) });
  }),

  http.post(`${API}/samples/:id/audit-review/:cid/decide/`, async ({ params, request }) => {
    const sid = String(params.id);
    const sample = samples.find((s) => s.id === sid);
    if (sample && sample.status !== 'ANALYST_VALIDATED') {
      return HttpResponse.json({ code: 'NOT_AUDITABLE', detail: 'El caso debe estar validado por el analista.' }, { status: 409 });
    }
    const reviews = getOrBuildAuditReviews(sid);
    const review = reviews.find((r) => r.chromosome === params.cid);
    if (!review) return HttpResponse.json({ code: 'REVIEW_NOT_FOUND' }, { status: 404 });
    const body = (await request.json()) as { decision?: string; comment?: string };
    if (body.decision !== 'CONFIRMED' && body.decision !== 'REJECTED') {
      return HttpResponse.json({ code: 'INVALID_DECISION', detail: 'Decisión inválida' }, { status: 400 });
    }
    review.decision = body.decision;
    review.comment = body.comment ?? '';
    review.reviewer = 1;
    review.reviewer_name = 'Supervisor Demo';
    review.decided_at = new Date().toISOString();
    pushAudit(sid, 'AUDIT_DECISION', review.chromosome, modeOf(request));
    return HttpResponse.json(review);
  }),

  // Supervisor S2 (ADR-0023 S2, DD-SUP-002) — firma MFA (TOTP mock: 123456).
  http.post(`${API}/samples/:id/sign/`, async ({ params, request }) => {
    const sid = String(params.id);
    const sample = samples.find((s) => s.id === sid);
    if (!sample) return HttpResponse.json({ code: 'NOT_FOUND' }, { status: 404 });
    if (sample.status !== 'ANALYST_VALIDATED') {
      return HttpResponse.json({ code: 'NOT_SIGNABLE', detail: 'El caso no está en estado firmable.' }, { status: 409 });
    }
    if (auditReviewSummary(sid).pending > 0) {
      return HttpResponse.json({ code: 'AUDIT_INCOMPLETE', detail: 'Debe revisar toda la auditoría del 5% antes de firmar.' }, { status: 409 });
    }
    if ((signFails[sid] ?? 0) >= 3) {
      return HttpResponse.json({ code: 'MFA_LOCKED', detail: 'Firma bloqueada por intentos fallidos de MFA.' }, { status: 423 });
    }
    const body = (await request.json()) as { mfa_code?: string };
    if (body.mfa_code !== MOCK_MFA_CODE) {
      signFails[sid] = (signFails[sid] ?? 0) + 1;
      if (signFails[sid] >= 3) {
        return HttpResponse.json({ code: 'MFA_LOCKED', detail: 'Firma bloqueada por intentos fallidos de MFA.' }, { status: 423 });
      }
      return HttpResponse.json({ code: 'MFA_INVALID', detail: 'Código MFA inválido.' }, { status: 401 });
    }
    signFails[sid] = 0;
    sample.status = 'SIGNED';
    pushAudit(sid, 'SIGN_REPORT', null, modeOf(request));
    return HttpResponse.json({ sample_id: sid, status: 'SIGNED', signed_at: new Date().toISOString() });
  }),
];
