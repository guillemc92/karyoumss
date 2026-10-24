import { expect, test } from '@playwright/test';
import { ANALISTA, chnUnico, pedirToken, sembrarSesion } from '../fixtures/sesion';

/**
 * E2E-07 — Con la IA caída, la muestra se registra igual (RN-07).
 *
 * Único caso del Planner aceptado sin tocar: flujo, ruta y oráculo coherentes.
 * El test del Generator, en cambio, se descartó: comprobaba el banner de
 * degradación sin provocar la condición que lo produce.
 *
 * ## Cómo se provoca la degradación de verdad
 *
 * backend-ml NO está levantado en esta suite (es el proceso que carga el modelo
 * de 42 MB). Eso no es una limitación que se esquiva: ES el escenario. El
 * circuit breaker de `pipeline_client` recibe connection refused y el registro
 * sigue adelante (RN-07).
 *
 * ## Por qué se registra por API y no por el formulario
 *
 * El formulario de registro tiene sus `<label>` sin `htmlFor`: son decorativos y
 * `getByLabel` no los encuentra. Conducirlo exigiría selectores CSS, que es lo
 * que la pregunta 1 prohíbe. Se anota como ancla pendiente del producto y aquí
 * se entra por la API, que es el mismo backend real. Lo que se prueba en la
 * interfaz es la CONSECUENCIA: la muestra existe, y el visor dice honestamente
 * que aún no hay cariotipo.
 *
 * Oráculo — RN-07 + ADR-0036: la muestra persiste, `degraded` es true,
 * `analyzed_count` es 0, y la UI no finge un cariotipo que no existe.
 *
 * Las cinco preguntas:
 *   1  getByRole / getByTestId
 *   2  sin esperas fijas
 *   3  se verifica un ESTADO (sin cariotipo), no un texto de modelo
 *   4  un comportamiento, empieza navegando
 *   5  crea su propio caso con CHN único
 */

const CLINIC_API = process.env.E2E_CLINIC_API || 'http://localhost:8002';

function bmpBase64(): string {
  const cabecera = Buffer.alloc(26 + 200);
  cabecera.write('BM', 0, 'ascii');
  cabecera.writeInt32LE(1024, 18);
  cabecera.writeInt32LE(768, 22);
  return cabecera.toString('base64');
}

test('con el pipeline de IA caído la muestra queda registrada y el visor lo dice sin fingir un cariotipo', async ({
  page,
  request,
}) => {
  const sesion = await pedirToken(request, ANALISTA);
  const chn = chnUnico();

  const registro = await request.post(`${CLINIC_API}/api/clinic/samples/register/`, {
    headers: { Authorization: `Bearer ${sesion.access}` },
    data: {
      sample: { chn_code: chn, sample_type: 'sangre', gender: 'M' },
      patient: { full_name: 'E2E Paciente Degradado', birth_date: '', document_id: '', phone: '' },
      clinical_history: { indication: 'E2E modo degradado', family_history: '' },
      analysis_requests: ['karyotype_high_res'],
      images: [1, 2, 3].map((i) => ({
        data_base64: bmpBase64(),
        filename: `metafase_${i}.bmp`,
        source: 'upload',
      })),
      is_draft: false,
    },
  });

  // ORÁCULO 1 (RN-07, en el backend real): se registró pese a la IA caída.
  expect(registro.status(), await registro.text()).toBe(201);
  const cuerpo = await registro.json();
  expect(cuerpo.degraded).toBe(true);
  expect(cuerpo.image_count).toBe(3);
  // ADR-0036: se guardaron tres y no se analizó ninguna. Y se dice.
  expect(cuerpo.analyzed_count).toBe(0);

  // ORÁCULO 2 (en la interfaz): la muestra existe y se puede abrir.
  await sembrarSesion(page, sesion);
  await page.goto(`/clinic/samples/${cuerpo.id}`);
  await expect(page.getByRole('heading', { name: chn })).toBeVisible();

  // ORÁCULO 3 (en la interfaz): el visor no inventa un cariotipo. Dice que no
  // lo hay todavía, que es la verdad del sistema degradado.
  await page.goto(`/clinic/samples/${cuerpo.id}/karyotype`);
  await expect(page.getByTestId('karyo-error')).toContainText(/aún no tiene un cariotipo/i);
});
