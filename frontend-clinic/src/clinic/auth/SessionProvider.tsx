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

const ROLE_KEY = 'biomed.clinic.role';
const USERNAME_KEY = 'biomed.clinic.username';

interface SessionProviderProps {
  children: ReactNode;
  /** Modo demo: fuerza sesión analista sin pedir login (para MSW). */
  forceAnalystOnMount?: boolean;
}

export function SessionProvider({ children, forceAnalystOnMount = false }: SessionProviderProps) {
  const [session, setSession] = useState<Session>(() => ({
    isAuthenticated: authClient.isAuthenticated(),
    role: (localStorage.getItem(ROLE_KEY) as ClinicRole) ?? null,
    username: localStorage.getItem(USERNAME_KEY),
  }));

  const doLogin = useCallback(async (username: string, password: string, role: ClinicRole) => {
    await authClient.login(username, password);
    localStorage.setItem(ROLE_KEY, role);
    localStorage.setItem(USERNAME_KEY, username);
    setSession({ isAuthenticated: true, role, username });
  }, []);

  const doLogout = useCallback(() => {
    authClient.logout();
    localStorage.removeItem(ROLE_KEY);
    localStorage.removeItem(USERNAME_KEY);
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
