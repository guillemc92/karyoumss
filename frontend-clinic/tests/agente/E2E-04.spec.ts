import { test, expect, page } from '@playwright/test';
import { pedirToken, sembrarSesion } from '../fixtures/sesion';

test('E2E-04: Segregacion de funciones: analista ajeno al caso', async ({ page }) => {
  const cred = { rol: 'analista', credencial: 'analista' };
  const tok = await pedirToken(page, cred);
  sembrarSesion(page, tok);

  const id = chnUnico();
  const url = `/clinic/samples/${id}/karyotype`;

  await page.goto(url);

  await expect(page.locator('data-testid="karyo-error"')).expect('text', 'Error al cargar');

  await expect(page.locator('data-testid="karyo-degraded-banner"')).expect('display', 'none');

  await expect(page.locator('data-testid="karyo-validated-banner"')).expect('display', 'none');

  await expect(page.locator('data-testid="inbox-forbidden"')).expect('text', 'Acceso denegado');

  await expect(page.locator('data-testid="inbox-total-pending"')).expect('text', '0');

  await expect(page.locator('data-testid="inbox-error"')).expect('text', 'Error al cargar');

  await expect(page.locator('data-testid="tool-camino"')).expect('display', 'none');

  await expect(page.locator('data-testid="tool-fuente"')).expect('display', 'none');
});
