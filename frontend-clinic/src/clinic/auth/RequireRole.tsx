import type { ReactNode } from 'react';
import { useSession, type ClinicRole } from '.';

interface RequireRoleProps {
  roles: ClinicRole[];
  children: ReactNode;
  fallback?: ReactNode;
}

/** RN-06: oculta acciones que el rol actual no puede ejecutar (cortesía UI; la defensa real vive en el backend). */
export function RequireRole({ roles, children, fallback = null }: RequireRoleProps) {
  const { role } = useSession();
  if (!role || !roles.includes(role)) {
    return <>{fallback}</>;
  }
  return <>{children}</>;
}
