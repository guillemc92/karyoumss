import { expect } from '@playwright/test';
import { ANALISTA, SUPERVISOR, chnUnico, pedirToken, sembrarSesion } from './sesion';

/**
 * Una muestra PROPIA del test, con una metafase real y segmentada por el
 * backend-ml de verdad (DD-KARYO-007).
 *
 * ## Por qué no se usa un caso que ya existe
 *
 * Las ediciones de la metafase emiten eventos en una auditoría que solo admite
 * inserciones (RN-05): lo que un test haga en un caso ya no se puede quitar.
 * Así que se lee (solo lectura) la metafase real de un caso de la base y se
 * registra con ella una muestra nueva, con CHN único, desde el formulario.
 */

export const CLINIC_API = process.env.E2E_CLINIC_API || 'http://localhost:8002';

export type Cab = Record<string, string>;
export interface Cromosoma {
  id: string;
  predicted_class: string;
  is_active: boolean;
  bbox: { x: number; y: number; w: number; h: number };
  contour?: number[][] | null;
}

export async function json(request: any, url: string, cab: Cab) {
  const r = await request.get(`${CLINIC_API}/api/clinic${url}`, { headers: cab });
  return r.ok() ? r.json() : null;
}

/** Una metafase real de la base, leída sin tocar nada. */
export async function metafaseReal(request: any): Promise<Buffer | null> {
  const sup = await pedirToken(request, SUPERVISOR);
  const cab = { Authorization: `Bearer ${sup.access}` };
  const lista = await json(request, '/samples/', cab);
  for (const m of (Array.isArray(lista) ? lista : lista?.results ?? [])) {
    if (m.status !== 'READY') continue;
    const r = await request.get(`${CLINIC_API}/api/clinic/samples/${m.id}/karyotype/metaphase/`,
      { headers: { ...cab, Accept: 'image/*' } });
    if (r.ok()) return Buffer.from(await r.body());
  }
  return null;
}

/** Registra la muestra como analista y espera a que la IA real la segmente. */
export async function registrarMuestraPropia(page: any, request: any, imagen: Buffer) {
  const sesion = await pedirToken(request, ANALISTA);
  const cab = { Authorization: `Bearer ${sesion.access}` };
  const chn = chnUnico();
  await sembrarSesion(page, sesion);
  await page.goto('/clinic/samples/register');
  await page.getByLabel(/CHN \(Historia Clínica\)/).fill(chn);
  await page.getByLabel(/Nombre completo/).fill('Paciente E2E');
  await page.getByLabel(/Fecha de recolección/).fill('2026-10-23');
  await page.getByTestId('metafase-file-input').setInputFiles(
    [0, 1, 2].map((i) => ({ name: `metafase_${i}.bmp`, mimeType: 'image/bmp', buffer: imagen })),
  );
  await page.getByRole('button', { name: /Registrar y analizar con IA/ }).click();

  let id = '';
  await expect(async () => {
    const lista = await json(request, '/samples/', cab);
    const m = (Array.isArray(lista) ? lista : lista?.results ?? []).find((s: any) => s.chn_code === chn);
    expect(m?.status, `la muestra ${chn} todavía no tiene cariotipo`).toBe('READY');
    id = m.id;
  }).toPass({ timeout: 150_000, intervals: [3_000] });
  return { id, cab };
}

/** Ancho y alto de la metafase, decodificada por el navegador. */
export async function dimensionesMetafase(page: any, id: string): Promise<{ w: number; h: number }> {
  return page.evaluate(async (url: string) => {
    const r = await fetch(url, {
      headers: { Authorization: `Bearer ${localStorage.getItem('biomed.auth.access') ?? ''}`, Accept: 'image/*' },
    });
    const bmp = await createImageBitmap(await r.blob());
    return { w: bmp.width, h: bmp.height };
  }, `/api/clinic/samples/${id}/karyotype/metaphase/`);
}
