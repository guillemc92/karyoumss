import test from '@playwright/test';
import { pedirToken, sembrarSesion, chnUnico } from '../fixtures/sesion';

test('MUE-07: Edicion de muestra (FSD-UC-001) - Cambios guardados se ven en el listado', async ({ page }) => {
  const token = await pedirToken(page, { cred: 'ANALISTA' });
  sembrarSesion(page, token);

  const chn = chnUnico();
  const id = chn.id;

  await page.goto(`/clinic/samples/${id}/edit`);

  await page.fill('input[name="patient"]', chn.patient);
  await page.fill('input[name="sample"]', chn.sample);
  await page.click('button[type="submit"]');

  await page.waitForChange();

  await page.goto('/clinic/samples');
  await page.waitForSelector('table');

  const rows = await page.$$( 'tr' );
  const expectedRow = rows[0];
  const actualRow = rows[1];

  await expect(actualRow).toHaveText('Patient: ' + chn.patient);
  await expect(actualRow).toHaveText('Sample: ' + chn.sample);
});
