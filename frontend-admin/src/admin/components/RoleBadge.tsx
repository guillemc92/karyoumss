import { AdminRole } from '../types/adminUser';

interface RoleBadgeProps {
  role: AdminRole;
}

const LABELS: Record<AdminRole, string> = {
  analista: 'Analista',
  supervisor: 'Supervisor',
  admin: 'Administrador',
};

const TEST_ID: Record<AdminRole, string> = {
  analista: 'role-analista',
  supervisor: 'role-supervisor',
  admin: 'role-admin',
};

export function RoleBadge({ role }: RoleBadgeProps) {
  return (
    <span
      className={`biomed-role-badge biomed-role-badge--${role}`}
      data-testid={TEST_ID[role]}
      title={LABELS[role]}
    >
      {LABELS[role]}
    </span>
  );
}