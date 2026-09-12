import test from '@playwright/test';
import { pedirToken, sembrarSesion, chnUnico } from '../fixtures/sesion';
import { ANALISTA, SUPERVISOR } from '../fixtures/credenciales';

test('E2E-07: Modo degradado (FSD-UC-007)', async ({ page }) => {
  const cred = ANALISTA;
  const tok = await pedirToken(page, cred);
  sembrarSesion(page, tok);

  const chn = chnUnico();
  const id = chn.id;

  await page.goto(`/clinic/samples/${id}`);
  await page.waitForSelector('data-testid="karyo-error"');

  await page.click('data-testid="karyo-error"');
  await page.waitForSelector('data-testid="karyo-degraded-banner"');

  await page.click('data-testid="karyo-degraded-banner"');
  await page.waitForSelector('data-testid="inbox-forbidden"');

  await page.click('data-testid="inbox-forbidden"');
  await page.waitForSelector('data-testid="inbox-total-pending"');

  await page.click('data-testid="inbox-total-pending"');
  await page.waitForSelector('data-testid="tool-camino"');

  await page.click('data-testid="tool-camino"');
  await page.waitForSelector('data-testid="tool-fuente"');

  await page.click('data-testid="tool-fuente"');
  await page.waitForSelector('data-testid="karyo-validated-banner"');

  expect(await page.$('data-testid="karyo-validated-banner"')).not.toBeNull();
});
