import { expect, test } from '@playwright/test';
import { ANALISTA, chnUnico, pedirToken, sembrarSesion } from '../fixtures/sesion';

/**
 * MUE-07 — Editar una muestra guarda el cambio y vuelve al listado.
 *
 * Caso AÑADIDO por la auditoría: el Planner no propuso la edición pese a
 * tener la ruta en su contexto, igual que no propuso ninguno de los casos de
 * error obvios de su sección.
 *
 * ## El flujo estaba mal clasificado, y conviene decirlo
 *
 * La entrega del 16/09 mandó este flujo a evals con el motivo «mismo
 * formulario que el registro, sin htmlFor». Es falso: la edición usa
 * `SampleFormModal`, **otro componente, que tenía `htmlFor` desde siempre**.
 * El diagnóstico del formulario de registro se extendió a este sin
 * comprobarlo. Se podía haber probado desde el primer día.
 *
 * ## Lo que hizo el Generator y por qué se reescribió
 *
 * `MUE-07_crudo.ts`: `chnUnico().id` sobre un string —el MISMO fallo que
 * E2E-03 y E2E-06 en la tanda del 11/09, repetido seis semanas después—,
 * `input[name="patient"]` que es CSS y no existe, y `page.waitForChange()`,
 * que no es una función de Playwright.
 *
 * Las cinco preguntas:
 *   1  getByLabel y getByRole
 *   2  sin esperas fijas
 *   3  se verifica el ESTADO persistido (el valor vuelve a salir tras
 *      recargar la pantalla), no un mensaje de éxito
 *   4  un comportamiento; empieza con page.goto
 *   5  crea su propia muestra por API, con CHN único
 */
const CLINIC_API = process.env.E2E_CLINIC_API || 'http://localhost:8002';

test('al editar el paciente de una muestra el cambio queda guardado', async ({
  page,
  request,
}) => {
  const sesion = await pedirToken(request, ANALISTA);
  const chn = chnUnico();

  // Datos propios del test (pregunta 5): la muestra se crea por API para que
  // el test mida SOLO la edición, no el registro, que tiene su propio test.
  const alta = await request.post(`${CLINIC_API}/api/clinic/samples/`, {
    headers: { Authorization: `Bearer ${sesion.access}` },
    data: { chn_code: chn, patient_ref: 'PAC-ORIGINAL' },
  });
  expect(alta.ok()).toBeTruthy();

  // El POST devuelve un ECO de lo enviado (chn_code, patient_ref, image_path,
  // metadata) y NO el id del recurso creado. Suponer `alta.json().id` dejaba
  // la URL en `/clinic/samples/undefined/edit` — el mismo fallo que se le
  // reprocha al Generator, por otra via. El id se busca en el listado.
  const listado = await request.get(`${CLINIC_API}/api/clinic/samples/`, {
    headers: { Authorization: `Bearer ${sesion.access}` },
  });
  expect(listado.ok()).toBeTruthy();
  const muestra = (await listado.json()).find((m: { chn_code: string }) => m.chn_code === chn);
  expect(muestra, `la muestra ${chn} recien creada debe estar en el listado`).toBeTruthy();
  const id = muestra.id;

  await sembrarSesion(page, sesion);
  await page.goto(`/clinic/samples/${id}/edit`);

  await expect(page.getByRole('heading', { name: 'Editar Muestra' })).toBeVisible();
  await page.getByLabel('Paciente *').fill('PAC-CORREGIDO');
  await page.getByRole('button', { name: /Guardar|Actualizar/i }).click();

  // Vuelve al listado por sí solo: es lo que promete el formulario.
  await expect(page).toHaveURL(/\/clinic\/samples$/);

  // ORÁCULO: el cambio PERSISTE. Se vuelve a abrir la pantalla en vez de
  // creerse un mensaje de éxito — un toast puede mentir, el dato releído no.
  await page.goto(`/clinic/samples/${id}/edit`);
  await expect(page.getByLabel('Paciente *')).toHaveValue('PAC-CORREGIDO');
});
