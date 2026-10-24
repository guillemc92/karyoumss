import test from '@playwright/test';
import { pedirToken, sembrarSesion, chnUnico } from '../fixtures/sesion';

test('MUE-01: Registro de muestra con metafases (FSD-UC-001)', async ({ page }) => {
  const cred = { rol: 'ANALISTA', credenciales: 'credenciales' };
  const tok = await pedirToken(page, cred);
  sembrarSesion(page, tok);

  const chn = await chnUnico();
  const url = '/clinic/samples/register';
  const expectedUrl = '/clinic/samples/validado';

  await page.goto(url);
  await page.fill('input[name="chn"]', chn);
  await page.fill('input[name="nombre"]', 'nombre');
  await page.fill('input[name="apellido"]', 'apellido');
  await page.click('button[type="submit"]');

  await page.waitForSelector('data-testid="karyo-validated-banner", visible');
  expect(await page.$('data-testid="karyo-validated-banner").textContent()').includes('Validado'));

  await page.goto(expectedUrl);
  await page.waitForSelector('data-testid="semaphore-legend", visible');
  expect(await page.$('data-testid="semaphore-legend").textContent()').includes('Validado');

  await page.goto('/clinic/supervisor');
  await page.waitForSelector('data-testid="inbox-forbidden", visible');
  expect(await page.$('data-testid="inbox-forbidden").textContent()').includes('Acceso denegado');

  await page.goto('/clinic/consultas');
  await page.waitForSelector('data-testid="tool-camino", visible');
  expect(await page.$('data-testid="tool-camino").textContent()').includes('Validado');

  await page.goto('/clinic/samples/:id/karyotype');
  await page.waitForSelector('data-testid="karyo-error", visible');
  expect(await page.$('data-testid="karyo-error").textContent()').includes('Error al cargar');
});
