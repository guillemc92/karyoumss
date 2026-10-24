import { AdminUser } from '../types/adminUser';

interface UserDeleteConfirmProps {
  user: AdminUser;
  onConfirm: () => Promise<void>;
  onCancel: () => void;
  busy?: boolean;
}

export function UserDeleteConfirm({ user, onConfirm, onCancel, busy }: UserDeleteConfirmProps) {
  return (
    <div className="biomed-modal" role="alertdialog" data-testid="delete-confirm">
      <h2>Eliminar usuario</h2>
      <p>
        ¿Desactivar a <strong>{user.full_name}</strong> (<code>{user.email}</code>)? Esta acción
        es reversible sólo por un administrador (soft-delete).
      </p>
      <div className="biomed-form-actions">
        <button
          type="button"
          className="biomed-btn biomed-btn--danger"
          onClick={onConfirm}
          disabled={busy}
          data-testid="confirm-delete"
        >
          {busy ? 'Desactivando…' : 'Sí, desactivar'}
        </button>
        <button
          type="button"
          className="biomed-btn"
          onClick={onCancel}
          disabled={busy}
          data-testid="cancel-delete"
        >
          Cancelar
        </button>
      </div>
    </div>
  );
}