import { expect, test } from '@playwright/test';
import {
  type Cromosoma, dimensionesMetafase, json, metafaseReal, registrarMuestraPropia,
} from '../fixtures/muestraPropia';
import { STAGE_WIDTH, posicionesCariograma } from '../../src/clinic/lib/karyoLayout';

/**
 * DD-KARYO-007 T8 — La corrección manual de punta a punta, en Chromium y
 * contra el stack real, sobre una muestra PROPIA (auditoría de solo inserción):
 *
 *   añadir → descartar → separar → deshacer → girar 180° → volver a girar
 *
 * Lo que se verifica al final es el RASTRO: la auditoría tiene, en orden,
 * ADD_OBJECT, REJECT_OBJECT, SPLIT, UNDO_EDIT y dos ORIENT, y el recuento de
 * objetos vuelve al de la segmentación.
 *
 * Girar se comprueba en los PÍXELES del cariograma, no en un atributo: el
 * cromosoma cambia al girarlo y vuelve a ser idéntico al girarlo otra vez. Lo
 * segundo es el control del instrumento: si la huella cambiara sola entre dos
 * lecturas, «cambió al girar» no demostraría nada.
 *
 * Capturas para la documentación: `E2E_CAPTURAS=<carpeta>`.
 */
const CAPTURAS = process.env.E2E_CAPTURAS;

/** Huella de los píxeles del hueco de un cromosoma en el cariograma. */
async function huellaEnCariograma(page: any, pos: { x: number; y: number }): Promise<string> {
  const visor = page.getByTestId('karyotype-viewer');
  await visor.scrollIntoViewIfNeeded();
  return page.evaluate(({ x, y, ancho }: { x: number; y: number; ancho: number }) => {
    const lienzo = document.querySelector('[data-testid="karyotype-viewer"] canvas') as HTMLCanvasElement;
    const k = lienzo.width / ancho;
    const datos = lienzo.getContext('2d')!.getImageData(Math.round(x * k), Math.round(y * k),
      Math.round(26 * k), Math.round(104 * k)).data;
    let h = 0;
    for (let i = 0; i < datos.length; i += 1) h = (h * 31 + datos[i]) >>> 0;
    return `${h}`;
  }, { x: pos.x, y: pos.y + 8, ancho: STAGE_WIDTH });
}

