import { AdminUser } from '../types/adminUser';
import { RoleBadge } from './RoleBadge';

interface UserTableProps {
  users: AdminUser[];
  onEdit: (user: AdminUser) => void;
  onDelete: (user: AdminUser) => void;
  onShowHistory: (user: AdminUser) => void;
}

export function UserTable({ users, onEdit, onDelete, onShowHistory }: UserTableProps) {
  return (
    <table className="biomed-user-table" data-testid="user-table">
      <thead>
        <tr>
          <th>Nombre</th>
          <th>Email</th>
          <th>Rol</th>
          <th>Estado</th>
          <th>Acciones</th>
        </tr>
      </thead>
      <tbody>
        {users.map((u) => (
          <tr key={u.id} data-testid={`user-row-${u.id}`}>
            <td>{u.full_name}</td>
            <td>
              <code>{u.email}</code>
            </td>
            <td>
              <RoleBadge role={u.role} />
            </td>
            <td>
              <span
                className={`biomed-status-pill biomed-status-pill--${u.active ? 'on' : 'off'}`}
                data-testid={`status-pill-${u.id}`}
              >
                {u.active ? 'Activo' : 'Inactivo'}
              </span>
            </td>
            <td>
              <button
                type="button"
                onClick={() => onEdit(u)}
                data-testid={`edit-${u.id}`}
                aria-label={`Editar ${u.full_name}`}
              >
                Editar
              </button>{' '}
              <button
                type="button"
                onClick={() => onShowHistory(u)}
                data-testid={`history-${u.id}`}
                aria-label={`Ver historial de ${u.full_name}`}
              >
                Historial
              </button>{' '}
              <button
                type="button"
                className="biomed-btn biomed-btn--danger"
                onClick={() => onDelete(u)}
                data-testid={`delete-${u.id}`}
                aria-label={`Eliminar ${u.full_name}`}
              >
                Eliminar
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}