import { expect, test } from '@playwright/test';
import { ANALISTA, SUPERVISOR, chnUnico, pedirToken, sembrarSesion } from '../fixtures/sesion';

/**
 * DD-KARYO-007 T3 — Añadir y descartar objetos sobre la metafase, en Chromium
 * y contra el stack real (backend-ml incluido: la clase del objeto nuevo la
 * pone el clasificador de verdad).
 *
 * ## Datos propios, nunca un caso existente
 *
 * Añadir y descartar emiten eventos en una auditoría que solo admite
 * inserciones (RN-05): lo que se haga en un caso ya no se puede quitar. Así que
 * el test lee (solo lectura) la metafase real de un caso de la base, registra
 * con ella una muestra NUEVA con CHN único y trabaja sobre esa.
 *
 * ## Qué se verifica
 *
 * Estado, no mensajes: el recuento de objetos en la metafase y los eventos
 * ADD_OBJECT / REJECT_OBJECT que devuelve la API de auditoría, con su payload.
 *
 * Capturas para la documentación: `E2E_CAPTURAS=<carpeta>`.
 */

const CLINIC_API = process.env.E2E_CLINIC_API || 'http://localhost:8002';
const CAPTURAS = process.env.E2E_CAPTURAS;

type Cab = Record<string, string>;
interface Cromosoma { id: string; bbox: { x: number; y: number; w: number; h: number }; contour?: number[][] | null }

async function json(request: any, url: string, cab: Cab) {
  const r = await request.get(`${CLINIC_API}/api/clinic${url}`, { headers: cab });
  return r.ok() ? r.json() : null;
}

/** Una metafase real de la base, leída sin tocar nada. */
async function metafaseReal(request: any, cab: Cab): Promise<Buffer | null> {
  const lista = await json(request, '/samples/', cab);
  for (const m of (Array.isArray(lista) ? lista : lista?.results ?? [])) {
    if (m.status !== 'READY') continue;
    const r = await request.get(`${CLINIC_API}/api/clinic/samples/${m.id}/karyotype/metaphase/`,
      { headers: { ...cab, Accept: 'image/*' } });
    if (r.ok()) return Buffer.from(await r.body());
  }
  return null;
}

/** Una zona de 40 × 40 px de la metafase que no toca ningún objeto. */
function zonaLibre(crom: Cromosoma[], ancho: number, alto: number) {
  const L = 40;
  const choca = (x: number, y: number) => crom.some(({ bbox: b }) =>
    x < b.x + b.w + 10 && x + L + 10 > b.x && y < b.y + b.h + 10 && y + L + 10 > b.y);
  for (let y = 20; y + L < alto - 20; y += 20) {
    for (let x = 20; x + L < ancho - 20; x += 20) {
      if (!choca(x, y)) return { x, y, w: L, h: L };
    }
  }
  return null;
}