test('corrección manual completa: añadir, descartar, separar, deshacer y orientar', async ({ page, request }) => {
  test.setTimeout(300_000);
  const imagen = await metafaseReal(request);
  test.skip(!imagen, 'no hay ningún caso READY con metafase real en esta base');
  const { id, cab } = await registrarMuestraPropia(page, request, imagen!);
  const inicio: Cromosoma[] = (await json(request, `/samples/${id}/karyotype/`, cab)).chromosomes;

  await page.goto(`/clinic/samples/${id}/karyotype`);
  const editor = page.getByTestId('metafase-editor');
  const lienzo = editor.locator('canvas').first();
  await expect(lienzo).toBeVisible();
  const cuenta = page.getByTestId('metafase-cuenta');
  await expect(cuenta).toHaveText(`${inicio.length} objeto(s)`);
  const dim = await dimensionesMetafase(page, id);
  const enPantalla = async (x: number, y: number) => {
    await lienzo.scrollIntoViewIfNeeded();
    const c = (await lienzo.boundingBox())!;
    const k = c.width / dim.w;
    return [c.x + x * k, c.y + y * k] as const;
  };

  // 1. Añadir en una zona libre de 40 px.
  const L = 40;
  const choca = (x: number, y: number) => inicio.some(({ bbox: b }) =>
    x < b.x + b.w + 10 && x + L + 10 > b.x && y < b.y + b.h + 10 && y + L + 10 > b.y);
  let libre: { x: number; y: number } | null = null;
  for (let y = 20; !libre && y + L < dim.h - 20; y += 20) {
    for (let x = 20; x + L < dim.w - 20; x += 20) if (!choca(x, y)) { libre = { x, y }; break; }
  }
  expect(libre, 'la metafase no tiene ninguna zona libre').toBeTruthy();
  await page.getByTestId('metafase-herramienta-anadir').click();
  await page.mouse.move(...(await enPantalla(libre!.x, libre!.y)));
  await page.mouse.down();
  await page.mouse.move(...(await enPantalla(libre!.x + L, libre!.y + L)), { steps: 5 });
  await page.mouse.up();
  await expect(cuenta).toHaveText(`${inicio.length + 1} objeto(s)`, { timeout: 30_000 });

  // 2. Descartarlo (queda seleccionado tras añadirlo).
  await page.keyboard.press('Escape');
  await page.keyboard.press('Delete');
  await page.getByTestId('metafase-motivo').selectOption('suciedad');
  await page.getByTestId('metafase-confirmar').click();
  await expect(cuenta).toHaveText(`${inicio.length} objeto(s)`, { timeout: 30_000 });

  // 3. Separar el objeto más grande con silueta, y 4. deshacerlo.
  const objetivo = inicio
    .filter((c) => c.contour && c.contour.length >= 3)
    .sort((a, b) => b.bbox.w * b.bbox.h - a.bbox.w * a.bbox.h)[0];
  const b = objetivo.bbox;
  await page.mouse.click(...(await enPantalla(b.x + b.w / 2, b.y + b.h / 2)));
  await expect(page.getByTestId('chromosome-props')).toBeVisible();
  await page.keyboard.press('Alt+s');
  const [x0, y0, x1, y1] = b.w > b.h
    ? [b.x + b.w / 2, b.y - 15, b.x + b.w / 2, b.y + b.h + 15]
    : [b.x - 15, b.y + b.h / 2, b.x + b.w + 15, b.y + b.h / 2];
  await page.mouse.move(...(await enPantalla(x0, y0)));
  await page.mouse.down();
  await page.mouse.move(...(await enPantalla(x1, y1)), { steps: 12 });
  await page.mouse.up();
  await expect(cuenta).not.toHaveText(`${inicio.length} objeto(s)`, { timeout: 60_000 });
  if (CAPTURAS) {
    await editor.screenshot({ path: `${CAPTURAS}/flujo-separado.png`, style: '.navbar { position: static !important; }' });
  }
  await page.getByTestId('metafase-deshacer').click();
  await expect(cuenta).toHaveText(`${inicio.length} objeto(s)`, { timeout: 30_000 });

  // 5. Girar 180° en el cariograma: cambian los píxeles; girar otra vez los devuelve.
  const activos: Cromosoma[] = (await json(request, `/samples/${id}/karyotype/`, cab)).chromosomes;
  const pos = posicionesCariograma(activos as any).get(objetivo.id)!;
  await page.mouse.click(...(await enPantalla(b.x + b.w / 2, b.y + b.h / 2)));
  await expect(page.getByTestId('action-girar')).toBeVisible();
  const antes = await huellaEnCariograma(page, pos);
  expect(await huellaEnCariograma(page, pos), 'la huella cambia sin tocar nada: el instrumento no sirve').toBe(antes);
  await page.getByTestId('action-girar').click();
  await expect.poll(() => huellaEnCariograma(page, pos), { timeout: 15_000 }).not.toBe(antes);
  if (CAPTURAS) {
    await page.getByTestId('karyotype-viewer').screenshot({ path: `${CAPTURAS}/flujo-girado.png` });
  }
  await page.getByTestId('action-girar').click();
  await expect.poll(() => huellaEnCariograma(page, pos), { timeout: 15_000 }).toBe(antes);

  // 6. El rastro, en orden, y el caso como empezó.
  const eventos = ((await json(request, `/samples/${id}/audit/`, cab)) as any[]).map((e) => e.event_type)
    .filter((t: string) => ['ADD_OBJECT', 'REJECT_OBJECT', 'SPLIT', 'UNDO_EDIT', 'ORIENT'].includes(t));
  expect(eventos).toEqual(['ADD_OBJECT', 'REJECT_OBJECT', 'SPLIT', 'UNDO_EDIT', 'ORIENT', 'ORIENT']);
  const fin: Cromosoma[] = (await json(request, `/samples/${id}/karyotype/`, cab)).chromosomes;
  expect(fin.map((c) => c.id).sort()).toEqual(inicio.map((c) => c.id).sort());
});
