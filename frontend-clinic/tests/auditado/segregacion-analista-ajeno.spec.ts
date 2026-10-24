import { expect, test } from '@playwright/test';
import { ANALISTA, chnUnico, pedirToken, sembrarSesion } from '../fixtures/sesion';

/**
 * E2E-04 — Un analista no puede abrir el caso de otro analista.
 *
 * Es el ÚNICO test del Generator con la intención correcta, y por eso es
 * «corregido» y no «descartado». Lo que se cambió:
 *
 *   - `chnUnico()` usado como id de muestra → ahora el caso se CREA de verdad
 *     por API con un segundo analista, y se usa el id que devuelve
 *   - `page.locator('data-testid="x"')` sin corchetes → getByTestId
 *   - `locator().expect('text', ...)`, que no existe → expect(...).toBeVisible()
 *   - anclas de la bandeja del supervisor y de consultas dentro de un test del
 *     visor → fuera; un comportamiento por test
 *   - comprobaba «hubo un error» → ahora comprueba que el error es de PERMISO
 *
 * Para poder afirmar lo último hubo que añadir un ancla al producto:
 * `data-testid="karyo-forbidden"`, porque el visor pintaba un 403 igual que
 * cualquier otro fallo. Agregar anclas es trabajo legítimo de QA; queda anotado.
 *
 * Oráculo — RN-06: segregación de funciones. El backend devuelve 403 NOT_OWNER
 * (probado en `test_contrato_errores_endpoints.py`); aquí se prueba que la
 * interfaz se lo DICE al analista en vez de fingir un error de servidor.
 *
 * Las cinco preguntas:
 *   1  getByTestId puesto a propósito; getByRole para el encabezado
 *   2  sin esperas fijas
 *   3  verifica el motivo del rechazo, no un texto generado
 *   4  un comportamiento, empieza navegando
 *   5  crea SU caso con SU CHN dentro del test; no hereda nada
 */

const OTRA_ANALISTA = {
  email: process.env.E2E_ANALISTA2_USER || 'ana.nueva@biomed.umss.bo',
  password: process.env.E2E_ANALISTA2_PASS || 'E2ePlaywright!2026',
};

const CLINIC_API = process.env.E2E_CLINIC_API || 'http://localhost:8002';

/** Cabecera BMP mínima de 1024x768: pasa el guardrail de metafase (>= 640x480). */
function bmpBase64(): string {
  const cabecera = Buffer.alloc(26 + 200);
  cabecera.write('BM', 0, 'ascii');
  cabecera.writeInt32LE(1024, 18);
  cabecera.writeInt32LE(768, 22);
  return cabecera.toString('base64');
}

test('un analista que no es dueño del caso recibe el aviso de segregación, no un error genérico', async ({
  page,
  request,
}) => {
  // 1. Otra analista registra SU caso, por API. Datos propios del test (P5).
  const ajena = await pedirToken(request, OTRA_ANALISTA);
  const chn = chnUnico();
  const registro = await request.post(`${CLINIC_API}/api/clinic/samples/register/`, {
    headers: { Authorization: `Bearer ${ajena.access}` },
    data: {
      sample: { chn_code: chn, sample_type: 'sangre', gender: 'F' },
      patient: { full_name: 'E2E Paciente Ajena', birth_date: '', document_id: '', phone: '' },
      clinical_history: { indication: 'E2E segregación', family_history: '' },
      analysis_requests: ['karyotype_high_res'],
      images: [1, 2, 3].map((i) => ({
        data_base64: bmpBase64(),
        filename: `metafase_${i}.bmp`,
        source: 'upload',
      })),
      is_draft: false,
    },
  });
  expect(registro.status(), await registro.text()).toBe(201);
  const { id } = await registro.json();

  // 2. El analista de siempre intenta abrir ese caso.
  await sembrarSesion(page, await pedirToken(request, ANALISTA));
  await page.goto(`/clinic/samples/${id}/karyotype`);

  // ORÁCULO (RN-06): la interfaz dice que es cuestión de PERMISO.
  await expect(page.getByTestId('karyo-forbidden')).toBeVisible();
  await expect(page.getByTestId('karyo-forbidden')).toContainText(/no es dueño/i);
  // Y no lo disfraza de fallo de servidor.
  await expect(page.getByTestId('karyo-error')).toHaveCount(0);
});
