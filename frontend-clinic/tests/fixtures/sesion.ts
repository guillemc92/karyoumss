import { expect, test as base } from '@playwright/test';

/**
 * Sesión real contra backend-admin, y datos propios por test.
 *
 * ## Por qué el token se pide al backend y no se falsifica
 *
 * ADR-0020: backend-admin es la **única autoridad de JWT**. Un token fabricado
 * en el test pasaría la comprobación del frontend y fallaría en el backend, o
 * peor, pasaría en ambos y estaríamos probando un sistema que en producción no
 * existe. Se pide el token de verdad al endpoint de verdad.
 *
 * ## Aislamiento (pregunta P3 del checklist)
 *
 * Cada test que crea una muestra usa su **propio CHN**, generado con marca de
 * tiempo. Sin eso, el segundo test chocaría con el CHN del primero (409
 * CHN_DUPLICATE) y el resultado dependería del orden de ejecución — que es
 * exactamente lo que P3 descarta.
 */

const AUTH_BASE = process.env.E2E_AUTH_BASE || 'http://localhost:8001';

export interface Credenciales {
  /** El login de backend-admin pide `email`, NO `username`. Se descubrió
   *  ejecutando contra el backend real: con `username` devuelve
   *  `{"email":["Este campo es requerido."]}`. Es exactamente la clase de
   *  detalle que un doble de red habría ocultado. */
  email: string;
  password: string;
}

export const ANALISTA: Credenciales = {
  email: process.env.E2E_ANALISTA_USER || 'demo.analista@biomed.umss.bo',
  password: process.env.E2E_ANALISTA_PASS || 'E2ePlaywright!2026',
};

export const SUPERVISOR: Credenciales = {
  email: process.env.E2E_SUPERVISOR_USER || 'demo_supervisor@umss.bo',
  password: process.env.E2E_SUPERVISOR_PASS || 'E2ePlaywright!2026',
};

/** Pide un JWT real a backend-admin. Lanza con el motivo si no lo da. */
export async function pedirToken(request: any, cred: Credenciales) {
  const r = await request.post(`${AUTH_BASE}/api/auth/login/`, {
    data: { email: cred.email, password: cred.password },
  });
  if (!r.ok()) {
    throw new Error(
      `backend-admin no emitió token para ${cred.email}: ${r.status()} ${await r.text()}`,
    );
  }
  const data = await r.json();
  return { access: data.access as string, refresh: data.refresh as string };
}

/**
 * Deja la sesión puesta ANTES de que cargue la app.
 *
 * `addInitScript` corre antes de cualquier script de la página, así que
 * `SessionProvider` ya encuentra el token al montarse. Navegar primero y
 * escribir después obligaría a recargar, y esa recarga es una espera implícita
 * de las que P2 descarta.
 */
export async function sembrarSesion(page: any, tokens: { access: string; refresh: string }) {
  await page.addInitScript(
    ([acceso, refresco]: [string, string]) => {
      localStorage.setItem('biomed.auth.access', acceso);
      localStorage.setItem('biomed.auth.refresh', refresco);
    },
    [tokens.access, tokens.refresh],
  );
}

/** CHN único por test. Formato real: CHN-AAAA-MM-DD-NNNN. */
export function chnUnico(): string {
  const ahora = new Date();
  const fecha = ahora.toISOString().slice(0, 10);
  const secuencia = String(ahora.getTime() % 10000).padStart(4, '0');
  return `CHN-${fecha}-${secuencia}`;
}

type Fixtures = {
  comoAnalista: void;
  comoSupervisor: void;
};

export const test = base.extend<Fixtures>({
  comoAnalista: [
    async ({ page, request }, use) => {
      await sembrarSesion(page, await pedirToken(request, ANALISTA));
      await use();
    },
    { auto: false },
  ],
  comoSupervisor: [
    async ({ page, request }, use) => {
      await sembrarSesion(page, await pedirToken(request, SUPERVISOR));
      await use();
    },
    { auto: false },
  ],
});

export { expect };
