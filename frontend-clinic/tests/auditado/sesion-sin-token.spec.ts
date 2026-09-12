import { expect, test } from '@playwright/test';

/**
 * E2E-10 — Sin token no se ven datos clínicos.
 *
 * Caso AÑADIDO por la auditoría del plan. Es la frontera donde RN-03 (cero
 * fuga de PII) se sostiene o se cae: si la aplicación pintara datos de paciente
 * antes de comprobar la sesión, la regla estaría rota aunque el backend
 * respondiera 401.
 *
 * ## Este test es el contraejemplo del que generó el agente
 *
 * El Generator escribió un `E2E-10` que **se titula «sin token» y lo primero
 * que hace es sembrar un token**. Falla la pregunta 3 en su forma más pura: no
 * verifica lo que promete. Aquí no se siembra nada — ese es justo el punto.
 *
 * Las cinco preguntas:
 *   1  getByText sobre lo que vería una persona
 *   2  sin esperas fijas
 *   3  el título dice «sin token» y el test NO pone token
 *   4  un comportamiento, empieza navegando
 *   5  no necesita datos: la ausencia de sesión es el dato
 */
test('sin token en localStorage la aplicación no muestra datos de pacientes', async ({
  page,
}) => {
  // Deliberadamente NO se llama a sembrarSesion().
  await page.goto('/clinic/samples');

  // ORÁCULO (RN-03 + ADR-0020): sin sesión no puede haber ni un código CHN en
  // pantalla. El CHN es el identificador del caso clínico; verlo sin token
  // sería fuga de dato clínico aunque no apareciera el nombre del paciente.
  await expect(page.getByText(/CHN-\d{4}-\d{2}-\d{2}-\d{4}/)).toHaveCount(0);
});
