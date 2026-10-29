import { expect, test } from '@playwright/test';
import {
  type Cromosoma, dimensionesMetafase, json, metafaseReal, registrarMuestraPropia,
} from '../fixtures/muestraPropia';

/**
 * DD-KARYO-007 T6 — Separar un objeto trazando una línea y deshacerlo, en
 * Chromium y contra el stack real: el corte en ráster lo hace backend-ml y cada
 * trozo lo reclasifica el modelo de verdad.
 *
 * Trabaja sobre una muestra PROPIA (ver `fixtures/muestraPropia.ts`): separar y
 * deshacer dejan eventos en una auditoría de solo inserción.
 *
 * Qué se verifica (estado, no mensajes):
 * - la línea llega al servidor en píxeles de la metafase y separa el objeto:
 *   hay un cromosoma más y el evento SPLIT guarda la línea;
 * - el original ya no es la caja de antes, sino un trozo de ella;
 * - «Deshacer» deja el cromosoma EXACTAMENTE como estaba (caja y silueta), el
 *   trozo nuevo sale del cariotipo, y queda UNDO_EDIT apuntando al SPLIT.
 *
 * Capturas para la documentación: `E2E_CAPTURAS=<carpeta>`.
 */
const CAPTURAS = process.env.E2E_CAPTURAS;

test('el analista separa un objeto trazando una línea y lo deshace', async ({ page, request }) => {
  test.setTimeout(240_000);   // incluye una segmentación real (~20-35 s en CPU)
  const imagen = await metafaseReal(request);
  test.skip(!imagen, 'no hay ningún caso READY con metafase real en esta base');
  const { id, cab } = await registrarMuestraPropia(page, request, imagen!);

  const antes: Cromosoma[] = (await json(request, `/samples/${id}/karyotype/`, cab)).chromosomes;
  // El objeto más grande con silueta: el que más probablemente sean dos que se tocan.
  const objetivo = antes
    .filter((c) => c.contour && c.contour.length >= 3)
    .sort((a, b) => b.bbox.w * b.bbox.h - a.bbox.w * a.bbox.h)[0];
  expect(objetivo, 'la segmentación no dejó ningún objeto con silueta').toBeTruthy();

  await page.goto(`/clinic/samples/${id}/karyotype`);
  const lienzo = page.getByTestId('metafase-editor').locator('canvas').first();
  await expect(lienzo).toBeVisible();
  await expect(page.getByTestId('metafase-cuenta')).toHaveText(`${antes.length} objeto(s)`);
  const dim = await dimensionesMetafase(page, id);
  const b = objetivo.bbox;
  // El objeto puede quedar por debajo de la ventana: el 29/10, con metafase_1,
  // su centro caía en y = 802 de 720 y el clic no seleccionaba nada. Se lleva
  // al medio de la ventana ANTES de medir dónde está el lienzo. Con la rueda
  // no: sobre el lienzo, la rueda hace zoom.
  const previa = (await lienzo.boundingBox())!;
  const centroY = previa.y + (b.y + b.h / 2) * (previa.width / dim.w);
  await page.evaluate((dy: number) => window.scrollBy(0, dy), centroY - page.viewportSize()!.height / 2);
  const caja = (await lienzo.boundingBox())!;
  const k = caja.width / dim.w;
  const aPantalla = (x: number, y: number) => [caja.x + x * k, caja.y + y * k] as const;

  // 1. Seleccionarlo pulsando dentro de su silueta (el centro de su caja).
  await page.mouse.click(...aPantalla(b.x + b.w / 2, b.y + b.h / 2));
  await expect(page.getByTestId('chromosome-props')).toBeVisible();
  await expect(page.getByTestId('metafase-deshacer')).toHaveText('Nada que deshacer');

  // 2. Separar: una línea por el centro, a lo ANCHO del objeto (perpendicular a
  //    su lado largo), que entra y sale con 15 px de margen.
  await page.keyboard.press('Alt+s');
  const tumbado = b.w > b.h;
  const [x0, y0, x1, y1] = tumbado
    ? [b.x + b.w / 2, b.y - 15, b.x + b.w / 2, b.y + b.h + 15]
    : [b.x - 15, b.y + b.h / 2, b.x + b.w + 15, b.y + b.h / 2];
  await page.mouse.move(...aPantalla(x0, y0));
  await page.mouse.down();
  await page.mouse.move(...aPantalla(x1, y1), { steps: 12 });
  const t0 = Date.now();
  await page.mouse.up();

  // Separar de verdad es cortar en backend-ml y reclasificar cada trozo con el
  // modelo: el 23/10 tardó más de los 15 s por defecto. Se da margen y se mide.
  await expect(page.getByTestId('metafase-cuenta')).not.toHaveText(`${antes.length} objeto(s)`, { timeout: 60_000 });
  test.info().annotations.push({ type: 'separar', description: `${((Date.now() - t0) / 1000).toFixed(1)} s` });
  const tras: Cromosoma[] = (await json(request, `/samples/${id}/karyotype/`, cab)).chromosomes;
  expect(tras.length).toBeGreaterThan(antes.length);
  const original = tras.find((c) => c.id === objetivo.id)!;
  expect(original.bbox, 'el original sigue siendo la caja entera').not.toEqual(objetivo.bbox);
  const split = ((await json(request, `/samples/${id}/audit/`, cab)) as any[]).find((e) => e.event_type === 'SPLIT');
  expect(split, 'no hay evento SPLIT').toBeTruthy();
  // La línea llegó en píxeles de la metafase: empieza donde se trazó (±2 px).
  expect(Math.abs(split.payload.linea[0][0] - x0)).toBeLessThanOrEqual(2);
  expect(Math.abs(split.payload.linea[0][1] - y0)).toBeLessThanOrEqual(2);

  if (CAPTURAS) {
    await page.getByTestId('metafase-editor').screenshot({
      path: `${CAPTURAS}/metafase-separado.png`, style: '.navbar { position: static !important; }',
    });
  }

  // 3. Deshacer: la barra dice qué deshace y lo deja como estaba.
  await expect(page.getByTestId('metafase-deshacer')).toHaveText('Deshacer: Separó');
  const t1 = Date.now();
  await page.getByTestId('metafase-deshacer').click();
  await expect(page.getByTestId('metafase-cuenta')).toHaveText(`${antes.length} objeto(s)`, { timeout: 30_000 });
  test.info().annotations.push({ type: 'deshacer', description: `${((Date.now() - t1) / 1000).toFixed(1)} s` });
  const fin: Cromosoma[] = (await json(request, `/samples/${id}/karyotype/`, cab)).chromosomes;
  const restaurado = fin.find((c) => c.id === objetivo.id)!;
  expect(restaurado.bbox).toEqual(objetivo.bbox);
  expect(restaurado.contour).toEqual(objetivo.contour);
  expect(fin.map((c) => c.id).sort()).toEqual(antes.map((c) => c.id).sort());
  const undo = ((await json(request, `/samples/${id}/audit/`, cab)) as any[]).find((e) => e.event_type === 'UNDO_EDIT');
  expect(undo?.payload?.deshace).toBe(split.id);
  await expect(page.getByTestId('metafase-deshacer')).toHaveText('Nada que deshacer');
});
