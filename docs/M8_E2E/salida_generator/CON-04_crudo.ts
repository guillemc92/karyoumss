import test from '@playwright/test';
import { pedirToken, sembrarSesion, chnUnico } from '../fixtures/sesion';
import { ANALISTA, SUPERVISOR } from '../fixtures/credenciales';

test('CON-04: Consulta fuera de alcance (tool calling: SIN_MATCH)', async ({ page }) => {
  const cred = ANALISTA;
  const tok = await sembrarSesion(page, cred.token);
  await sembrarSesion(page, tok);

  const chn = chnUnico();
  await page.goto('/clinic/consultas');

  await page.fill('input[name="query"]', 'pregunta que no corresponde a ninguna herramienta');
  await page.click('button[type="submit"]');

  await page.waitForSelector('div[data-testid="tool-camino"]');

  const camino = await page.locator('div[data-testid="tool-camino"]').textContent();
  expect(camino).toBe('Fuera de alcance');

  await page.waitForSelector('div[data-testid="karyo-error"]');

  const error = await page.locator('div[data-testid="karyo-error"]').textContent();
  expect(error).toBe('Error al cargar datos');

  await page.waitForSelector('div[data-testid="inbox-forbidden"]');

  const aviso = await page.locator('div[data-testid="inbox-forbidden"]').textContent();
  expect(aviso).toBe('Acceso denegado');

  await page.waitForSelector('div[data-testid="inbox-error"]');

  const errorSupervisor = await page.locator('div[data-testid="inbox-error"]').textContent();
  expect(errorSupervisor).toBe('Error al cargar datos');
});
