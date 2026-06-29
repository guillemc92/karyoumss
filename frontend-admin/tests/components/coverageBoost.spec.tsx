import { describe, expect, it, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AdminUsersPanel } from '../../src/admin/components/AdminUsersPanel';
import { AdminUsersProvider } from '../../src/admin/state/adminUsersStore';
import { createAdminClient, setAuthToken } from '../../src/admin/api/adminClient';
import { UserTable } from '../../src/admin/components/UserTable';
import { UserDeleteConfirm } from '../../src/admin/components/UserDeleteConfirm';
import type { AdminUser } from '../../src/admin/types/adminUser';

const sampleUser: AdminUser = {
  id: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
  full_name: 'Sample User',
  email: 'sample@biomed.umss.bo',
  role: 'analista',
  active: true,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  created_by: null,
};

function renderPanel() {
  return render(
    <AdminUsersProvider>
      <AdminUsersPanel />
    </AdminUsersProvider>,
  );
}

describe('AdminUsersPanel — flujos secundarios (cobertura)', () => {
  beforeEach(() => {
    setAuthToken(null);
  });

  it('muestra error si load() falla', async () => {
    const client = createAdminClient('/api/admin');
    client.list = vi.fn(async () => {
      throw new Error('red caída');
    });
    render(
      <AdminUsersProvider client={client}>
        <AdminUsersPanel />
      </AdminUsersProvider>,
    );
    await waitFor(() => {
      expect(screen.getByTestId('load-error')).toHaveTextContent(/red caída/);
    });
  });

  it('muestra empty state cuando la lista viene vacía', async () => {
    const client = createAdminClient('/api/admin');
    client.list = vi.fn(async () => []);
    render(
      <AdminUsersProvider client={client}>
        <AdminUsersPanel />
      </AdminUsersProvider>,
    );
    await waitFor(() => {
      expect(screen.getByTestId('empty-users')).toBeInTheDocument();
    });
  });

  it('abre dialog de edit y guarda cambios', async () => {
    const user = userEvent.setup();
    renderPanel();
    await screen.findByText('Ana Castro');
    await user.click(screen.getByTestId('edit-11111111-1111-1111-1111-111111111111'));
    expect(screen.getByText('Editar usuario')).toBeInTheDocument();
    // Cambia nombre y rol
    const nameInput = screen.getByTestId('input-full_name');
    await user.clear(nameInput);
    await user.type(nameInput, 'Ana Castro Actualizada');
    await user.selectOptions(screen.getByTestId('select-role'), 'analista');
    await user.click(screen.getByTestId('submit-user'));
    await waitFor(() =>
      expect(screen.queryByText('Editar usuario')).not.toBeInTheDocument(),
    );
  });

  it('abre dialog de delete y cancela', async () => {
    const user = userEvent.setup();
    renderPanel();
    await screen.findByText('Ana Castro');
    await user.click(screen.getByTestId('delete-11111111-1111-1111-1111-111111111111'));
    expect(screen.getByTestId('delete-confirm')).toBeInTheDocument();
    await user.click(screen.getByTestId('cancel-delete'));
    expect(screen.queryByTestId('delete-confirm')).not.toBeInTheDocument();
  });

  it('abre dialog de delete y confirma eliminación', async () => {
    const user = userEvent.setup();
    renderPanel();
    await screen.findByText('Bruno Pinto');
    await user.click(screen.getByTestId('delete-22222222-2222-2222-2222-222222222222'));
    await user.click(screen.getByTestId('confirm-delete'));
    await waitFor(() => {
      expect(screen.queryByText('Bruno Pinto')).not.toBeInTheDocument();
    });
  });

  it('abre historial y muestra entradas', async () => {
    const user = userEvent.setup();
    renderPanel();
    await screen.findByText('Ana Castro');
    await user.click(screen.getByTestId('history-11111111-1111-1111-1111-111111111111'));
    await waitFor(() => {
      expect(screen.getByTestId('history-list')).toBeInTheDocument();
    });
    await user.click(screen.getByTestId('close-history'));
    expect(screen.queryByTestId('history-modal')).not.toBeInTheDocument();
  });

  it('botón recargar invoca load() de nuevo', async () => {
    const user = userEvent.setup();
    renderPanel();
    await screen.findByText('Ana Castro');
    await user.click(screen.getByTestId('reload'));
    // Después del click debe seguir mostrando los usuarios (status=success)
    expect(screen.getByText('Ana Castro')).toBeInTheDocument();
  });

  it('muestra dialog-error si createUser lanza', async () => {
    const client = createAdminClient('/api/admin');
    client.list = vi.fn(async () => []);
    client.create = vi.fn(async () => {
      throw new Error('server caído');
    });
    const user = userEvent.setup();
    render(
      <AdminUsersProvider client={client}>
        <AdminUsersPanel />
      </AdminUsersProvider>,
    );
    await screen.findByTestId('empty-users');
    await user.click(screen.getByTestId('new-user'));
    await user.type(screen.getByTestId('input-full_name'), 'Cualquier Nombre');
    await user.type(screen.getByTestId('input-email'), 'cualquier@biomed.umss.bo');
    await user.click(screen.getByTestId('submit-user'));
    await waitFor(() =>
      expect(screen.getByTestId('dialog-error')).toHaveTextContent(/server caído/),
    );
  });

  it('muestra dialog-error si deleteUser lanza', async () => {
    const client = createAdminClient('/api/admin');
    client.list = vi.fn(async () => [sampleUser]);
    client.softDelete = vi.fn(async () => {
      throw new Error('forbidden');
    });
    const user = userEvent.setup();
    render(
      <AdminUsersProvider client={client}>
        <AdminUsersPanel />
      </AdminUsersProvider>,
    );
    await screen.findByText('Sample User');
    await user.click(screen.getByTestId(`delete-${sampleUser.id}`));
    await user.click(screen.getByTestId('confirm-delete'));
    await waitFor(() =>
      expect(screen.getByTestId('dialog-error')).toHaveTextContent(/forbidden/),
    );
  });

  it('muestra modal de historial con lista vacía', async () => {
    const client = createAdminClient('/api/admin');
    const userInactivo: AdminUser = {
      ...sampleUser,
      id: 'cccccccc-cccc-cccc-cccc-cccccccccccc',
      full_name: 'Carlos Test',
    };
    client.list = vi.fn(async () => [userInactivo]);
    client.history = vi.fn(async () => []);
    const user = userEvent.setup();
    render(
      <AdminUsersProvider client={client}>
        <AdminUsersPanel />
      </AdminUsersProvider>,
    );
    await screen.findByText('Carlos Test');
    await user.click(screen.getByTestId(`history-${userInactivo.id}`));
    await waitFor(() => {
      expect(screen.getByText('Sin entradas de auditoría.')).toBeInTheDocument();
    });
  });

  it('muestra "No se pudo cargar el historial" cuando history falla', async () => {
    const client = createAdminClient('/api/admin');
    const userConHistoria: AdminUser = {
      ...sampleUser,
      id: 'dddddddd-dddd-dddd-dddd-dddddddddddd',
      full_name: 'Diana Test',
    };
    client.list = vi.fn(async () => [userConHistoria]);
    client.history = vi.fn(async () => {
      throw new Error('boom');
    });
    const user = userEvent.setup();
    render(
      <AdminUsersProvider client={client}>
        <AdminUsersPanel />
      </AdminUsersProvider>,
    );
    await screen.findByText('Diana Test');
    await user.click(screen.getByTestId(`history-${userConHistoria.id}`));
    await waitFor(() => {
      expect(screen.getByText('No se pudo cargar el historial.')).toBeInTheDocument();
    });
  });
});

