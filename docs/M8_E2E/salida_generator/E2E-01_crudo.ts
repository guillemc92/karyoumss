import test from '@playwright/test';
import { pedirToken, sembrarSesion, chnUnico } from '../fixtures/sesion';

test('E2E-01: Registro de muestra con metafases (FSD-UC-001)', async ({ page }) => {
  const token = await pedirToken(page, { cred: 'ANALISTA' });
  sembrarSesion(page, token);

  const chn = await chnUnico();
  const url = '/clinic/samples/register';
  const metafases = 3;

  await page.goto(url);
  await page.fill('input[name="chn"]', chn);
  await page.fill('input[name="metafases"]', metafases.toString());
  await page.click('button[type="submit"]');

  await page.waitForSelector('div[data-testid="karyo-validated-banner"]');

  const bannerValidado = await page.$('div[data-testid="karyo-validated-banner"]');
  const bannerDegradado = await page.$('div[data-testid="karyo-degraded-banner"]');
  const bannerError = await page.$('div[data-testid="karyo-error"]');

  expect(bannerValidado).not.toBeNull();
  expect(bannerDegradado).toBeNull();
  expect(bannerError).toBeNull();

  await page.goto(`/clinic/samples/${chn}/karyotype`);
  await page.waitForSelector('div[data-testid="semaphore-legend"]');

  const legend = await page.$('div[data-testid="semaphore-legend"]');
  const error = await page.$('div[data-testid="karyo-error"]');

  expect(legend).not.toBeNull();
  expect(error).toBeNull();

  await page.goto('/clinic/supervisor');
  await page.waitForSelector('div[data-testid="inbox-forbidden"]');

  const inboxForbidden = await page.$('div[data-testid="inbox-forbidden"]');
  const inboxTotalPending = await page.$('div[data-testid="inbox-total-pending"]');
  const inboxError = await page.$('div[data-testid="inbox-error"]');

  expect(inboxForbidden).not.toBeNull();
  expect(inboxTotalPending).not.toBeNull();
  expect(inboxError).toBeNull();

  await page.goto('/clinic/consultas');
  await page.waitForSelector('div[data-testid="tool-camino"]');

  const camino = await page.$('div[data-testid="tool-camino"]');
  const fuente = await page.$('div[data-testid="tool-fuente"]');

  expect(camino).not.toBeNull();
  expect(fuente).not.toBeNull();
});
