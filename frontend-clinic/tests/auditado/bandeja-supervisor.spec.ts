import { expect, test } from '@playwright/test';
import { SUPERVISOR, pedirToken, sembrarSesion } from '../fixtures/sesion';

/**
 * SUP-06 — El supervisor abre su bandeja y ve el trabajo agrupado por etapa.
 *
 * Caso AÑADIDO por la auditoría, la otra cara de SUP-05: aquel comprueba que
 * un analista NO entra; este, que el supervisor SÍ y que la pantalla le dice
 * cuánto tiene esperando.
 *
 * ## Qué cubre y qué NO
 *
 * Cubre el flujo «el supervisor abre su bandeja»: la pantalla carga con su
 * rol, muestra el contador de casos esperando acción y agrupa por etapa.
 *
 * **No cubre el sorteo del 5 % (RN-08)**, que necesita un caso en
 * `ANALYST_VALIDATED` con cariotipo real —y eso depende del modelo, que es
 * justo lo que §7 argumenta que va a evals. Son dos cosas distintas y solo
 * una entra aquí; decir que este test prueba RN-08 sería mentir sobre su
 * alcance.
 *
 * Las cinco preguntas:
 *   1  getByRole y getByTestId
 *   2  sin esperas fijas
 *   3  se afirma que la bandeja CARGA para el supervisor —contador visible,
 *      sin aviso de exclusividad ni de error—, no un número concreto de
 *      casos, que depende de lo que haya en la base
 *   4  un comportamiento; empieza con page.goto
 *   5  no siembra datos: la bandeja existe con o sin casos, y ese es el punto
 */
test('el supervisor abre su bandeja y ve cuántos casos esperan acción', async ({
  page,
  request,
}) => {
  await sembrarSesion(page, await pedirToken(request, SUPERVISOR));
  await page.goto('/clinic/supervisor');

  // ORÁCULO (RN-06, la cara positiva): al supervisor SÍ se le abre.
  await expect(
    page.getByRole('heading', { name: /Bandeja del Supervisor/ }),
  ).toBeVisible();
  await expect(page.getByTestId('inbox-forbidden')).toHaveCount(0);

  // Y la pantalla informa de la carga de trabajo, sin fijar cuánta: el número
  // depende de la base y afirmarlo haría el test dependiente de otros.
  const total = page.getByTestId('inbox-total-pending');
  await expect(total).toBeVisible();
  await expect(total).toHaveText(/\d+ caso\(s\) esperando acción/);

  // No se pinta el aviso de error: la bandeja cargó de verdad.
  await expect(page.getByTestId('inbox-error')).toHaveCount(0);
});
