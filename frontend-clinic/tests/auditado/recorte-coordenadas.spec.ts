import { expect, test } from '@playwright/test';
import { SUPERVISOR, pedirToken, sembrarSesion } from '../fixtures/sesion';
import { STAGE_WIDTH, chromosomePosition } from '../../src/clinic/lib/karyoLayout';
import { aPanel, escalaPanel, regionDeRecorte } from '../../src/clinic/lib/recorteMetafase';

/**
 * DD-KARYO-006 §2 / T4 — El recorte manual tiene que caer sobre el cromosoma.
 *
 * El analista selecciona un cromosoma, pulsa «Recortar y reclasificar» y, en el
 * panel «Metafase», dibuja el rectángulo EXACTAMENTE sobre el recuadro del
 * recorte actual. El `bbox` que el visor envía está en píxeles de la metafase
 * (`Chromosome.bbox`), así que tiene que coincidir con la caja que ese
 * cromosoma ya tiene en ella, salvo el redondeo a píxel.
 *
 * Antes de D7 este test FALLABA (13/10): el rectángulo se dibujaba sobre el
 * cariograma y se enviaba en sus coordenadas, `{x: 9, y: 18, w: 22, h: 100}`
 * para un cromosoma que estaba en `{x: 448, y: 35, w: 175, h: 73}`.
 *
 * ## Dos particularidades, a propósito
 *
 * - **Lee un caso real en vez de crear uno.** Solo los casos que pasaron por el
 *   pipeline de IA tienen metafase y cajas, y backend-ml no forma parte de la
 *   suite (su ausencia es el escenario de RN-07). El caso se busca por API; si
 *   no hay ninguno, el test se salta y lo dice.
 * - **No escribe nada.** La petición de recorte se intercepta y se responde
 *   con el cromosoma sin cambios: recortar reclasifica y deja eventos en la
 *   auditoría, que es de solo inserción (RN-05), y una prueba no puede
 *   ensuciar un caso real. Lo que se verifica es exactamente lo que el visor
 *   ENVIARÍA.
 *
 * Las cinco preguntas:
 *   1  getByTestId; el lienzo de Konva es un único <canvas>: dentro se
 *      apunta por coordenadas, con la misma geometría que el producto
 *   2  sin esperas fijas
 *   3  se verifica el bbox enviado, no un texto
 *   4  un comportamiento, empieza navegando
 *   5  no crea caso, por lo explicado arriba, pero tampoco modifica ninguno
 */

const CLINIC_API = process.env.E2E_CLINIC_API || 'http://localhost:8002';

interface Caja { x: number; y: number; w: number; h: number }
interface Cromosoma {
  id: string; predicted_class: string; position_index: number;
  is_active: boolean; bbox: Partial<Caja>;
}

/** Ancho y alto de la metafase, leídos de su cabecera (BMP o PNG). */
function dimensiones(b: Buffer): { w: number; h: number } {
  if (b.subarray(0, 2).toString('latin1') === 'BM') return { w: b.readInt32LE(18), h: Math.abs(b.readInt32LE(22)) };
  if (b[0] === 0x89 && b.subarray(1, 4).toString('latin1') === 'PNG') return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
  throw new Error('metafase en un formato que este test no sabe medir');
}

/** Primer caso no validado con metafase servible y algún cromosoma con caja. */
async function casoConMetafase(request: any, access: string) {
  const cab = { Authorization: `Bearer ${access}` };
  const lista = await (await request.get(`${CLINIC_API}/api/clinic/samples/`, { headers: cab })).json();
  const muestras = Array.isArray(lista) ? lista : lista.results ?? [];
  for (const m of muestras) {
    if (m.status !== 'READY') continue;
    const img = await request.get(`${CLINIC_API}/api/clinic/samples/${m.id}/karyotype/metaphase/`,
      { headers: { ...cab, Accept: 'image/*' } });
    if (!img.ok()) continue;
    const k = await (await request.get(`${CLINIC_API}/api/clinic/samples/${m.id}/karyotype/`, { headers: cab })).json();
    const crom = (k.chromosomes as Cromosoma[]).find((c) => c.is_active && (c.bbox?.w ?? 0) > 0);
    if (crom) return { muestra: m.id as string, crom, imagen: dimensiones(await img.body()) };
  }
  return null;
}


