import { expect, test } from '@playwright/test';
import { ANALISTA, pedirToken, sembrarSesion } from '../fixtures/sesion';

/**
 * CON-05 — La página de modo degradado dice qué pasa y qué se puede hacer.
 *
 * Caso AÑADIDO por la auditoría. En el inventario del 16/09 este flujo estaba
 * descartado como «informativa, sin regla detrás», y eso era un error de
 * criterio mío: es la cara visible de RN-07 (degradación elegante). Cuando el
 * pipeline cae, esta pantalla es lo único que el analista tiene, y que
 * explique las alternativas es justo lo que la regla exige.
 *
 * ## No se solapa con modo-degradado.spec.ts
 *
 * Aquel prueba el COMPORTAMIENTO: con backend-ml caído de verdad, la muestra
 * se registra igual y el visor no finge un cariotipo. Este prueba la PÁGINA:
 * que el aviso esté redactado con salida, no solo con la mala noticia. Son
 * dos cosas distintas y por eso son dos tests, no uno más largo (pregunta 4).
 *
 * Las cinco preguntas:
 *   1  getByRole sobre el alert, el encabezado y el enlace
 *   2  sin esperas fijas
 *   3  se afirma que hay salida (lista de alternativas + vuelta al listado),
 *      no la redacción exacta del aviso
 *   4  un comportamiento; empieza con page.goto
 *   5  no necesita datos propios: la página es estática
 */
test('la página de modo degradado anuncia la caída y ofrece qué hacer mientras tanto', async ({
  page,
  request,
}) => {
  await sembrarSesion(page, await pedirToken(request, ANALISTA));
  await page.goto('/clinic/degraded');

  // ORÁCULO (RN-07): la aplicación lo DICE en vez de romperse.
  const aviso = page.getByRole('alert');
  await expect(aviso).toBeVisible();
  await expect(
    page.getByRole('heading', { name: /Modo Degradado/ }),
  ).toBeVisible();

  // Y no se queda en la mala noticia: enumera alternativas y deja volver.
  await expect(aviso.getByRole('listitem')).not.toHaveCount(0);
  await expect(page.getByRole('link', { name: /Volver a la lista/ })).toBeVisible();
});
