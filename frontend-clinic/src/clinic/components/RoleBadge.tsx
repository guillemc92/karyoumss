import type { ClinicRole } from '../auth';

const LABELS: Record<ClinicRole, string> = {
  analista: 'Analista',
  supervisor: 'Supervisor',
  admin: 'Administrador',
};

export function RoleBadge({ role }: { role: ClinicRole }) {
  return <span className="role-badge" data-role={role}>{LABELS[role]}</span>;
}
