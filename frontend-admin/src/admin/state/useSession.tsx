/**
 * useSession — gating del shell institucional.
 *
 * Lee/escribe `biomed:auth:role` y `biomed:auth:currentUserId` en localStorage,
 * usando el mismo namespace que el `configuracion.html` (MVP vigente de
 * PR-IMPL-ADMIN-001). Esto mantiene coherencia entre ambos shells.
 *
 * Demo MSW (VITE_USE_MSW=true): el `SessionProvider` fuerza role=admin al
 * montar para que la demo funcione out-of-the-box sin requerir login manual,
 * replicando el comportamiento del `configuracion.html` actual.
 *
 * Cuando se active F9 (smoke E2E con FastAPI real), el exchange
 * (`exchangeFastApiJwt`) guardará el rol real del usuario y este hook lo
 * respetará sin necesidad de cambios.
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

export type Role = 'admin' | 'supervisor' | 'analista' | null;

const ROLE_KEY = 'biomed:auth:role';
const USER_ID_KEY = 'biomed:auth:currentUserId';
const USER_NAME_KEY = 'biomed:auth:currentUserName';

function safeGet(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function safeSet(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    // localStorage no disponible (modo privado / SSR / tests sin jsdom)
  }
}

function safeRemove(key: string): void {
  try {
    localStorage.removeItem(key);
  } catch {
    // ignorar
  }
}

export function getStoredRole(): Role {
  const v = safeGet(ROLE_KEY);
  if (v === 'admin' || v === 'supervisor' || v === 'analista') return v;
  return null;
}

export function setStoredRole(role: Role): void {
  if (role) safeSet(ROLE_KEY, role);
  else safeRemove(ROLE_KEY);
}

export function getStoredUserName(): string | null {
  return safeGet(USER_NAME_KEY);
}

export function setStoredUserName(name: string | null): void {
  if (name) safeSet(USER_NAME_KEY, name);
  else safeRemove(USER_NAME_KEY);
}

export function getStoredUserId(): string | null {
  return safeGet(USER_ID_KEY);
}

export interface SessionState {
  role: Role;
  userName: string | null;
  isAdmin: boolean;
}

export interface SessionApi extends SessionState {
  setRole: (role: Role) => void;
  setUserName: (name: string | null) => void;
  refresh: () => void;
}

const SessionContext = createContext<SessionApi | null>(null);

export interface SessionProviderProps {
  children: ReactNode;
  /**
   * Si true (default en demo MSW), fuerza role=admin al montar para que
   * la sección "Usuarios" del sidebar sea visible sin login manual.
   * En producción, este flag es false y se respeta el rol real del bridge.
   */
  forceAdminOnMount?: boolean;
}

export function SessionProvider({
  children,
  forceAdminOnMount = false,
}: SessionProviderProps) {
  const [role, setRoleState] = useState<Role>(() => getStoredRole());
  const [userName, setUserNameState] = useState<string | null>(() => getStoredUserName());

  // Demo MSW: si no hay rol seteado y el flag está activo, forzar admin.
  // Esto reproduce el comportamiento del `configuracion.html` actual.
  useEffect(() => {
    if (forceAdminOnMount && !role) {
      setRoleState('admin');
      setStoredRole('admin');
    }
  }, [forceAdminOnMount, role]);

  const setRole = useCallback((next: Role) => {
    setRoleState(next);
    setStoredRole(next);
  }, []);

  const setUserName = useCallback((name: string | null) => {
    setUserNameState(name);
    setStoredUserName(name);
  }, []);

  const refresh = useCallback(() => {
    setRoleState(getStoredRole());
    setUserNameState(getStoredUserName());
  }, []);

  const value = useMemo<SessionApi>(
    () => ({
      role,
      userName,
      isAdmin: role === 'admin',
      setRole,
      setUserName,
      refresh,
    }),
    [role, userName, setRole, setUserName, refresh],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionApi {
  const ctx = useContext(SessionContext);
  if (!ctx) {
    throw new Error('useSession debe usarse dentro de <SessionProvider>');
  }
  return ctx;
}
