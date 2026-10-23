import { expect, test } from '@playwright/test';
import { SUPERVISOR, pedirToken, sembrarSesion } from '../fixtures/sesion';

/**
 * DD-KARYO-007 T2 — La metafase como lienzo: contornos reales y selección
 * compartida con el cariograma, en Chromium y contra el stack real.
 *
 * Lo que el mock de react-konva no puede probar y esto sí:
 * - que Konva detecta el clic DENTRO de la silueta (el relleno tenue es lo que
 *   lo hace posible; sin relleno solo respondería el borde);
 * - que la escala del Stage pone la silueta encima del cromosoma de la imagen;
 * - que un caso antiguo, al abrirse, queda con sus contornos guardados.
 *
 * Escritura: abrir el caso hace que el producto guarde los contornos que
 * faltaban (`POST /karyotype/contours/`). Es lo que hace la pantalla para
 * cualquiera; no emite evento de auditoría ni cambia ninguna decisión clínica.
 * El test no crea casos ni pulsa ninguna acción clínica (RN-05).
 *
 * Capturas para la documentación: `E2E_CAPTURAS=<carpeta>`.
 */

const CLINIC_API = process.env.E2E_CLINIC_API || 'http://localhost:8002';
const CAPTURAS = process.env.E2E_CAPTURAS;

interface Cromosoma {
  id: string; predicted_class: string; is_active: boolean;
  bbox: { x?: number; y?: number; w?: number; h?: number } | null;
  contour?: number[][] | null;
}
type Cab = Record<string, string>;

async function cromosomas(request: any, cab: Cab, id: string): Promise<Cromosoma[]> {
  const r = await request.get(`${CLINIC_API}/api/clinic/samples/${id}/karyotype/`, { headers: cab });
  if (!r.ok()) return [];
  return ((await r.json()).chromosomes as Cromosoma[]).filter((c) => c.is_active);
}

function dentro([px, py]: number[], pol: number[][]): boolean {
  let si = false;
  for (let i = 0, j = pol.length - 1; i < pol.length; j = i++) {
    const [xi, yi] = pol[i];
    const [xj, yj] = pol[j];
    if ((yi > py) !== (yj > py) && px < ((xj - xi) * (py - yi)) / (yj - yi) + xi) si = !si;
  }
  return si;
}

/** Un punto claramente dentro de la silueta: el centro de su caja, si cae dentro. */
function puntoInterior(c: Cromosoma): number[] | null {
  if (!c.contour || c.contour.length < 3 || !c.bbox) return null;
  const p = [(c.bbox.x ?? 0) + (c.bbox.w ?? 0) / 2, (c.bbox.y ?? 0) + (c.bbox.h ?? 0) / 2];
  return dentro(p, c.contour) ? p : null;
}

test('la metafase muestra las siluetas y seleccionar en ella selecciona en el cariograma', async ({ page, request }) => {
  const tokens = await pedirToken(request, SUPERVISOR);
  const cab = { Authorization: `Bearer ${tokens.access}` };

  const lista = await (await request.get(`${CLINIC_API}/api/clinic/samples/`, { headers: cab })).json();
  const ready = (Array.isArray(lista) ? lista : lista.results ?? [])
    .filter((m: any) => m.status === 'READY').map((m: any) => m.id as string);
  let id: string | null = null;
  for (const candidato of ready) {
    const img = await request.get(`${CLINIC_API}/api/clinic/samples/${candidato}/karyotype/metaphase/`,
      { headers: { ...cab, Accept: 'image/*' } });
    if (img.ok() && (await cromosomas(request, cab, candidato)).length > 0) { id = candidato; break; }
  }
  test.skip(!id, 'no hay ningún caso READY con metafase real en esta base');

  await sembrarSesion(page, tokens);
  await page.goto(`/clinic/samples/${id}/karyotype`);
  const editor = page.getByTestId('metafase-editor');
  const lienzo = editor.locator('canvas').first();
  await expect(lienzo).toBeVisible();

  // Al abrirlo, el caso queda con las siluetas: las de T1 o las completadas ahora.
  let crom: Cromosoma[] = [];
  await expect
    .poll(async () => {
      crom = await cromosomas(request, cab, id!);
      return crom.filter((c) => Array.isArray(c.contour) && c.contour.length >= 3).length / crom.length;
    }, { message: 'menos del 90 % de los cromosomas tienen silueta' })
    .toBeGreaterThanOrEqual(0.9);
  await expect(page.getByTestId('metafase-cuenta')).toHaveText(`${crom.length} objeto(s)`);

  // Píxeles de la metafase → píxeles de pantalla: el lienzo es la imagen escalada.
  const anchoImagen = await page.evaluate(async (url) => {
    const r = await fetch(url, { headers: { Authorization: `Bearer ${localStorage.getItem('biomed.auth.access') ?? ''}`, Accept: 'image/*' } });
    return r.ok ? (await createImageBitmap(await r.blob())).width : 0;
  }, `/api/clinic/samples/${id}/karyotype/metaphase/`);
  const caja = (await lienzo.boundingBox())!;
  const escala = anchoImagen > 0 ? caja.width / anchoImagen : 0;
  test.skip(escala === 0, 'no se pudo leer el tamaño de la metafase desde el navegador');

  // Control: antes de pulsar no hay nada seleccionado.
  await expect(page.getByTestId('chromosome-props-empty')).toBeVisible();

  const objetivo = crom.find((c) => puntoInterior(c));
  expect(objetivo, 'ningún cromosoma tiene el centro de su caja dentro de la silueta').toBeTruthy();
  const [px, py] = puntoInterior(objetivo!)!;
  await page.mouse.click(caja.x + px * escala, caja.y + py * escala);

  await expect(page.getByTestId('chromosome-props')).toBeVisible();
  await expect(page.getByTestId('props-class')).toContainText(objetivo!.predicted_class);

  if (CAPTURAS) {
    await editor.screenshot({ path: `${CAPTURAS}/metafase-editor.png`, style: '.navbar { position: static !important; }' });
  }
});
