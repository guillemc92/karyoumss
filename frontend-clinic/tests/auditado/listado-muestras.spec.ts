import { expect, test } from '@playwright/test';
import { ANALISTA, pedirToken, sembrarSesion } from '../fixtures/sesion';

/**
 * E2E-09 — El analista entra al listado y lo ve como dueño.
 *
 * Caso AÑADIDO por la auditoría del plan: el Planner no propuso ni uno para la
 * pantalla de entrada, que es por la que pasa todo usuario.
 *
 * Oráculo — RN-06: el analista ve lo suyo. No es «la página carga»: es que
 * carga CON permiso. Un 403 también «carga».
 *
 * Las cinco preguntas:
 *   1  getByRole sobre el encabezado que ve una persona
 *   2  sin esperas fijas
 *   3  verifica el estado de la pantalla, no texto generado por un modelo
 *   4  un comportamiento, empieza navegando
 *   5  solo lee; no crea datos que otro test pueda heredar
 */
test('el analista abre el listado y no recibe un aviso de acceso denegado', async ({
  page,
  request,
}) => {
  await sembrarSesion(page, await pedirToken(request, ANALISTA));

  await page.goto('/clinic/samples');

  await expect(
    page.getByRole('heading', { name: /Gestión de Muestras/i }),
  ).toBeVisible();

  // ORÁCULO (RN-06): la pantalla no puede negar el acceso a su propio dueño.
  await expect(page.getByText(/no es dueño|acceso denegado|forbidden/i)).toHaveCount(0);
});
