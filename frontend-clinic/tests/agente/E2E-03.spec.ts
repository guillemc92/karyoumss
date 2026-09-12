import test from '@playwright/test';
import { pedirToken, sembrarSesion, chnUnico } from '../fixtures/sesion';
import { ANALISTA, SUPERVISOR } from '../fixtures/credenciales';

test('E2E-03 Bloqueo de emision por naranjas sin resolver', async ({ page }) => {
  const cred = ANALISTA;
  const tok = await pedirToken(page, cred);
  sembrarSesion(page, tok);

  const chn = chnUnico();
  const id = chn.id;

  await page.goto(`/clinic/samples/${id}/karyotype`);
  await page.waitForSelector('data-testid="semaphore-legend"');

  await page.click('data-testid="karyo-error"');
  await page.waitForSelector('data-testid="karyo-degraded-banner"');

  await page.click('data-testid="inbox-forbidden"');
  await page.waitForSelector('data-testid="inbox-total-pending"');

  await page.click('data-testid="inbox-error"');
  await page.waitForSelector('data-testid="karyo-validated-banner"');

  await expect(page).toHaveText('Faltan 1 naranja sin resolver');
});
