import test from '@playwright/test';
import { pedirToken, sembrarSesion, chnUnico } from '../fixtures/sesion';
import { ANALISTA, SUPERVISOR } from '../fixtures/credenciales';

test('E2E-06: El ISCN es de solo lectura', async ({ page }) => {
  const cred = ANALISTA;
  const tok = await pedirToken(page, cred);
  sembrarSesion(page, tok);

  const chn = chnUnico();
  const id = chn.id;

  await page.goto(`/clinic/samples/${id}`);
  await page.waitForSelector('data-testid="karyo-error"');

  await page.click('data-testid="karyo-error"');
  await page.waitForSelector('data-testid="inbox-forbidden"');

  await page.click('data-testid="inbox-forbidden"');
  await page.waitForSelector('data-testid="inbox-error"');

  await page.click('data-testid="inbox-error"');
  await page.waitForSelector('data-testid="karyo-validated-banner"');

  await expect(page).not.toHaveSelector('data-testid="karyo-validated-banner"');
});
