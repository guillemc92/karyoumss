import test from '@playwright/test';
import { pedirToken, sembrarSesion, chnUnico, ANALISTA, SUPERVISOR } from '../fixtures/sesion';

test('E2E-09: Listado y filtrado de muestras (FSD-UC-001)', async ({ page }) => {
  const token = await pedirToken(page, ANALISTA.cred);
  sembrarSesion(page, token);

  const chn = chnUnico();
  const analista = chnUnico();

  await page.goto('/clinic/samples');
  await page.fill('input[name="search"]', 'Muestra recien creada');
  await page.click('button[type="submit"]');

  await page.waitForSelector('table', { state: 'visible' });
  const listado = await page.locator('table');
  const fila = await listado.locator('tr', { hasText: 'Muestra recien creada' });
  const estado = await fila.locator('td', { hasText: 'En proceso' });
  expect(await estado.textContent()).toBe('En proceso');

  await page.click('button[type="button"]', { hasText: 'Ver karyotipo' });
  await page.goto(`/clinic/samples/${chn.id}/karyotype`);
  await page.waitForSelector('div[data-testid="karyo-validated-banner"]');

  await page.goto('/clinic/supervisor');
  await page.waitForSelector('div[data-testid="inbox-error"]');

  await page.goto('/clinic/consultas');
  await page.waitForSelector('div[data-testid="tool-fuente"]');
});
