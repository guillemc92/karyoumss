import test from '@playwright/test';
import { pedirToken, sembrarSesion, chnUnico } from '../fixtures/sesion';
import { ANALISTA, SUPERVISOR } from '../fixtures/credenciales';

test('El supervisor ve cualquier caso (FSD-UC-004)', async ({ page }) => {
  const cred = SUPERVISOR;
  const tok = await pedirToken(page, cred);
  sembrarSesion(page, tok);

  const chn = chnUnico();
  const id = chn.id;

  await page.goto(`/clinic/samples/${id}/karyotype`);

  await page.locator('data-testid="semaphore-legend"').expect('text', 'Cariotipo');
  await page.locator('data-testid="karyo-error"').expect('text', 'Error al cargar');
  await page.locator('data-testid="karyo-degraded-banner"').expect('text', 'Banner de modo degradado');
  await page.locator('data-testid="karyo-validated-banner"').expect('text', 'Banner de caso validado');

  await page.goto(`/clinic/supervisor`);

  await page.locator('data-testid="inbox-forbidden"').expect('text', 'Acceso denegado');
  await page.locator('data-testid="inbox-total-pending"').expect('text', '0');
  await page.locator('data-testid="inbox-error"').expect('text', 'Error');

  await page.goto(`/clinic/consultas`);

  await page.locator('data-testid="tool-camino"').expect('text', 'Camino');
  await page.locator('data-testid="tool-fuente"').expect('text', 'Fuente');

  await expect(page.locator('data-testid="inbox-total-pending"')).expect('text', '1');
});
