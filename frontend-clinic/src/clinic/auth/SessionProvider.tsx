import { createContext, useCallback, useEffect, useRef, useState, type ReactNode } from 'react';
import * as authClient from '../api/authClient';

export type ClinicRole = 'analista' | 'supervisor' | 'admin';

export interface Session {
  isAuthenticated: boolean;
  role: ClinicRole | null;
  username: string | null;
}

export interface SessionContextValue extends Session {
  login: (username: string, password: string, role: ClinicRole) => Promise<void>;
  logout: () => void;
}

export const SessionContext = createContext<SessionContextValue | undefined>(undefined);

/** SSO (ADR-0020): storage real, compartido con frontend-admin. */
const SESSION_ACCESS_KEY = 'biomed.auth.access';

/** Espera antes de reintentar una renovación que falló por red. */
const REINTENTO_MS = 30_000;

/** Decodifica el payload de un JWT sin verificar firma — la firma ya la
 * valida el backend; acá solo se leen claims para UX (mismo patrón que
 * frontend-admin/src/admin/auth/authClient.ts::decodeExp()). */
function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const payload = token.split('.')[1];
    return JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/')));
  } catch {
    return null;
  }
}

function sessionFromToken(): Session {
  const token = localStorage.getItem(SESSION_ACCESS_KEY);
  if (!token) return { isAuthenticated: false, role: null, username: null };
  const claims = decodeJwtPayload(token);
  const role = (claims?.role as ClinicRole) ?? null;
  const username = (claims?.email as string) ?? null;
  return { isAuthenticated: true, role, username };
}

interface SessionProviderProps {
  children: ReactNode;
  /** Modo demo: fuerza sesión analista sin pedir login (para MSW). */
  forceAnalystOnMount?: boolean;
}

export function SessionProvider({ children, forceAnalystOnMount = false }: SessionProviderProps) {
  const [session, setSession] = useState<Session>(() => sessionFromToken());

  const doLogin = useCallback(async (username: string, password: string, role: ClinicRole) => {
    // Solo alcanzable en modo demo MSW (ver authClient.ts) — el login real
    // ocurre en frontend-admin, no acá.
    await authClient.login(username, password);
    setSession({ isAuthenticated: true, role, username });
  }, []);

  const doLogout = useCallback(() => {
    authClient.logout();
    setSession({ isAuthenticated: false, role: null, username: null });
  }, []);

  useEffect(() => {
    if (forceAnalystOnMount && !session.isAuthenticated) {
      void doLogin('demo_analista', 'demo12345', 'analista');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [forceAnalystOnMount]);

  // --- Renovación automática de la sesión SSO ------------------------------
  // El SPA clínico es otra aplicación que la de administración: al entrar aquí
  // el temporizador de refresco de frontend-admin ya no existe. Sin esto, la
  // sesión moría a los 30 minutos en mitad del trabajo.
  const temporizador = useRef<ReturnType<typeof setTimeout> | null>(null);

  const programarRenovacion = useCallback((token: string) => {
    const exp = authClient.decodeExp(token);
    if (exp === null) return;
    const ahora = Date.now() / 1000;
    const demora = Math.max((exp - ahora - authClient.MARGEN_RENOVACION_SEGUNDOS) * 1000, 0);
    temporizador.current = setTimeout(() => {
      void authClient.renovarSesion().then((nuevo) => {
        if (nuevo) {
          programarRenovacion(nuevo);
          return;
        }
        // Que falle una renovación no significa que la sesión haya muerto:
        // puede ser un corte de red momentáneo. Mientras al token le quede
        // vida se reintenta; solo se cierra cuando ya está caducado de verdad.
        // Echar al usuario de una sesión válida es peor que el fallo original.
        if (Date.now() / 1000 < exp) {
          temporizador.current = setTimeout(() => programarRenovacion(token), REINTENTO_MS);
        } else {
          setSession({ isAuthenticated: false, role: null, username: null });
        }
      });
    }, demora);
  }, []);

  useEffect(() => {
    const token = authClient.getAccessToken();
    if (!token) return;
    programarRenovacion(token);
    return () => {
      if (temporizador.current) clearTimeout(temporizador.current);
    };
  }, [session.isAuthenticated, programarRenovacion]);

  return (
    <SessionContext.Provider value={{ ...session, login: doLogin, logout: doLogout }}>
      {children}
    </SessionContext.Provider>
  );
}
