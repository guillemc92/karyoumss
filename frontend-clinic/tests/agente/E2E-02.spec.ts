import test from '@playwright/test';
import { pedirToken, sembrarSesion, chnUnico } from '../fixtures/sesion';
import { ANALISTA, SUPERVISOR } from '../fixtures/credenciales';

test('E2E-02: Semaforizacion del cariotipo (FSD-UC-002)', async ({ page }) => {
  const cred = ANALISTA;
  const tok = await pedirToken(page, cred);
  sembrarSesion(page, tok);

  const chn = chnUnico();
  const id = chn.id;

  await page.goto(`/clinic/samples/${id}/karyotype`);

  await expect(page.locator('data-testid="semaphore-legend"')).toHaveStyle('color: orange');

  await expect(page.locator('data-testid="karyo-error"')).not.toBeVisible();

  await expect(page.locator('data-testid="karyo-degraded-banner"')).not.toBeVisible();

  await expect(page.locator('data-testid="karyo-validated-banner"')).not.toBeVisible();

  await expect(page.locator('data-testid="inbox-forbidden"')).not.toBeVisible();

  await expect(page.locator('data-testid="inbox-total-pending"')).toHaveText('0');

  await expect(page.locator('data-testid="inbox-error"')).not.toBeVisible();

  await expect(page.locator('data-testid="tool-camino"')).toHaveText('CarioTipo');

  await expect(page.locator('data-testid="tool-fuente"')).toHaveText('Procedencia');

  await expect(page.locator('data-testid="karyo-validated-banner"')).toHaveStyle('background-color: green');

  await expect(page.locator('data-testid="karyo-validated-banner"')).toHaveText('CarioTipo validado');
});
