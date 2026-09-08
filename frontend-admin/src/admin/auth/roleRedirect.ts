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

/** `null` significa "quedarse en esta SPA" (solo aplica a admin). */
export function getRedirectForRole(role: Role): string | null {
  switch (role) {
    case 'admin':
      return null;
    case 'analista':
      return `${CLINIC_APP_URL}/clinic/samples`;
    case 'supervisor':
      return SUPERVISOR_LEGACY_URL;
    default:
      return null;
  }
}