describe('UserTable — handlers', () => {
  it('invoca onEdit, onDelete, onShowHistory', async () => {
    const user = userEvent.setup();
    const onEdit = vi.fn();
    const onDelete = vi.fn();
    const onShowHistory = vi.fn();
    render(
      <UserTable
        users={[sampleUser]}
        onEdit={onEdit}
        onDelete={onDelete}
        onShowHistory={onShowHistory}
      />,
    );
    await user.click(screen.getByTestId(`edit-${sampleUser.id}`));
    expect(onEdit).toHaveBeenCalledWith(sampleUser);
    await user.click(screen.getByTestId(`delete-${sampleUser.id}`));
    expect(onDelete).toHaveBeenCalledWith(sampleUser);
    await user.click(screen.getByTestId(`history-${sampleUser.id}`));
    expect(onShowHistory).toHaveBeenCalledWith(sampleUser);
  });
});

describe('UserDeleteConfirm', () => {
  it('muestra info y llama onConfirm / onCancel', async () => {
    const onConfirm = vi.fn(async () => undefined);
    const onCancel = vi.fn();
    const user = userEvent.setup();
    render(
      <UserDeleteConfirm
        user={sampleUser}
        onConfirm={onConfirm}
        onCancel={onCancel}
      />,
    );
    expect(screen.getByTestId('delete-confirm')).toHaveTextContent(/Sample User/);
    await user.click(screen.getByTestId('confirm-delete'));
    expect(onConfirm).toHaveBeenCalled();
    await user.click(screen.getByTestId('cancel-delete'));
    expect(onCancel).toHaveBeenCalled();
  });

  it('respeta busy (botón disabled)', () => {
    render(
      <UserDeleteConfirm
        user={sampleUser}
        onConfirm={() => Promise.resolve()}
        onCancel={() => undefined}
        busy
      />,
    );
    expect(screen.getByTestId('confirm-delete')).toBeDisabled();
  });
});

describe('UserTable — branches', () => {
  it('muestra status "Inactivo" para usuarios no activos', () => {
    const inactive: AdminUser = { ...sampleUser, active: false };
    render(
      <UserTable
        users={[inactive]}
        onEdit={() => undefined}
        onDelete={() => undefined}
        onShowHistory={() => undefined}
      />,
    );
    const pill = screen.getByTestId(`status-pill-${inactive.id}`);
    expect(pill).toHaveTextContent('Inactivo');
  });
});