/**
 * AuthContext — sesión real del login unificado (ADR-0017).
 *
 * Hidrata desde localStorage al montar (valida contra /me, no confía
 * ciegamente en el token guardado). Programa un refresh automático antes
 * de que expire el access token (decodifica `exp`, setTimeout).
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import * as authClient from './authClient';
import type { MeResponse, Role } from './types';

export interface AuthUser {
  email: string;
  role: Role;
  fullName: string | null;
}

export interface AuthApi {
  user: AuthUser | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<AuthUser>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthApi | null>(null);

const REFRESH_MARGIN_SECONDS = 60;

function toAuthUser(me: MeResponse): AuthUser {
  return { email: me.email, role: me.role, fullName: me.full_name };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const refreshTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearRefreshTimer = useCallback(() => {
    if (refreshTimer.current) {
      clearTimeout(refreshTimer.current);
      refreshTimer.current = null;
    }
  }, []);

  const scheduleAutoRefresh = useCallback(
    (accessToken: string) => {
      clearRefreshTimer();
      const exp = authClient.decodeExp(accessToken);
      if (exp === null) return;
      const nowSeconds = Date.now() / 1000;
      const delayMs = Math.max((exp - nowSeconds - REFRESH_MARGIN_SECONDS) * 1000, 0);
      refreshTimer.current = setTimeout(async () => {
        const newAccess = await authClient.refresh();
        if (newAccess) {
          scheduleAutoRefresh(newAccess);
        } else {
          setUser(null);
        }
      }, delayMs);
    },
    [clearRefreshTimer],
  );

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const access = authClient.getAccessToken();
      if (!access) {
        setIsLoading(false);
        return;
      }
      const me = await authClient.me();
      if (cancelled) return;
      if (me) {
        setUser(toAuthUser(me));
        scheduleAutoRefresh(access);
      } else {
        authClient.clearTokens();
      }
      setIsLoading(false);
    })();
    return () => {
      cancelled = true;
      clearRefreshTimer();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      const data = await authClient.login(email, password);
      const authUser: AuthUser = { email: data.email, role: data.role, fullName: data.full_name };
      setUser(authUser);
      scheduleAutoRefresh(data.access);
      return authUser;
    },
    [scheduleAutoRefresh],
  );

  const logout = useCallback(async () => {
    clearRefreshTimer();
    await authClient.logout();
    setUser(null);
  }, [clearRefreshTimer]);

  const value = useMemo<AuthApi>(
    () => ({
      user,
      isLoading,
      isAuthenticated: user !== null,
      login,
      logout,
    }),
    [user, isLoading, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthApi {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth debe usarse dentro de <AuthProvider>');
  }
  return ctx;
}
