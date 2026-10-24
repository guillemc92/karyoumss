import { useEffect, useState } from 'react';
import { AdminUser, AdminUserDraft } from '../types/adminUser';
import { useAdminUsers } from '../state/adminUsersStore';
import { UserTable } from './UserTable';
import { UserForm } from './UserForm';
import { UserDeleteConfirm } from './UserDeleteConfirm';
import { EmptyState } from './EmptyState';

type Dialog =
  | { kind: 'none' }
  | { kind: 'create' }
  | { kind: 'edit'; user: AdminUser }
  | { kind: 'delete'; user: AdminUser }
  | { kind: 'history'; user: AdminUser };

export function AdminUsersPanel() {
  const { state, load, createUser, updateUser, deleteUser, openHistory, closeHistory } =
    useAdminUsers();
  const [dialog, setDialog] = useState<Dialog>({ kind: 'none' });
  const [dialogBusy, setDialogBusy] = useState(false);
  const [dialogError, setDialogError] = useState<string | null>(null);

  // Carga inicial: status idle → loading → success/error.
  useEffect(() => {
    if (state.status === 'idle') {
      void load();
    }
  }, [state.status, load]);

  async function submitFromForm(draft: AdminUserDraft) {
    setDialogBusy(true);
    setDialogError(null);
    try {
      if (dialog.kind === 'create') {
        await createUser(draft);
      } else if (dialog.kind === 'edit') {
        await updateUser(dialog.user.id, {
          full_name: draft.full_name,
          role: draft.role,
          active: draft.active,
        });
      }
      setDialog({ kind: 'none' });
    } catch (err) {
      setDialogError(err instanceof Error ? err.message : 'Error al guardar');
    } finally {
      setDialogBusy(false);
    }
  }

  async function handleConfirmDelete() {
    if (dialog.kind !== 'delete') return;
    setDialogBusy(true);
    setDialogError(null);
    try {
      await deleteUser(dialog.user.id);
      setDialog({ kind: 'none' });
    } catch (err) {
      setDialogError(err instanceof Error ? err.message : 'Error al eliminar');
    } finally {
      setDialogBusy(false);
    }
  }

  function closeDialog() {
    if (dialog.kind === 'history') closeHistory();
    setDialog({ kind: 'none' });
    setDialogError(null);
  }

  return (
    <section data-testid="admin-users-panel">
      <header className="biomed-panel-actions">
        <button
          type="button"
          className="biomed-btn biomed-btn--primary"
          onClick={() => {
            setDialog({ kind: 'create' });
            setDialogError(null);
          }}
          data-testid="new-user"
        >
          + Nuevo usuario
        </button>
        <button
          type="button"
          className="biomed-btn"
          onClick={() => void load()}
          disabled={state.status === 'loading'}
          data-testid="reload"
        >
          {state.status === 'loading' ? 'Cargando…' : 'Recargar'}
        </button>
      </header>

      {state.status === 'error' && (
        <p role="alert" className="biomed-form-error" data-testid="load-error">
          {state.errorMessage}
        </p>
      )}

      {state.status === 'success' && state.users.length === 0 && (
        <EmptyState
          title="No hay usuarios administradores activos."
          hint="Crea el primero con el botón «Nuevo usuario»."
          testId="empty-users"
        />
      )}

      {(state.status === 'success' || state.status === 'loading') &&
        state.users.length > 0 && (
          <UserTable
            users={state.users}
            onEdit={(user) => {
              setDialog({ kind: 'edit', user });
              setDialogError(null);
            }}
            onDelete={(user) => {
              setDialog({ kind: 'delete', user });
              setDialogError(null);
            }}
            onShowHistory={(user) => {
              setDialog({ kind: 'history', user });
              void openHistory(user.id);
            }}
          />
        )}

      {(dialog.kind === 'create' || dialog.kind === 'edit') && (
        <div className="biomed-modal-backdrop" data-testid="modal-backdrop">
          <UserForm
            editing={dialog.kind === 'edit' ? dialog.user : undefined}
            onSubmit={submitFromForm}
            onCancel={closeDialog}
          />
          {dialogError && (
            <p role="alert" className="biomed-form-error" data-testid="dialog-error">
              {dialogError}
            </p>
          )}
        </div>
      )}

      {dialog.kind === 'delete' && (
        <div className="biomed-modal-backdrop" data-testid="modal-backdrop">
          <UserDeleteConfirm
            user={dialog.user}
            busy={dialogBusy}
            onConfirm={handleConfirmDelete}
            onCancel={closeDialog}
          />
          {dialogError && (
            <p role="alert" className="biomed-form-error" data-testid="dialog-error">
              {dialogError}
            </p>
          )}
        </div>
      )}

      {dialog.kind === 'history' && (
        <div className="biomed-modal-backdrop" data-testid="modal-backdrop">
          <div className="biomed-modal" data-testid="history-modal">
            <h2>Historial de {dialog.user.full_name}</h2>
            {state.historyStatus === 'loading' && <p>Cargando…</p>}
            {state.historyStatus === 'error' && (
              <p role="alert" className="biomed-form-error">
                No se pudo cargar el historial.
              </p>
            )}
            {state.historyStatus === 'success' && state.history.length === 0 && (
              <p>Sin entradas de auditoría.</p>
            )}
            {state.historyStatus === 'success' && state.history.length > 0 && (
              <ul data-testid="history-list">
                {state.history.map((e) => (
                  <li key={e.id}>
                    <strong>{e.action}</strong> · {new Date(e.timestamp).toLocaleString()} ·{' '}
                    {e.actor_email ?? 'sistema'}
                  </li>
                ))}
              </ul>
            )}
            <div className="biomed-form-actions">
              <button
                type="button"
                className="biomed-btn"
                onClick={closeDialog}
                data-testid="close-history"
              >
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}