import { expect, test } from '@playwright/test';
import { SUPERVISOR, pedirToken, sembrarSesion } from '../fixtures/sesion';
import { STAGE_WIDTH, chromosomePosition } from '../../src/clinic/lib/karyoLayout';

/**
 * DD-KARYO-006 §7 / T5 — El analista ve los cromosomas reales, y sin metafase
 * ve lo de siempre.
 *
 * Dos casos reales de la base, leídos por API (no se crea ni se modifica nada):
 *
 * 1. Un caso con metafase servible: el endpoint responde 200 con una imagen y
 *    el cromosoma, en el lienzo, tiene PÍXELES DE IMAGEN.
 * 2. Un caso sin metafase (los del seed de demo): el endpoint responde 404
 *    `NO_METAPHASE_IMAGE`, el lienzo pinta las cajas de color, aparece el aviso
 *    y no hay ningún error.
 *
 * ## Cómo se decide que «es una imagen» y no una caja
 *
 * El lienzo de Konva es un `<canvas>`: no hay DOM que mirar. Se cuentan los
 * niveles de gris distintos dentro del cuerpo de un cromosoma. Una caja de
 * color es un relleno liso más el número de clase con su antialias; un recorte
 * de metafase con bandas G tiene muchos más niveles.
 *
 * El umbral no se da por bueno a priori (lección M9: un instrumento se
 * equivoca antes que el sistema). El caso 2 mide LA MISMA MÉTRICA sobre una
 * caja de color y exige que quede por debajo: si un día los dos casos dieran
 * lo mismo, el test lo vería en vez de pasar en verde por accidente.
 *
 * Las cinco preguntas:
 *   1  getByTestId; dentro del canvas, coordenadas con la geometría del producto
 *   2  sin esperas fijas: `expect.poll` sobre los píxeles
 *   3  se verifican píxeles y el código del 404, no solo textos
 *   4  un comportamiento por test, empieza navegando
 *   5  solo lectura: no crea casos ni toca la auditoría (RN-05)
 *
 * Capturas para la documentación: `E2E_CAPTURAS=<carpeta>`.
 */

const CLINIC_API = process.env.E2E_CLINIC_API || 'http://localhost:8002';
const CAPTURAS = process.env.E2E_CAPTURAS;

/** Por encima, píxeles de imagen; por debajo, una caja de color con su número. */
const UMBRAL_NIVELES = 40;

interface Cromosoma {
  id: string; predicted_class: string; position_index: number;
  is_active: boolean; bbox: { x?: number; y?: number; w?: number; h?: number } | null;
}

type Cab = Record<string, string>;

async function muestrasReady(request: any, cab: Cab): Promise<string[]> {
  const lista = await (await request.get(`${CLINIC_API}/api/clinic/samples/`, { headers: cab })).json();
  const muestras = Array.isArray(lista) ? lista : lista.results ?? [];
  return muestras.filter((m: any) => m.status === 'READY').map((m: any) => m.id as string);
}

async function cariotipo(request: any, cab: Cab, id: string): Promise<Cromosoma[]> {
  const r = await request.get(`${CLINIC_API}/api/clinic/samples/${id}/karyotype/`, { headers: cab });
  if (!r.ok()) return [];
  return ((await r.json()).chromosomes as Cromosoma[]).filter((c) => c.is_active);
}

/** Niveles de gris distintos en el cuerpo del cromosoma, compuestos todos los
 *  canvas del visor (Konva usa uno por capa). El cuerpo ocupa (2, 10)–(24, 110)
 *  dentro de su grupo; se recorta 4 px por lado para no contar el borde. */
async function nivelesEnCuerpo(page: any, crom: Cromosoma): Promise<number> {
  const visor = page.getByTestId('karyotype-viewer');
  await visor.scrollIntoViewIfNeeded();
  const pos = chromosomePosition(crom);
  return page.evaluate(
    ({ x, y, w, h, ancho }: { x: number; y: number; w: number; h: number; ancho: number }) => {
      const lienzos = Array.from(
        document.querySelectorAll('[data-testid="karyotype-viewer"] canvas'),
      ) as HTMLCanvasElement[];
      if (lienzos.length === 0) return 0;
      const base = lienzos[0];
      const k = base.width / ancho; // coordenadas del Stage → píxeles del canvas
      const comp = document.createElement('canvas');
      comp.width = base.width;
      comp.height = base.height;
      const ctx = comp.getContext('2d')!;
      for (const c of lienzos) ctx.drawImage(c, 0, 0);
      const datos = ctx.getImageData(Math.round(x * k), Math.round(y * k),
        Math.max(1, Math.round(w * k)), Math.max(1, Math.round(h * k))).data;
      const niveles = new Set<number>();
      for (let i = 0; i < datos.length; i += 4) {
        niveles.add(Math.round(0.299 * datos[i] + 0.587 * datos[i + 1] + 0.114 * datos[i + 2]));
      }
      return niveles.size;
    },
    { x: pos.x + 6, y: pos.y + 14, w: 14, h: 92, ancho: STAGE_WIDTH },
  );
}

