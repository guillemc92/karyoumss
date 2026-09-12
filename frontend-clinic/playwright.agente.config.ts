import { defineConfig } from '@playwright/test';
import base from './playwright.config';

/**
 * Corrida de los tests GENERADOS por el agente, tal como salieron.
 *
 *   npx playwright test --config playwright.agente.config.ts
 *
 * Es la captura de «rojo controlado» que pide la consigna. Se separa de la
 * suite principal porque 5 de los 9 no llegan a cargar —importan
 * `../fixtures/credenciales`, que no existe— y un fichero que no carga aborta
 * la corrida completa de Playwright antes de ejecutar nada.
 *
 * Nada de lo que hay en `tests/agente` se ha tocado: es la evidencia de la
 * auditoría (specs/AUDITORIA_E2E.md). El reporte va a una carpeta aparte para
 * no pisar el de la suite verde.
 */
export default defineConfig({
  ...base,
  testMatch: /tests[\\/]agente[\\/].*\.spec\.ts$/,
  reporter: [
    ['list'],
    ['html', { open: 'never', outputFolder: 'playwright-report-agente' }],
  ],
  outputDir: 'test-results-agente',
});
