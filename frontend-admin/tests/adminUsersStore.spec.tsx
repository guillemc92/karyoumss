import { describe, expect, it, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import type { ReactNode } from 'react';
import { AdminUsersProvider, useAdminUsers } from '../src/admin/state/adminUsersStore';
import { createAdminClient } from '../src/admin/api/adminClient';
import type { AdminUser } from '../src/admin/types/adminUser';

function wrapperWith(client: ReturnType<typeof createAdminClient>) {
  return ({ children }: { children: ReactNode }) => (
    <AdminUsersProvider client={client}>{children}</AdminUsersProvider>
  );
}

const sampleUser: AdminUser = {
  id: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
  full_name: 'Test User',
  email: 'test@biomed.umss.bo',
  role: 'analista',
  active: true,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  created_by: null,
};

describe('adminUsersStore (puro, con client inyectado)', () => {
  it('lanza error si useAdminUsers se usa fuera del provider', () => {
    expect(() => renderHook(() => useAdminUsers())).toThrow(/AdminUsersProvider/);
  });

  it('load() exitoso actualiza state.users', async () => {
    const client = createAdminClient('/api/admin');
    const listSpy = vi.fn(async () => [sampleUser]);
    client.list = listSpy;
    const { result } = renderHook(() => useAdminUsers(), {
      wrapper: wrapperWith(client),
    });
    await act(async () => {
      await result.current.load();
    });
    expect(result.current.state.users).toEqual([sampleUser]);
    expect(result.current.state.status).toBe('success');
    expect(listSpy).toHaveBeenCalled();
  });

  it('load() con error → state.status=error y message', async () => {
    const client = createAdminClient('/api/admin');
    client.list = async () => {
      throw new Error('boom');
    };
    const { result } = renderHook(() => useAdminUsers(), {
      wrapper: wrapperWith(client),
    });
    await act(async () => {
      await result.current.load();
    });
    expect(result.current.state.status).toBe('error');
    expect(result.current.state.errorMessage).toBe('boom');
  });

  it('createUser() inserta en users', async () => {
    const client = createAdminClient('/api/admin');
    client.create = async () => sampleUser;
    const { result } = renderHook(() => useAdminUsers(), {
      wrapper: wrapperWith(client),
    });
    await act(async () => {
      await result.current.createUser({
        full_name: sampleUser.full_name,
        email: sampleUser.email,
        role: sampleUser.role,
        active: true,
      });
    });
    expect(result.current.state.users).toContainEqual(sampleUser);
  });

  it('updateUser() reemplaza existente por id', async () => {
    const client = createAdminClient('/api/admin');
    const updated: AdminUser = { ...sampleUser, full_name: 'Test Updated' };
    client.list = async () => [sampleUser];
    client.update = async () => updated;
    const { result } = renderHook(() => useAdminUsers(), {
      wrapper: wrapperWith(client),
    });
    await act(async () => {
      await result.current.load();
    });
    await act(async () => {
      await result.current.updateUser(sampleUser.id, { full_name: 'Test Updated' });
    });
    expect(result.current.state.users[0].full_name).toBe('Test Updated');
  });

  it('deleteUser() quita de users', async () => {
    const client = createAdminClient('/api/admin');
    client.list = async () => [sampleUser];
    client.softDelete = async () => undefined;
    const { result } = renderHook(() => useAdminUsers(), {
      wrapper: wrapperWith(client),
    });
    await act(async () => {
      await result.current.load();
    });
    await act(async () => {
      await result.current.deleteUser(sampleUser.id);
    });
    expect(result.current.state.users).toEqual([]);
  });

  it('openHistory() y closeHistory()', async () => {
    const client = createAdminClient('/api/admin');
    client.history = async () => [
      {
        id: 1,
        action: 'create',
        timestamp: '2026-01-01T00:00:00Z',
        actor_email: 'system',
        changes: {},
        object_repr: 'Test User',
      },
    ];
    const { result } = renderHook(() => useAdminUsers(), {
      wrapper: wrapperWith(client),
    });
    await act(async () => {
      await result.current.openHistory(sampleUser.id);
    });
    expect(result.current.state.historyOpenFor).toBe(sampleUser.id);
    expect(result.current.state.historyStatus).toBe('success');
    expect(result.current.state.history).toHaveLength(1);
    act(() => {
      result.current.closeHistory();
    });
    expect(result.current.state.historyOpenFor).toBeNull();
    expect(result.current.state.history).toEqual([]);
  });

  it('openHistory() con error → historyStatus=error', async () => {
    const client = createAdminClient('/api/admin');
    client.history = async () => {
      throw new Error('boom history');
    };
    const { result } = renderHook(() => useAdminUsers(), {
      wrapper: wrapperWith(client),
    });
    await act(async () => {
      await result.current.openHistory(sampleUser.id);
    });
    expect(result.current.state.historyStatus).toBe('error');
  });

  it('load() con throw que no es Error → mensaje por defecto', async () => {
    const client = createAdminClient('/api/admin');
    client.list = async () => {
      // eslint-disable-next-line @typescript-eslint/no-throw-literal
      throw 'string-error';
    };
    const { result } = renderHook(() => useAdminUsers(), {
      wrapper: wrapperWith(client),
    });
    await act(async () => {
      await result.current.load();
    });
    expect(result.current.state.status).toBe('error');
    expect(result.current.state.errorMessage).toBe('Error desconocido');
  });

  it('createUser() inserta o reemplaza (upsert por id)', async () => {
    const client = createAdminClient('/api/admin');
    const updated: AdminUser = { ...sampleUser, full_name: 'Test Updated' };
    client.list = async () => [sampleUser];
    client.update = async () => updated;
    const { result } = renderHook(() => useAdminUsers(), {
      wrapper: wrapperWith(client),
    });
    await act(async () => {
      await result.current.load();
    });
    // create con mismo id → reemplaza
    client.create = async () => updated;
    await act(async () => {
      await result.current.createUser({
        full_name: updated.full_name,
        email: updated.email,
        role: updated.role,
        active: updated.active,
      });
    });
    expect(result.current.state.users).toHaveLength(1);
    expect(result.current.state.users[0].full_name).toBe('Test Updated');
  });
});