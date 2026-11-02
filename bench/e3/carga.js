// Carga del experimento E3 (DD-E3-001 D8). Adaptado de la plantilla del docente
// (eterceros/mae-ds-ai, m8/demo-e3-nest, k6/carga.js y k6/comun.js).
//
// Son DOS rutas a la vez, a ritmo fijo (modelo abierto), mientras se rompe la bitácora:
//   GET /api/clinic/samples/{id}/audit/   usa la bitácora          (ruta=bitacora)
//   GET /api/clinic/samples/{id}/         NO la usa: ruta de control (ruta=control)
//
// Cada petición lleva su fase según el reloj:
//   calentamiento  [0, CALENTAMIENTO)        se descarta
//   antes          hasta INICIO_FALLA         bitácora sana
//   falla          de INICIO_FALLA a FIN_FALLA, bitácora rota por Toxiproxy (si hay FALLA)
//   despues        de FIN_FALLA a DURACION    bitácora arreglada: ¿se recupera sola?
// INICIO_FALLA, FIN_FALLA y DURACION se cuentan desde el fin del calentamiento.
//
// No se corre a mano: lo lanza correr.sh, que pasa MODO, FALLA, RPS y SALIDA.
import http from 'k6/http';
import { sleep } from 'k6';
import { SharedArray } from 'k6/data';

const API = __ENV.API || 'http://api:8000';
const TOXIPROXY = __ENV.TOXIPROXY || 'http://toxiproxy:8474';
const PROXY = 'bitacora'; // el nombre del proxy en toxiproxy.json
const MODO = __ENV.MODO || 'desconocido'; // proceso | http
const RPS = Number(__ENV.RPS || 10); // peticiones por segundo, EN CADA ruta
const CALENTAMIENTO = Number(__ENV.CALENTAMIENTO || 10);
const INICIO_FALLA = Number(__ENV.INICIO_FALLA || 10);
const FIN_FALLA = Number(__ENV.FIN_FALLA || 20);
const DURACION = Number(__ENV.DURACION || 30);
const FALLA = __ENV.FALLA || '';
if (!['', 'colgado', 'caido', 'lento'].includes(FALLA)) throw new Error(`FALLA desconocida: '${FALLA}'`);
const TOTAL = CALENTAMIENTO + DURACION;

// k6 no inventa datos: los ids y el token los deja el seed en el volumen k6data.
const IDS = new SharedArray('ids', () => JSON.parse(open('/datos/ids.json')));
const TOKEN = open('/datos/token.txt').trim();
const idAlAzar = () => IDS[Math.floor(Math.random() * IDS.length)];

const RUTAS = ['bitacora', 'control'];
const FASES = ['calentamiento', 'antes', 'falla', 'despues'];

// k6 solo informa las submétricas que tienen umbral. Estos nunca fallan: solo
// están para que cada combinación de ruta y fase aparezca en el resumen.
const thresholds = {};
for (const ruta of RUTAS) {
  for (const fase of FASES) {
    thresholds[`http_req_duration{ruta:${ruta},fase:${fase}}`] = ['max>=0'];
    thresholds[`http_req_failed{ruta:${ruta},fase:${fase}}`] = ['rate>=0'];
  }
}

const escenario = (exec) => ({
  executor: 'constant-arrival-rate', rate: RPS, timeUnit: '1s', duration: `${TOTAL}s`,
  preAllocatedVUs: 50, maxVUs: 400, exec,
});

export const options = {
  summaryTrendStats: ['med', 'p(95)', 'p(99)', 'max', 'avg', 'count'],
  thresholds,
  scenarios: {
    bitacora: escenario('bitacora'),
    control: escenario('control'),
    // Un solo usuario virtual que rompe y arregla la bitácora a su hora.
    falla: { executor: 'per-vu-iterations', vus: 1, iterations: 1, exec: 'falla', maxDuration: `${TOTAL + 5}s` },
  },
};

const auth = { Authorization: `Bearer ${TOKEN}` };
const admin = { headers: { 'content-type': 'application/json' }, tags: { fase: 'admin' } };

