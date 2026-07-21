import { createContext, useCallback, useEffect, useState, type ReactNode } from 'react';
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

  return (
    <SessionContext.Provider value={{ ...session, login: doLogin, logout: doLogout }}>
      {children}
    </SessionContext.Provider>
  );
}
