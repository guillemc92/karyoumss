import { expect, test } from '@playwright/test';
import { ANALISTA, pedirToken, sembrarSesion } from '../fixtures/sesion';

/**
 * SUP-05 — Un analista no entra a la bandeja del supervisor (RN-06).
 *
 * Caso AÑADIDO por la auditoría del plan de la sección «supervisor»: el
 * Planner propuso cuatro casos y ninguno era el error obvio de la pantalla.
 * RN-06 (segregación de funciones) tiene dos caras y esta es la que se ve
 * desde la bandeja: quien valida como analista no puede actuar como
 * supervisor, y la interfaz se lo dice con un aviso, no con un error.
 *
 * ## Lo que hizo el Generator y por qué se reescribió
 *
 * `SUP-05_crudo.ts` no es un test de Playwright: `test(...)({ name, url,
 * expect: {...} })` es una API inventada. Además:
 *   - `locator('data-testid="inbox-forbidden"')` sin corchetes (pregunta 1).
 *   - Afirma el texto de MI criterio del plan («Acceso restringido»), no lo
 *     que la interfaz muestra («Esta bandeja es exclusiva del Supervisor»):
 *     la pregunta 3 aplicada al plan.
 *   - Exige a la vez `inbox-error` con «Error al cargar»: un test que espera
 *     el aviso de permiso Y un error de carga no sabe qué está probando.
 *
 * Las cinco preguntas:
 *   1  getByRole('alert') y getByTestId; el texto es el que ve la persona
 *   2  sin esperas fijas: expect espera solo
 *   3  se afirma el motivo (exclusiva del supervisor), no un error genérico
 *   4  un comportamiento; empieza con page.goto
 *   5  la sesión del analista la pide el propio test
 */
test('un analista que abre la bandeja del supervisor ve el aviso de exclusividad y ningún caso', async ({
  page,
  request,
}) => {
  await sembrarSesion(page, await pedirToken(request, ANALISTA));
  await page.goto('/clinic/supervisor');

  // ORÁCULO (RN-06): la bandeja le dice al analista que no es suya.
  const aviso = page.getByTestId('inbox-forbidden');
  await expect(aviso).toBeVisible();
  await expect(aviso).toHaveText(/exclusiva del Supervisor/);

  // Y no se pinta ni el total ni un error de carga: el 403 no es un fallo.
  await expect(page.getByTestId('inbox-total-pending')).toHaveCount(0);
  await expect(page.getByTestId('inbox-error')).toHaveCount(0);
});
