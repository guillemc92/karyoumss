// Prueba de carga con trazas (DD-OBS-001 D6). Sigue la forma de bench/e3/carga.js.
//
// Dos tipos de petición a la vez, contra `web` (la misma entrada que usa una persona):
//   GET  /api/clinic/samples/{id}/karyotype/   lectura, a ritmo fijo         (tipo=lectura)
//   POST /api/clinic/samples/{id}/process/     la lenta: clinic → ml → clinic (tipo=procesar)
//
// `procesar` llega de dos en dos: en cada ciclo, PAREJA usuarios piden procesar a
// la vez. backend-ml atiende una inferencia por vez (ML_MAX_INFERENCIAS=1), así
// que una entra y la otra espera su turno. Es lo que la hipótesis H2 quiere ver.
//
// Cómo se corre (desde la raíz del repo, con el stack arriba y el perfil obs):
//   docker compose --profile carga run --rm carga-semilla
//   docker compose --profile carga run --rm k6 run /k6/carga.js
import http from 'k6/http';
import { sleep } from 'k6';
import { SharedArray } from 'k6/data';

const API = __ENV.API || 'http://web:8080';
const RPS = Number(__ENV.RPS || 5); // lecturas por segundo
const DURACION = Number(__ENV.DURACION || 120); // segundos
const CICLO = Number(__ENV.CICLO || 60); // cada cuántos segundos llega una pareja de «procesar»
const PAREJA = Number(__ENV.PAREJA || 2);
const SALIDA = __ENV.SALIDA || 'carga';

// k6 no inventa datos: los ids y el token los deja el seed en el volumen k6data.
const IDS = new SharedArray('ids', () => JSON.parse(open('/datos/ids.json')));
const TOKEN = open('/datos/token.txt').trim();
const auth = { Authorization: `Bearer ${TOKEN}` };
const TIPOS = ['lectura', 'procesar'];

// k6 solo informa las submétricas que tienen umbral. Estos nunca fallan: están
// para que cada tipo aparezca por separado en el resumen.
const thresholds = {};
for (const tipo of TIPOS) {
  thresholds[`http_req_duration{tipo:${tipo}}`] = ['max>=0'];
  thresholds[`http_req_failed{tipo:${tipo}}`] = ['rate>=0'];
}

export const options = {
  summaryTrendStats: ['med', 'p(95)', 'p(99)', 'max', 'avg', 'count'],
  thresholds,
  scenarios: {
    lectura: {
      executor: 'constant-arrival-rate', rate: RPS, timeUnit: '1s', duration: `${DURACION}s`,
      preAllocatedVUs: 20, maxVUs: 200, exec: 'lectura',
    },
    procesar: {
      executor: 'per-vu-iterations', vus: PAREJA, iterations: Math.max(1, Math.floor(DURACION / CICLO)),
      maxDuration: `${DURACION + 120}s`, exec: 'procesar',
    },
  },
};

export function setup() {
  // Comprueba antes de medir que el token y los ids sirven.
  const r = http.get(`${API}/api/clinic/samples/${IDS[0]}/karyotype/`, { headers: auth, tags: { tipo: 'previo' } });
  if (r.status !== 200) throw new Error(`la API no responde bien antes de medir: ${r.status} ${r.body}`);
  console.log(`${RPS} lecturas/s; ${PAREJA} «procesar» a la vez cada ${CICLO} s; ${DURACION} s; ${IDS.length} muestras`);
  return { inicio: Date.now() };
}

export function lectura() {
  // Las lecturas van sobre la segunda mitad de las muestras: las de «procesar»
  // se están reescribiendo y no deben mezclarse en la medida de lectura.
  const mitad = Math.floor(IDS.length / 2);
  const id = IDS[mitad + Math.floor(Math.random() * (IDS.length - mitad))];
  http.get(`${API}/api/clinic/samples/${id}/karyotype/`, {
    headers: auth, timeout: '10s', tags: { tipo: 'lectura', name: 'GET /samples/:id/karyotype/' },
  });
}

export function procesar(datos) {
  // Cada usuario espera al inicio de su ciclo: así los PAREJA salen a la vez.
  const transcurrido = (Date.now() - datos.inicio) / 1000;
  const espera = __ITER * CICLO - transcurrido;
  if (espera > 0) sleep(espera);
  // Cada usuario y cada vuelta usan una muestra distinta de la primera mitad.
  const mitad = Math.max(1, Math.floor(IDS.length / 2));
  const id = IDS[((__VU - 1) + __ITER * PAREJA) % mitad];
  http.post(`${API}/api/clinic/samples/${id}/process/`, '{}', {
    headers: { ...auth, 'content-type': 'application/json' }, timeout: '170s',
    tags: { tipo: 'procesar', name: 'POST /samples/:id/process/' },
  });
}

export function handleSummary(data) {
  const m = data.metrics;
  const ms = (v) => (v === undefined ? '-' : v.toFixed(0));
  const filas = [`\nresultados/${SALIDA}.json`,
    'tipo       peticiones   p50 (ms)   p95 (ms)   max (ms)   % errores'];
  for (const tipo of TIPOS) {
    const d = m[`http_req_duration{tipo:${tipo}}`];
    const e = m[`http_req_failed{tipo:${tipo}}`];
    if (!d) continue;
    const v = d.values;
    filas.push(`${tipo.padEnd(10)} ${String(v.count).padStart(10)} ${ms(v.med).padStart(10)} `
      + `${ms(v['p(95)']).padStart(10)} ${ms(v.max).padStart(10)} ${(e ? (e.values.rate * 100).toFixed(1) : '-').padStart(11)}`);
  }
  filas.push('', 'La traza lenta: Grafana (http://localhost:3000) → Explore → Tempo → TraceQL:',
    '  { resource.service.name = "backend-clinic" && name =~ "POST.*process.*" }');
  return { [`/out/${SALIDA}.json`]: JSON.stringify(data, null, 1), stdout: filas.join('\n') + '\n\n' };
}
