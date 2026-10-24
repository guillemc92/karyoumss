import { expect, test } from '@playwright/test';
import { ANALISTA, chnUnico, pedirToken, sembrarSesion } from '../fixtures/sesion';

/**
 * MUE-01 — Registrar una muestra con metafases desde la interfaz.
 *
 * Caso del plan de la sección «muestras», corregido en la auditoría: el
 * Planner proponía «la muestra se registra con datos cifrados», y el cifrado
 * no es algo que una persona vea — es un hecho del servidor. El criterio se
 * reescribió a lo que la interfaz promete.
 *
 * ## Por qué es el flujo que faltaba
 *
 * La entrega del 16/09 probaba el registro **por API** (dentro de
 * modo-degradado.spec.ts) porque el formulario no se podía conducir: sus
 * `<label>` no tenían `htmlFor`. Probar por API el flujo que una persona hace
 * a mano deja sin cubrir justo lo que el usuario toca. Con las anclas puestas,
 * este test recorre el formulario como lo haría el analista.
 *
 * ## Lo que hizo el Generator y por qué se reescribió
 *
 * `MUE-01_crudo.ts`: `input[name="chn"]` (CSS, y ese campo no se llama así),
 * cuatro `waitForSelector`, `data-testid="x"` sin corchetes, comillas
 * desbalanceadas que ni compilan, y **cinco pantallas en un solo test** —
 * incluida la bandeja del supervisor y la de consultas, que no tienen nada
 * que ver con registrar. Inventó además la ruta `/clinic/samples/validado`.
 *
 * ## Por qué tres imágenes y no veinte
 *
 * La interfaz recomienda 20 metafases y el servicio exige 3 (`handleSubmit`
 * de SampleRegisterPage). El test usa el mínimo real: subir veinte no prueba
 * nada más y multiplica por siete el tiempo de la suite.
 *
 * Las cinco preguntas:
 *   1  getByLabel y getByRole; el único data-testid es el del input de
 *      fichero, que está oculto a propósito y no tiene rótulo visible
 *   2  sin esperas fijas
 *   3  se verifica el ESTADO (la muestra existe con su CHN), no un mensaje
 *   4  un comportamiento —registrar—, empieza con page.goto
 *   5  CHN único por corrida
 */
const CLINIC_API = process.env.E2E_CLINIC_API || 'http://localhost:8002';

/** BMP mínimo válido: sirve de metafase sin arrastrar un fichero al repo. */
function bmpFalso(): Buffer {
  const b = Buffer.alloc(26 + 200);
  b.write('BM', 0, 'ascii');
  b.writeInt32LE(1024, 18);
  b.writeInt32LE(768, 22);
  return b;
}

test('el analista registra una muestra con metafases desde el formulario', async ({
  page,
  request,
}) => {
  const sesion = await pedirToken(request, ANALISTA);
  const chn = chnUnico();

  await sembrarSesion(page, sesion);
  await page.goto('/clinic/samples/register');

  await page.getByLabel(/CHN \(Historia Clínica\)/).fill(chn);
  await page.getByLabel(/Nombre completo/).fill('Paciente E2E');
  // La fecha de recolección está marcada con * en la pantalla. Dejarla vacía
  // hacía que el servidor respondiera 400 («Fecha con formato erróneo»), y ahí
  // salió a la luz el defecto de `[object Object]` que este test destapó.
  await page.getByLabel(/Fecha de recolección/).fill('2026-09-23');

  // El input de fichero está oculto y se dispara desde un botón, así que no
  // hay rótulo que una persona vea: por eso lleva data-testid (§5).
  await page.getByTestId('metafase-file-input').setInputFiles(
    [0, 1, 2].map((i) => ({
      name: `metafase_${i}.bmp`,
      mimeType: 'image/bmp',
      buffer: bmpFalso(),
    })),
  );

  // La interfaz cuenta lo que lleva subido: esa es la promesa intermedia.
  await expect(page.getByText(/Metafases capturadas \(3\//)).toBeVisible();

  await page.getByRole('button', { name: /Registrar y analizar con IA/ }).click();

  // ORÁCULO: la muestra EXISTE en el servidor con el CHN que se tecleó. Es un
  // estado comprobable, no el texto del modal de progreso, que cambia según
  // si el pipeline de IA está vivo.
  await expect(async () => {
    const r = await request.get(`${CLINIC_API}/api/clinic/samples/`, {
      headers: { Authorization: `Bearer ${sesion.access}` },
    });
    expect(r.ok()).toBeTruthy();
    const creada = (await r.json()).find((m: { chn_code: string }) => m.chn_code === chn);
    expect(creada, `la muestra ${chn} debe existir tras registrarla`).toBeTruthy();
  }).toPass();

  // Y RN-03: el nombre del paciente no se pinta en ninguna parte.
  await expect(page.getByText('Paciente E2E', { exact: true })).toHaveCount(0);
});
