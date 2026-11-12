/**
 * roleRedirect — implementa ADR-0017 D7: destino post-login por rol.
 *
 * 'admin' se queda dentro de esta SPA (PrivateRoute lo deja pasar).
 * 'analista'/'supervisor' navegan fuera (cross-app, gap de SSO documentado
 * en ADR-0017 D7 — no se propaga sesión al destino).
 */
import type { Role } from './types';

const CLINIC_APP_URL =
  (import.meta.env.VITE_CLINIC_APP_URL as string | undefined) ?? 'http://localhost:5174';

const SUPERVISOR_LEGACY_URL =
  (import.meta.env.VITE_SUPERVISOR_LEGACY_URL as string | undefined) ?? '/supervisor.html';

/**
 * La lista de muestras de la app clínica, a partir de su URL base.
 *
 * La base llega de configuración y tiene dos formas válidas: el origen de la app
 * (`http://localhost:5174`, en desarrollo) o su ruta detrás del proxy (`/clinic/`,
 * en el stack). Antes se le pegaba `/clinic/samples` sin mirar, y con la segunda
 * forma salía `/clinic//clinic/samples`: una página en blanco al entrar como
 * analista (Demo 3, 04/11/2026).
 */
export function urlMuestrasClinica(base: string): string {
  const sinBarraFinal = base.replace(/\/+$/, '');
  return sinBarraFinal.endsWith('/clinic')
    ? `${sinBarraFinal}/samples`
    : `${sinBarraFinal}/clinic/samples`;
}

/** `null` significa "quedarse en esta SPA" (solo aplica a admin). */
export function getRedirectForRole(role: Role): string | null {
  switch (role) {
    case 'admin':
      return null;
    case 'analista':
      return urlMuestrasClinica(CLINIC_APP_URL);
    case 'supervisor':
      return SUPERVISOR_LEGACY_URL;
    default:
      return null;
  }
}
