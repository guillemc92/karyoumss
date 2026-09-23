import { expect, test } from '@playwright/test';
import { ANALISTA, pedirToken, sembrarSesion } from '../fixtures/sesion';

/**
 * CON-04 — Una consulta ajena al dominio se declara «Fuera de alcance».
 *
 * Caso AÑADIDO por la auditoría del plan de la sección «consultas»: el
 * Planner propuso tres casos y el único «límite» inventaba un flujo («acceder
 * a datos sensibles») que la pantalla no tiene. El límite real es este: el
 * enrutador tiene tres salidas (sin IA / el modelo eligió / fuera de alcance)
 * y la tercera es la que protege al usuario de una respuesta inventada.
 *
 * ## Por qué este caso sí es E2E y la semaforización no
 *
 * El camino pasa por el modelo (llama3.2:3b decide si hay herramienta), así
 * que antes de aceptarlo se midió: tres preguntas ajenas al dominio, tres
 * veces cada una, **9 de 9 SIN_MATCH** contra el backend real. Lo que se
 * afirma es el camino, no la redacción: si el modelo cambiara de opinión el
 * test se pondría rojo y eso sería un hallazgo, no ruido.
 *
 * ## Lo que hizo el Generator y por qué se reescribió
 *
 * `CON-04_crudo.ts`: importa `fixtures/credenciales` (no existe), rellena
 * `input[name="query"]` (CSS, y el campo no se llama así), pulsa
 * `button[type="submit"]`, y tras comprobar `tool-camino` exige
 * `karyo-error`, `inbox-forbidden` e `inbox-error` — anclas de otras tres
 * pantallas — en la página de consultas. `expect` ni siquiera está importado.
 *
 * Las cinco preguntas:
 *   1  getByLabel / getByRole / getByTestId
 *   2  sin esperas fijas; el expect del camino lleva margen porque hay un
 *      modelo detrás, pero sigue siendo una espera de condición
 *   3  se afirma el camino que la interfaz promete, no el texto del modelo
 *   4  un comportamiento; empieza con page.goto
 *   5  la pregunta es del test y no toca datos de ninguna muestra
 */
// Este test espera a un modelo de 3B corriendo en la misma maquina, y el
// presupuesto global de 60 s de playwright.config se le queda corto cuando la
// suite va cargada: medido 41 s en solitario, 50,5 s dentro de la suite y un
// timeout a 60 s el 23/09. No es intermitencia tapada, es el coste real de la
// dependencia; se declara aqui en vez de subir el timeout de TODA la suite.
test.setTimeout(150_000);

test('una consulta ajena al dominio se declara fuera de alcance y no muestra datos de muestras', async ({
  page,
  request,
}) => {
  await sembrarSesion(page, await pedirToken(request, ANALISTA));
  await page.goto('/clinic/consultas');

  await page
    .getByLabel('Consulta en lenguaje natural')
    .fill('¿cuál es la capital de Francia?');
  await page.getByRole('button', { name: /consultar|enviar|buscar/i }).first().click();

  // ORÁCULO: el enrutador declara que no hay herramienta para eso. El camino
  // pasa por el modelo local, por eso el margen es mayor que en el resto de
  // la suite (medido: hasta ~20 s en frío).
  await expect(page.getByTestId('tool-camino')).toHaveText('Fuera de alcance', {
    timeout: 45_000,
  });

  // Y no se pinta ninguna fila de datos: «no sé» no viene con tabla.
  await expect(page.getByTestId('tool-fila')).toHaveCount(0);
});
