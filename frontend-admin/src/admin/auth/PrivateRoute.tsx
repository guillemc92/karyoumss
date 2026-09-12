import type { ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from './AuthContext';
import { getRedirectForRole } from './roleRedirect';
import type { Role } from './types';

interface PrivateRouteProps {
  children: ReactNode;
  allowedRoles: Role[];
}

/**
 * Guard de rutas (ADR-0017 D7): sin sesión → /login. Con sesión pero rol no
 * permitido en esta SPA → redirige fuera vía roleRedirect (nunca renderiza
 * el contenido protegido para un rol no autorizado).
 */
export function PrivateRoute({ children, allowedRoles }: PrivateRouteProps) {
  const { user, isLoading, isAuthenticated } = useAuth();

  if (isLoading) {
    return null;
  }

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" replace />;
  }

  if (!allowedRoles.includes(user.role)) {
    const target = getRedirectForRole(user.role);
    if (target) {
      window.location.href = target;
      return null;
    }
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}
