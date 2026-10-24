import test from '@playwright/test';
import { pedirToken, sembrarSesion, chnUnico } from '../fixtures/sesion';

test('E2E-10: Sin token en localStorage la app no muestra datos de pacientes', async ({ page }) => {
  const cred = { ANALISTA: 'analista', SUPERVISOR: 'supervisor' };
  const tok = await sembrarSesion(page, await pedirToken(chnUnico(), cred));
  await page.goto('/clinic/samples');

  await page.locator('data-testid="semaphore-legend"').expect('text', 'Legend').toBeVisible();
  await page.locator('data-testid="karyo-error"').expect('text', 'Error').toBeVisible();
  await page.locator('data-testid="karyo-degraded-banner"').expect('text', 'Degraded').toBeVisible();
  await page.locator('data-testid="karyo-validated-banner"').expect('text', 'Validated').toBeVisible();

  await page.goto('/clinic/supervisor');
  await page.locator('data-testid="inbox-forbidden"').expect('text', 'Forbidden').toBeVisible();
  await page.locator('data-testid="inbox-total-pending"').expect('text', 'Pending').toBeVisible();
  await page.locator('data-testid="inbox-error"').expect('text', 'Error').toBeVisible();

  await page.goto('/clinic/consultas');
  await page.locator('data-testid="tool-camino"').expect('text', 'Camino').toBeVisible();
  await page.locator('data-testid="tool-fuente"').expect('text', 'Fuente').toBeVisible();

  await page.locator('data-testid="karyotype"').click();
  await page.locator('data-testid="karyo-error"').expect('text', 'Error').toBeVisible();

  await page.locator('data-testid="inbox-forbidden"').expect('text', 'Forbidden').toBeVisible();
  await page.locator('data-testid="inbox-total-pending"').expect('text', 'Pending').toBeVisible();
  await page.locator('data-testid="inbox-error"').expect('text', 'Error').toBeVisible();

  await page.locator('data-testid="karyotype"').click();
  await page.locator('data-testid="karyo-error"').expect('text', 'Error').toBeVisible();
});
