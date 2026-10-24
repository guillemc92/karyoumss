import test from '@playwright/test';
import { pedirToken, sembrarSesion, chnUnico } from '../fixtures/sesion';
import { ANALISTA, SUPERVISOR } from '../fixtures/credenciales';

test('CON-05: Pagina de modo degradado (FSD-UC-007)', async ({ page }) => {
  const cred = ANALISTA;
  const tok = await pedirToken(page, cred);
  sembrarSesion(page, tok);

  const chn = chnUnico();
  const url = '/clinic/degraded';
  await page.goto(url);

  await page.locator('data-testid="karyo-degraded-banner"').expect('display' => 'block');
  await page.locator('data-testid="karyo-error"').expect('display' => 'none');

  await page.locator('data-testid="inbox-forbidden"').expect('display' => 'block');
  await page.locator('data-testid="inbox-total-pending"').expect('value', '0');
  await page.locator('data-testid="inbox-error"').expect('display' => 'none');

  await page.locator('data-testid="tool-camino"').click();
  await page.locator('data-testid="tool-fuente"').expect('display' => 'block');

  await page.locator('data-testid="karyo-validated-banner"').expect('display' => 'block');
});