test('con metafase real, el cariograma muestra los píxeles de los cromosomas', async ({ page, request }) => {
  const tokens = await pedirToken(request, SUPERVISOR);
  const cab = { Authorization: `Bearer ${tokens.access}` };

  let caso: { id: string; crom: Cromosoma; tipo: string } | null = null;
  for (const id of await muestrasReady(request, cab)) {
    const img = await request.get(`${CLINIC_API}/api/clinic/samples/${id}/karyotype/metaphase/`,
      { headers: { ...cab, Accept: 'image/*' } });
    if (!img.ok()) continue;
    const crom = (await cariotipo(request, cab, id)).find((c) => (c.bbox?.w ?? 0) > 0);
    if (crom) { caso = { id, crom, tipo: img.headers()['content-type'] }; break; }
  }
  test.skip(!caso, 'no hay ningún caso READY con metafase real y cajas en esta base');
  const { id, crom, tipo } = caso!;
  expect(tipo, 'el tipo sale de la firma de los bytes (D2)').toMatch(/^image\/(bmp|png|jpeg)$/);

  await sembrarSesion(page, tokens);
  await page.goto(`/clinic/samples/${id}/karyotype`);
  await expect(page.getByTestId('karyotype-viewer').locator('canvas').first()).toBeVisible();
  await expect(page.getByTestId('metafase-aviso')).toHaveCount(0);

  let medido = 0;
  await expect
    .poll(async () => (medido = await nivelesEnCuerpo(page, crom)), {
      message: 'el cuerpo del cromosoma sigue pareciendo una caja de color',
    })
    .toBeGreaterThan(UMBRAL_NIVELES);
  test.info().annotations.push({ type: 'niveles', description: `${medido} (umbral ${UMBRAL_NIVELES})` });

  if (CAPTURAS) {
    await page.getByTestId('karyotype-viewer').screenshot({ path: `${CAPTURAS}/cariograma-real.png` });
  }
});

test('sin metafase, el cariograma pinta cajas de color y lo avisa, sin error', async ({ page, request }) => {
  const tokens = await pedirToken(request, SUPERVISOR);
  const cab = { Authorization: `Bearer ${tokens.access}` };

  let caso: { id: string; crom: Cromosoma } | null = null;
  for (const id of await muestrasReady(request, cab)) {
    const img = await request.get(`${CLINIC_API}/api/clinic/samples/${id}/karyotype/metaphase/`,
      { headers: { ...cab, Accept: 'image/*' } });
    if (img.status() !== 404) continue;
    if ((await img.json()).code !== 'NO_METAPHASE_IMAGE') continue;
    const crom = (await cariotipo(request, cab, id))[0];
    if (crom) { caso = { id, crom }; break; }
  }
  test.skip(!caso, 'no hay ningún caso READY sin metafase en esta base');
  const { id, crom } = caso!;

  await sembrarSesion(page, tokens);
  await page.goto(`/clinic/samples/${id}/karyotype`);
  await expect(page.getByTestId('metafase-aviso')).toContainText('no tiene una metafase');
  await expect(page.getByTestId('karyo-error')).toHaveCount(0);
  await expect(page.getByTestId('karyotype-viewer').locator('canvas').first()).toBeVisible();

  // La métrica del caso 1, aplicada a una caja: tiene que quedar por debajo.
  const niveles = await nivelesEnCuerpo(page, crom);
  test.info().annotations.push({ type: 'niveles', description: `${niveles} (umbral ${UMBRAL_NIVELES})` });
  expect(niveles, `una caja de color dio ${niveles} niveles: el umbral no separa`).toBeLessThanOrEqual(UMBRAL_NIVELES);

  if (CAPTURAS) {
    await page.getByTestId('karyotype-viewer').screenshot({ path: `${CAPTURAS}/cariograma-sin-metafase.png` });
  }
});