test('el recorte dibujado sobre un cromosoma cae sobre ESE cromosoma en la metafase', async ({ page, request }) => {
  const tokens = await pedirToken(request, SUPERVISOR);
  const caso = await casoConMetafase(request, tokens.access);
  test.skip(!caso, 'no hay ningún caso READY con metafase real y cajas en esta base');
  const { muestra, crom, imagen } = caso!;
  const original = crom.bbox as Caja;

  let enviado: Caja | null = null;
  await page.route('**/chromosomes/*/recrop/', async (route) => {
    enviado = (route.request().postDataJSON() as { bbox: Caja }).bbox;
    await route.fulfill({ status: 200, json: crom });
  });

  await sembrarSesion(page, tokens);
  await page.goto(`/clinic/samples/${muestra}/karyotype`);
  const lienzo = page.getByTestId('karyotype-viewer').locator('canvas').first();
  await expect(lienzo).toBeVisible();
  // La posición del lienzo se mide JUSTO antes de cada uso: pulsar un botón del
  // panel lateral, que es largo, desplaza la página. La primera versión de este
  // test medía una sola vez y arrastraba sobre una zona vacía — el visor no
  // llegaba a enviar nada y el rojo no decía nada del defecto.
  const enPantalla = async (x: number, y: number) => {
    await lienzo.scrollIntoViewIfNeeded();
    const caja = (await lienzo.boundingBox())!;
    const escala = caja.width / STAGE_WIDTH;
    return { x: caja.x + x * escala, y: caja.y + y * escala };
  };

  // El cuerpo del cromosoma ocupa (2, 10)–(24, 110) dentro de su grupo.
  const pos = chromosomePosition(crom);
  const centro = await enPantalla(pos.x + 13, pos.y + 60);
  await page.mouse.click(centro.x, centro.y);
  await page.getByTestId('action-crop').click();

  // Se dibuja sobre el recuadro discontinuo del panel, con la misma geometría
  // que usa el producto para pintarlo.
  const panel = page.getByTestId('metafase-panel').locator('canvas').first();
  await expect(panel).toBeVisible();
  await panel.scrollIntoViewIfNeeded();
  const marco = (await panel.boundingBox())!;
  const region = regionDeRecorte(original, imagen);
  const actual = aPanel(original, region, escalaPanel(region));
  const desde = { x: marco.x + actual.x, y: marco.y + actual.y };
  const hasta = { x: marco.x + actual.x + actual.w, y: marco.y + actual.y + actual.h };
  await page.mouse.move(desde.x, desde.y);
  await page.mouse.down();
  await page.mouse.move(hasta.x, hasta.y, { steps: 6 });
  // Para la documentación (T5): el panel con el recorte en curso, antes de soltar.
  // La barra de navegación es `sticky` y, al llevar el panel arriba para la
  // captura, tapaba su título: solo durante la captura deja de ser fija.
  if (process.env.E2E_CAPTURA) {
    await page.getByTestId('metafase-panel').screenshot({
      path: process.env.E2E_CAPTURA,
      style: '.navbar { position: static !important; }',
    });
  }
  await page.mouse.up();

  await expect.poll(() => enviado, { message: 'el visor no llegó a enviar el recorte' }).not.toBeNull();
  // Un píxel de pantalla del panel son menos de dos de la metafase: tolerancia 2.
  const mensaje = `recorte enviado ${JSON.stringify(enviado)} frente a la caja del cromosoma ${JSON.stringify(original)}`;
  for (const k of ['x', 'y', 'w', 'h'] as const) {
    expect(Math.abs(enviado![k] - original[k]), mensaje).toBeLessThanOrEqual(2);
  }
});