export function setup() {
  if (MODO === 'http') http.post(`${TOXIPROXY}/reset`, null, admin); // sin fallas de una corrida anterior
  // Comprueba antes de medir que el token y los ids sirven.
  const r = http.get(`${API}/api/clinic/samples/${IDS[0]}/audit/`, { headers: auth, tags: { fase: 'admin' } });
  if (r.status !== 200) throw new Error(`la API no responde bien antes de medir: ${r.status} ${r.body}`);
  console.log(`Forma: ${MODO}; falla: ${FALLA || 'ninguna'}; ${RPS} pet/s por ruta; ${TOTAL} s; ${IDS.length} ids`);
  return { inicio: Date.now() };
}

function fase(datos) {
  const t = (Date.now() - datos.inicio) / 1000;
  if (t < CALENTAMIENTO) return 'calentamiento';
  if (t < CALENTAMIENTO + INICIO_FALLA) return 'antes';
  if (t < CALENTAMIENTO + FIN_FALLA) return 'falla';
  return 'despues';
}

export function bitacora(datos) {
  http.get(`${API}/api/clinic/samples/${idAlAzar()}/audit/`, {
    headers: auth, timeout: '10s', tags: { ruta: 'bitacora', fase: fase(datos), name: '/samples/:id/audit/' },
  });
}

export function control(datos) {
  http.get(`${API}/api/clinic/samples/${idAlAzar()}/`, {
    headers: auth, timeout: '10s', tags: { ruta: 'control', fase: fase(datos), name: '/samples/:id/' },
  });
}

// colgado y lento son toxics; caido apaga el proxy (DD-E3-001 D9).
const TOXICS = {
  // timeout=0 hacia la bitácora: Toxiproxy acepta la conexión, la petición no llega y nadie cierra.
  colgado: { type: 'timeout', stream: 'upstream', attributes: { timeout: 0 } },
  // La respuesta llega 1 s tarde: más que el plazo por intento (300 ms) y que el total (800 ms).
  lento: { type: 'latency', stream: 'downstream', attributes: { latency: 1000 } },
};

export function falla() {
  const romper = FALLA && MODO === 'http';
  if (FALLA && !romper) console.log('Forma en proceso: no hay red que romper; las fases se miden igual.');
  sleep(CALENTAMIENTO + INICIO_FALLA);
  const toxic = TOXICS[FALLA];
  if (romper && toxic) {
    http.post(`${TOXIPROXY}/proxies/${PROXY}/toxics`, JSON.stringify({ name: FALLA, toxicity: 1, ...toxic }), admin);
  } else if (romper) {
    http.post(`${TOXIPROXY}/proxies/${PROXY}`, JSON.stringify({ enabled: false }), admin);
  }
  sleep(FIN_FALLA - INICIO_FALLA);
  if (romper && toxic) http.del(`${TOXIPROXY}/proxies/${PROXY}/toxics/${FALLA}`, null, admin);
  else if (romper) http.post(`${TOXIPROXY}/proxies/${PROXY}`, JSON.stringify({ enabled: true }), admin);
}

export function handleSummary(data) {
  const nombre = __ENV.SALIDA || `${MODO}-${FALLA || 'sin-falla'}`;
  const m = data.metrics;
  const ms = (v) => (v === undefined ? '-' : v.toFixed(1));
  const filas = [`\nForma: ${MODO} · falla: ${FALLA || 'ninguna'} · resultados/${nombre}.json`,
    'ruta      fase            peticiones   p50 (ms)   p95 (ms)   max (ms)   % errores'];
  for (const ruta of RUTAS) {
    for (const f of FASES) {
      const d = m[`http_req_duration{ruta:${ruta},fase:${f}}`];
      const e = m[`http_req_failed{ruta:${ruta},fase:${f}}`];
      if (!d) continue;
      const v = d.values;
      filas.push(`${ruta.padEnd(9)} ${f.padEnd(15)} ${String(v.count).padStart(10)} ${ms(v.med).padStart(10)} `
        + `${ms(v['p(95)']).padStart(10)} ${ms(v.max).padStart(10)} ${(e ? (e.values.rate * 100).toFixed(1) : '-').padStart(11)}`);
    }
  }
  return { [`/out/${nombre}.json`]: JSON.stringify(data, null, 1), stdout: filas.join('\n') + '\n\n' };
}