test('el analista añade un cromosoma que faltaba y lo descarta, con su rastro en la auditoría', async ({ page, request }) => {
  test.setTimeout(240_000);   // incluye una segmentación real (~20-35 s en CPU)

  const sup = await pedirToken(request, SUPERVISOR);
  const imagen = await metafaseReal(request, { Authorization: `Bearer ${sup.access}` });
  test.skip(!imagen, 'no hay ningún caso READY con metafase real en esta base');

  // 1. Muestra propia, registrada desde la interfaz con la metafase real.
  const sesion = await pedirToken(request, ANALISTA);
  const cab = { Authorization: `Bearer ${sesion.access}` };
  const chn = chnUnico();
  await sembrarSesion(page, sesion);
  await page.goto('/clinic/samples/register');
  await page.getByLabel(/CHN \(Historia Clínica\)/).fill(chn);
  await page.getByLabel(/Nombre completo/).fill('Paciente E2E');
  await page.getByLabel(/Fecha de recolección/).fill('2026-10-23');
  await page.getByTestId('metafase-file-input').setInputFiles(
    [0, 1, 2].map((i) => ({ name: `metafase_${i}.bmp`, mimeType: 'image/bmp', buffer: imagen! })),
  );
  await page.getByRole('button', { name: /Registrar y analizar con IA/ }).click();

  let id = '';
  await expect(async () => {
    const lista = await json(request, '/samples/', cab);
    const m = (Array.isArray(lista) ? lista : lista?.results ?? []).find((s: any) => s.chn_code === chn);
    expect(m?.status, `la muestra ${chn} todavía no tiene cariotipo`).toBe('READY');
    id = m.id;
  }).toPass({ timeout: 150_000, intervals: [3_000] });

  const antes: Cromosoma[] = (await json(request, `/samples/${id}/karyotype/`, cab)).chromosomes;

  // 2. El editor, con los objetos que dejó la segmentación.
  // Cada descarga de la metafase son ~3 MB y, además, vuelve a montar el editor
  // (se pierden el zoom y la herramienta). Una corrección no debe provocarla.
  let descargas = 0;
  page.on('request', (r: any) => { if (r.url().includes('/karyotype/metaphase/')) descargas += 1; });
  await page.goto(`/clinic/samples/${id}/karyotype`);
  const lienzo = page.getByTestId('metafase-editor').locator('canvas').first();
  await expect(lienzo).toBeVisible();
  await expect(page.getByTestId('metafase-cuenta')).toHaveText(`${antes.length} objeto(s)`);

  const dim = await page.evaluate(async (url) => {
    const r = await fetch(url, { headers: { Authorization: `Bearer ${localStorage.getItem('biomed.auth.access') ?? ''}`, Accept: 'image/*' } });
    const bmp = await createImageBitmap(await r.blob());
    return { w: bmp.width, h: bmp.height };
  }, `/api/clinic/samples/${id}/karyotype/metaphase/`);
  const libre = zonaLibre(antes, dim.w, dim.h);
  expect(libre, 'la metafase no tiene ninguna zona libre de 40 px').toBeTruthy();

  // 3. Añadir: dibujar la caja sobre la zona libre.
  // Entrar en «Añadir» no puede mover el lienzo. El 23/10 lo movía: aparecía el
  // selector de clase, la barra crecía y la caja llegaba 6 px más arriba.
  const antesDeAnadir = (await lienzo.boundingBox())!;
  await page.getByTestId('metafase-herramienta-anadir').click();
  const caja = (await lienzo.boundingBox())!;
  expect(caja.y, 'el lienzo se movió al entrar en «Añadir»').toBeCloseTo(antesDeAnadir.y, 0);
  const k = caja.width / dim.w;
  await page.mouse.move(caja.x + libre!.x * k, caja.y + libre!.y * k);
  await page.mouse.down();
  await page.mouse.move(caja.x + (libre!.x + libre!.w) * k, caja.y + (libre!.y + libre!.h) * k, { steps: 5 });
  await page.mouse.up();

  await expect(page.getByTestId('metafase-cuenta')).toHaveText(`${antes.length + 1} objeto(s)`);
  await expect(page.getByTestId('chromosome-props')).toBeVisible();   // el nuevo queda seleccionado
  // La herramienta sigue activa para el siguiente cromosoma que falte.
  await expect(page.getByTestId('metafase-herramienta-anadir')).toHaveAttribute('aria-pressed', 'true');
  const descargasTrasCargar = descargas;
  const tras = (await json(request, `/samples/${id}/audit/`, cab)) as any[];
  const anadido = tras.find((e) => e.event_type === 'ADD_OBJECT');
  expect(anadido, 'no hay evento ADD_OBJECT').toBeTruthy();
  expect(anadido.payload.clasificado_por).toBe('modelo');   // lo clasificó backend-ml, no el doble
  // La caja que llegó al servidor es la dibujada, en píxeles de la metafase (±2 px).
  for (const c of ['x', 'y', 'w', 'h'] as const) {
    expect(Math.abs(anadido.payload.bbox[c] - libre![c]), `bbox.${c}`).toBeLessThanOrEqual(2);
  }

  if (CAPTURAS) {
    await page.getByTestId('metafase-editor').screenshot({
      path: `${CAPTURAS}/metafase-anadido.png`, style: '.navbar { position: static !important; }',
    });
  }

  // 4. Descartar el objeto añadido, con motivo.
  await page.keyboard.press('Escape');                     // vuelve a seleccionar
  await page.getByTestId('metafase-descartar').click();
  await page.getByTestId('metafase-motivo').selectOption('otro');
  await page.getByTestId('metafase-confirmar').click();

  await expect(page.getByTestId('metafase-cuenta')).toHaveText(`${antes.length} objeto(s)`);
  await expect(page.getByTestId('chromosome-props-empty')).toBeVisible();
  const fin = (await json(request, `/samples/${id}/audit/`, cab)) as any[];
  const descarte = fin.find((e) => e.event_type === 'REJECT_OBJECT');
  expect(descarte, 'no hay evento REJECT_OBJECT').toBeTruthy();
  expect(descarte.chromosome).toBe(anadido.chromosome);
  expect(descarte.payload.motivo).toBe('otro');
  expect(descargas, 'añadir o descartar volvió a descargar la metafase').toBe(descargasTrasCargar);
});
