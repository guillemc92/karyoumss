/**
 * MSW handlers — simulan los endpoints del bounded context admin.
 * Endpoints reflejan backend-admin/apps/users/urls.py + AUTH_BRIDGE.md.
 *
 * Reset por test: server.resetHandlers() en tests/setup.ts — pero la
 * mutación interna de `baseUsers` se revierte con `resetMockData()`.
 */
import { http, HttpResponse } from 'msw';
import type {
  AdminUser,
  AdminUserDraft,
  AdminUserUpdate,
  AuditLogEntry,
} from '../types/adminUser';

let nextId = 4;

const initialUsers: AdminUser[] = [
  {
    id: '11111111-1111-1111-1111-111111111111',
    full_name: 'Ana Castro',
    email: 'ana.castro@biomed.umss.bo',
    role: 'supervisor',
    active: true,
    created_at: '2026-06-01T10:00:00Z',
    updated_at: '2026-06-01T10:00:00Z',
    created_by: null,
  },
  {
    id: '22222222-2222-2222-2222-222222222222',
    full_name: 'Bruno Pinto',
    email: 'bruno.pinto@biomed.umss.bo',
    role: 'analista',
    active: true,
    created_at: '2026-06-02T11:00:00Z',
    updated_at: '2026-06-02T11:00:00Z',
    created_by: '11111111-1111-1111-1111-111111111111',
  },
  {
    id: '33333333-3333-3333-3333-333333333333',
    full_name: 'Carla Méndez',
    email: 'carla.mendez@biomed.umss.bo',
    role: 'admin',
    active: false,
    created_at: '2026-06-03T09:00:00Z',
    updated_at: '2026-06-03T09:00:00Z',
    created_by: '11111111-1111-1111-1111-111111111111',
  },
];

let baseUsers: AdminUser[] = [...initialUsers];

const initialAuditLog: Record<string, AuditLogEntry[]> = {
  '11111111-1111-1111-1111-111111111111': [
    {
      id: 1,
      action: 'create',
      timestamp: '2026-06-01T10:00:00Z',
      actor_email: 'system@biomed.umss.bo',
      changes: {},
      object_repr: 'Ana Castro <ana.castro@biomed.umss.bo>',
    },
  ],
};

let auditLog: Record<string, AuditLogEntry[]> = { ...initialAuditLog };

/** Restaura la base de datos mock al estado inicial. Tests lo llaman en beforeEach. */
export function resetMockData(): void {
  nextId = 4;
  baseUsers = initialUsers.map((u) => ({ ...u }));
  auditLog = Object.fromEntries(
    Object.entries(initialAuditLog).map(([k, v]) => [k, v.map((e) => ({ ...e }))]),
  );
}

export const handlers = [
  http.get('/api/admin/users/', () => {
    return HttpResponse.json(baseUsers.filter((u) => u.active));
  }),

  http.get('/api/admin/users/:id/', ({ params }) => {
    const user = baseUsers.find((u) => u.id === params.id);
    if (!user || !user.active) {
      return HttpResponse.json({ detail: 'No encontrado' }, { status: 404 });
    }
    return HttpResponse.json(user);
  }),

  http.post('/api/admin/users/', async ({ request }) => {
    const body = (await request.json()) as AdminUserDraft;
    // Validación primero (espejo del serializer + full_clean())
    if (!body.full_name?.trim() || body.full_name.trim().length < 2) {
      return HttpResponse.json(
        { full_name: ['El nombre debe tener al menos 2 caracteres'] },
        { status: 400 },
      );
    }
    if (!body.email?.trim() || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(body.email)) {
      return HttpResponse.json(
        { email: ['Email inválido'] },
        { status: 400 },
      );
    }
    // Unique check (espejo de admin_users_email_lower_unique_idx)
    if (baseUsers.some((u) => u.email.toLowerCase() === body.email.toLowerCase())) {
      return HttpResponse.json(
        { email: ['Ya existe un usuario con este email.'] },
        { status: 409 },
      );
    }
    const id = `${++nextId}${nextId}${nextId}${nextId}-${nextId}${nextId}${nextId}${nextId}-${nextId}${nextId}${nextId}${nextId}-${nextId}${nextId}${nextId}${nextId}`.slice(0, 36);
    const now = new Date().toISOString();
    const created: AdminUser = {
      id,
      full_name: body.full_name.trim(),
      email: body.email.trim().toLowerCase(),
      role: body.role,
      active: body.active,
      created_at: now,
      updated_at: now,
      created_by: null,
    };
    baseUsers.push(created);
    return HttpResponse.json(created, { status: 201 });
  }),

  http.patch('/api/admin/users/:id/', async ({ params, request }) => {
    const body = (await request.json()) as AdminUserUpdate;
    const idx = baseUsers.findIndex((u) => u.id === params.id);
    if (idx < 0 || !baseUsers[idx].active) {
      return HttpResponse.json({ detail: 'No encontrado' }, { status: 404 });
    }
    const updated: AdminUser = {
      ...baseUsers[idx],
      ...(body.full_name !== undefined ? { full_name: body.full_name } : {}),
      ...(body.role !== undefined ? { role: body.role } : {}),
      ...(body.active !== undefined ? { active: body.active } : {}),
      updated_at: new Date().toISOString(),
    };
    baseUsers[idx] = updated;
    return HttpResponse.json(updated);
  }),

  http.delete('/api/admin/users/:id/', ({ params }) => {
    const idx = baseUsers.findIndex((u) => u.id === params.id);
    if (idx < 0 || !baseUsers[idx].active) {
      return HttpResponse.json({ detail: 'No encontrado' }, { status: 404 });
    }
    baseUsers[idx] = { ...baseUsers[idx], active: false };
    return new HttpResponse(null, { status: 204 });
  }),

  http.get('/api/admin/users/:id/history', ({ params }) => {
    const entries = auditLog[String(params.id)] ?? [];
    return HttpResponse.json(entries);
  }),

  http.post('/api/admin/auth/exchange', async ({ request }) => {
    const body = (await request.json()) as { fastapi_jwt: string };
    if (!body.fastapi_jwt || body.fastapi_jwt.length < 10) {
      return HttpResponse.json({ detail: 'JWT inválido' }, { status: 400 });
    }
    return HttpResponse.json({ token: 'mocked-django-token-1234567890' });
  }),
];
