import test from '@playwright/test';
import { pedirToken, sembrarSesion, chnUnico } from '../fixtures/sesion';

test('Registro con campo obligatorio vacio (FSD-UC-001)', async ({ page }) => {
  const cred = { rol: 'ANALISTA', credenciales: 'credenciales' };
  const tok = await pedirToken(page, cred);
  sembrarSesion(page, tok);

  const chn = chnUnico();
  const url = '/clinic/samples/register';
  const respuesta = await page.goto(url);

  await expect(respuesta).toHaveText('Registro de paciente');

  await page.fill('input[name="chn"]', '');
  await page.click('button[type="submit"]');

  await expect(page).toHaveText('El campo CHN es obligatorio');
  await expect(page.locator('karyo-error')).toHaveText('El campo CHN es obligatorio');
});
