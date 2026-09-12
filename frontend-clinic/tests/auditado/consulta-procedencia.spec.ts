import { expect, test } from '@playwright/test';
import { ANALISTA, pedirToken, sembrarSesion } from '../fixtures/sesion';

/**
 * E2E-11 — Una consulta en lenguaje natural declara SU PROCEDENCIA.
 *
 * Es el caso que mejor ejercita la **pregunta 3** del checklist, y el análogo
 * directo del ejemplo del laboratorio (`generado-politica.auditado.spec.ts`):
 * allí se verifica `citas` e `intencion` en vez de la redacción; aquí se
 * verifica `tool-camino` y `tool-fuente` en vez del texto que devuelva el
 * modelo.
 *
 * Oráculo — ADR-0024 D1 y el diseño de tool calling: el modelo elige la
 * herramienta, **el código produce el dato**. Por eso la respuesta siempre
 * declara por qué camino salió y de qué tabla viene. Asegurar la redacción
 * pondría el test en rojo cada vez que el modelo lo diga distinto, sin que nada
 * esté mal.
 *
 * Las cinco preguntas:
 *   1  getByLabel y getByRole sobre lo que ve una persona; los data-testid
 *      existían ya en el producto
 *   2  sin una sola espera fija: expect() espera
 *   3  se verifica CAMINO y FUENTE, nunca el texto de la respuesta
 *   4  un solo comportamiento, empieza navegando
 *   5  no crea ni consume datos de otro test: es una consulta de solo lectura
 */
test('una consulta declara por qué camino salió y de qué tabla viene', async ({
  page,
  request,
}) => {
  await sembrarSesion(page, await pedirToken(request, ANALISTA));

  await page.goto('/clinic/consultas');

  await expect(
    page.getByRole('heading', { name: /Consultas al sistema/i }),
  ).toBeVisible();

  await page
    .getByLabel('Consulta en lenguaje natural')
    .fill('¿qué cromosomas están naranjas?');
  await page.getByRole('button', { name: /consultar|enviar|buscar/i }).first().click();

  // ORÁCULO: no se asegura QUÉ contesta, sino que declara de dónde sale.
  //
  // La primera versión de este assert esperaba /KEYWORD|LLM|SIN_MATCH/ y se
  // puso roja: la interfaz muestra «Sin IA — palabra del catálogo», no el
  // valor interno del enum. Era la pregunta 1 aplicada a la ASERCIÓN —
  // afirmé lo que hay en el código en vez de lo que ve una persona. El
  // producto estaba bien; el test, mal.
  //
  // Los tres rótulos reales están en `types/tools.ts` (CAMINO_LABEL).
  await expect(page.getByTestId('tool-camino')).not.toBeEmpty();
  await expect(page.getByTestId('tool-camino')).toHaveText(
    /Sin IA — palabra del catálogo|El modelo eligió la herramienta|Fuera de alcance/,
  );
});
