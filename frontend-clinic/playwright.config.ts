import { defineConfig, devices } from '@playwright/test';

/**
 * E2E del núcleo clínico (M8).
 *
 * ## Contra el stack REAL, no contra MSW
 *
 * El proyecto tiene dobles de red con MSW y se usan en los tests de componente.
 * Aquí no: con MSW el oráculo sería mi propio mock, así que el test probaría el
 * mock y no el sistema. Y este repositorio ya tiene la cicatriz — el bug de
 * creación de usuarios del 10/07/2026 tuvo como causa raíz `mockServiceWorker.js`
 * ausente más un fallback del proxy de Vite, y la lección que quedó escrita es
 * que **el hueco jsdom↔service worker real es estructural**.
 *
 * El stack se levanta aparte (ver abajo) y va contra los
 * backends de verdad.
 *
 * ## Sin reintentos en local, a propósito
 *
 * `retries: 0` en local: un test que pasa al segundo intento es un test que no
 * sabemos si funciona. Si algo es intermitente queremos verlo, no taparlo.
 */
export default defineConfig({
  testDir: './tests',
  // `tests/` ya la usa Vitest para los tests de componente. Playwright solo
  // mira sus dos subcarpetas: sin esto recoge los `.spec.tsx` de Vitest y
  // falla con «Vitest failed to access its internal state».
  //
  // Por defecto SOLO `tests/auditado`: los generados por el agente viven en
  // `tests/agente` como evidencia, y 5 de los 9 ni cargan (importan un módulo
  // que no existe). Si se incluyeran, Playwright abortaría la corrida entera
  // antes de ejecutar un solo test. Para verlos en rojo controlado:
  //
  //   npx playwright test --config playwright.agente.config.ts
  testMatch: /tests[\\/]auditado[\\/].*\.spec\.ts$/,
  // Un solo worker: los tests tocan la misma base clínica y el aislamiento se
  // consigue con datos propios por test (CHN único), no con paralelismo.
  workers: 1,
  fullyParallel: false,
  retries: 0,
  timeout: 60_000,
  expect: {
    // El pipeline real de IA tarda ~32 s en una metafase; las aserciones que
    // esperan un cariotipo necesitan margen por encima de eso.
    timeout: 15_000,
  },
  reporter: [
    ['list'],
    ['html', { open: 'never', outputFolder: 'playwright-report' }],
  ],
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:5174',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'off',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
  // Sin `webServer`: el stack se levanta aparte y a mano.
  //
  // No es comodidad, es honestidad sobre lo que hace falta. Estos E2E necesitan
  // CUATRO procesos vivos —backend-admin (JWT), backend-clinic, el front y, para
  // los flujos de cariotipo, backend-ml con el modelo de 42 MB— y arrancarlos
  // desde Playwright escondería esa dependencia detrás de un timeout de 120 s
  // que ya falló una vez. Quien corra la suite tiene que saber que el stack es
  // un requisito, no un detalle de configuración.
  //
  //   backend-admin :  manage.py runserver 8001
  //   backend-clinic:  manage.py runserver 8002   <- lo exige el proxy de Vite
  //   frontend      :  npx vite            (puerto 5174, el de vite.config)
});
