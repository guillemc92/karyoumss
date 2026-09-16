import test from '@playwright/test';
import { pedirToken, sembrarSesion, chnUnico, ANALISTA, SUPERVISOR } from '../fixtures/sesion';

test('Segregacion: el analista no entra a la bandeja del supervisor (RN-06)')({
  name: 'Segregacion: el analista no entra a la bandeja del supervisor (RN-06)',
  url: '/clinic/supervisor',
  expect: {
    count: 0,
    text: 'Acceso restringido',
  },
  async ({ page, request }) {
    const token = await pedirToken(request, ANALISTA.cred);
    sembrarSesion(page, token);

    const chn = chnUnico();
    await page.goto(`/clinic/supervisor?chn=${chn}`);

    await page.locator('data-testid="inbox-forbidden"').expect('text', 'Acceso restringido');
    await page.locator('data-testid="inbox-total-pending"').expect('count', 0);
    await page.locator('data-testid="inbox-error"').expect('text', 'Error al cargar');
  },
});
