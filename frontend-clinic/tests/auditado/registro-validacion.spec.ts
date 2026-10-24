import { expect, test } from '@playwright/test';
import { ANALISTA, pedirToken, sembrarSesion } from '../fixtures/sesion';

/**
 * MUE-03 — El registro no envía con los campos obligatorios vacíos.
 *
 * Caso del plan de la sección «muestras», corregido en la auditoría: el
 * Planner lo propuso como «se registra correctamente con un campo vacío»,
 * que es lo contrario de un límite. El oráculo real no es RN-03 sino la
 * validación del propio formulario.
 *
 * ## Por qué este test no existía hasta hoy
 *
 * El formulario de registro tenía los `<label>` SIN `htmlFor`, así que
 * `getByLabel('CHN')` no encontraba nada y conducirlo obligaba a selectores
 * CSS, que la pregunta 1 prohíbe. La entrega del 16/09 lo dejó anotado como
 * ancla pendiente y mandó el flujo a evals. Añadido el `htmlFor` (que además
 * es accesibilidad real: un lector de pantalla tampoco sabía qué rótulo
 * corresponde a cada campo), el flujo se prueba por la interfaz.
 *
 * ## Lo que hizo el Generator y por qué se reescribió
 *
 * `MUE-03_crudo.ts`: `input[name="chn"]` es CSS y ese campo no se llama así;
 * `expect(respuesta).toHaveText(...)` sobre la respuesta de `goto`, que no es
 * un locator; y afirma «El campo CHN es obligatorio», un texto **que el
 * modelo se inventó** — el producto dice otra cosa. La pregunta 3 en su forma
 * habitual: verifica la redacción imaginada, no lo que la interfaz promete.
 *
 * Las cinco preguntas:
 *   1  getByRole y getByLabel; el texto afirmado es el que ve una persona
 *   2  sin esperas fijas
 *   3  se afirma el aviso REAL del producto, leído de SampleRegisterPage
 *   4  un comportamiento; empieza con page.goto
 *   5  no necesita datos: el caso es precisamente no rellenar nada
 */
test('el registro con los campos obligatorios vacíos no envía y dice cuáles faltan', async ({
  page,
  request,
}) => {
  await sembrarSesion(page, await pedirToken(request, ANALISTA));
  await page.goto('/clinic/samples/register');

  await expect(
    page.getByRole('heading', { name: /Registro de Nueva Muestra/ }),
  ).toBeVisible();

  // El CHN se deja vacío a propósito: es el caso.
  await expect(page.getByLabel(/CHN \(Historia Clínica\)/)).toHaveValue('');
  await page.getByRole('button', { name: /Registrar|Guardar muestra|Enviar/i }).first().click();

  // ORÁCULO (validación del formulario): el aviso nombra los campos que
  // faltan. El texto es el de SampleRegisterPage, no uno inventado.
  await expect(page.getByText(/Complete los campos obligatorios/)).toBeVisible();

  // Y no se ha navegado a ninguna parte: el envío se detuvo.
  await expect(page).toHaveURL(/\/clinic\/samples\/register$/);
});
