import { expect, test } from '@playwright/test';
import { type Cromosoma, json, metafaseReal, registrarMuestraPropia } from '../fixtures/muestraPropia';
import { STAGE_WIDTH, posicionesCariograma } from '../../src/clinic/lib/karyoLayout';
import { ejeDe, giroParaEnderezar } from '../../src/clinic/lib/ejeCromosoma';

/**
 * DD-KARYO-008 T2 — En el cariograma, un cromosoma que en la metafase está en
 * diagonal se ve DE PIE, en Chromium y contra el stack real, sobre una muestra
 * PROPIA.
 *
 * Se comprueba en los PÍXELES, no en un atributo: el eje de los píxeles oscuros
 * del hueco del cromosoma tiene que quedar casi vertical. Hasta T2 quedaba con
 * la misma inclinación que en la metafase; este test lo reproducía (fallaba)
 * antes del cambio.
 *
 * Solo se mira un cromosoma que esté SOLO en su par: con copias, el hueco
 * contiene a varios y sus píxeles se mezclarían.
 */

/** Inclinación respecto a la vertical, en grados, de los píxeles oscuros y grises de una región. */
async function inclinacionEnCariograma(page: any, pos: { x: number; y: number }): Promise<{ grados: number; oscuros: number }> {
  await page.getByTestId('karyotype-viewer').scrollIntoViewIfNeeded();
  return page.evaluate(({ x, y, ancho }: { x: number; y: number; ancho: number }) => {
    const lienzo = document.querySelector('[data-testid="karyotype-viewer"] canvas') as HTMLCanvasElement;
    const k = lienzo.width / ancho;
    // El cuerpo del hueco (CUERPO = 2, 10, 22 × 100), con 2 px de margen.
    const x0 = Math.round((x + 0) * k);
    const y0 = Math.round((y + 8) * k);
    const w = Math.round(26 * k);
    const h = Math.round(104 * k);
    const d = lienzo.getContext('2d')!.getImageData(x0, y0, w, h).data;
    let n = 0; let sx = 0; let sy = 0; let sxx = 0; let syy = 0; let sxy = 0;
    for (let j = 0; j < h; j++) {
      for (let i = 0; i < w; i++) {
        const o = (j * w + i) * 4;
        const [r, g, b, alfa] = [d[o], d[o + 1], d[o + 2], d[o + 3]];
        // Lo que Konva no pinta es TRANSPARENTE y se lee (0, 0, 0, 0): gris y
        // negro. Sin exigir opacidad, el medidor contaba el hueco vacío, que es
        // un rectángulo vertical, y daba «de pie» antes y después del cambio.
        if (alfa < 200) continue;
        // Gris y oscuro: el cromosoma. El marco del semáforo es de color y no cuenta.
        const gris = Math.abs(r - g) < 25 && Math.abs(g - b) < 25;
        if (!gris || (r + g + b) / 3 > 150) continue;
        n++; sx += i; sy += j; sxx += i * i; syy += j * j; sxy += i * j;
      }
    }
    if (n < 30) return { grados: Number.NaN, oscuros: n };
    const mx = sx / n; const my = sy / n;
    const cxx = sxx / n - mx * mx; const cyy = syy / n - my * my; const cxy = sxy / n - mx * my;
    const theta = 0.5 * Math.atan2(2 * cxy, cxx - cyy); // eje mayor respecto a x
    const a = ((theta * 180) / Math.PI % 180 + 180) % 180;
    return { grados: Math.abs(a - 90), oscuros: n };
  }, { x: pos.x, y: pos.y, ancho: STAGE_WIDTH });
}

test('un cromosoma en diagonal se ve de pie en el cariograma', async ({ page, request }) => {
  test.setTimeout(240_000);
  const imagen = await metafaseReal(request);
  test.skip(!imagen, 'no hay ningún caso READY con metafase real en esta base');
  const { id, cab } = await registrarMuestraPropia(page, request, imagen!);
  const cromosomas: (Cromosoma & { position_index: number; order: number })[] =
    (await json(request, `/samples/${id}/karyotype/`, cab)).chromosomes.filter((c: Cromosoma) => c.is_active);

  const porClase = new Map<string, number>();
  for (const c of cromosomas) porClase.set(c.predicted_class, (porClase.get(c.predicted_class) ?? 0) + 1);
  // Solo en su par y claramente en diagonal (entre 25° y 65° de la vertical).
  const candidato = cromosomas.find((c) => {
    const g = giroParaEnderezar(ejeDe(c.contour));
    return porClase.get(c.predicted_class) === 1 && g !== null && Math.abs(g) >= 25 && Math.abs(g) <= 65;
  });
  test.skip(!candidato, 'la segmentación no dejó ningún cromosoma en diagonal solo en su par');
  const inclinadoEnMetafase = Math.abs(giroParaEnderezar(ejeDe(candidato!.contour))!);

  await page.goto(`/clinic/samples/${id}/karyotype`);
  await expect(page.getByTestId('karyotype-viewer').locator('canvas').first()).toBeVisible();
  const pos = posicionesCariograma(cromosomas).get(candidato!.id)!;

  // La metafase llega aparte: se espera a que el hueco tenga el cromosoma pintado.
  let medida = { grados: Number.NaN, oscuros: 0 };
  await expect.poll(async () => {
    medida = await inclinacionEnCariograma(page, pos);
    return medida.oscuros;
  }, { timeout: 30_000 }).toBeGreaterThanOrEqual(30);

  if (process.env.E2E_CAPTURAS) {
    await page.getByTestId('karyotype-viewer').screenshot({ path: `${process.env.E2E_CAPTURAS}/cariograma-enderezado.png` });
  }
  console.log(`[enderezado] clase ${candidato!.predicted_class}, bbox ${JSON.stringify(candidato!.bbox)}, `
    + `${inclinadoEnMetafase.toFixed(1)}° en la metafase, ${medida.grados.toFixed(1)}° en el cariograma, ${medida.oscuros} px oscuros`);
  // En la metafase está a `inclinadoEnMetafase` grados; en el cariograma, casi vertical.
  expect(medida.grados, `inclinado ${inclinadoEnMetafase.toFixed(0)}° en la metafase`).toBeLessThan(12);
});
