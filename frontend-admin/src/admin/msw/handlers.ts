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

/**
 * Perfil mock mutable por userId (1:1 con el User logueado).
 * DD-ADMIN-002 P1: usado por los handlers GET/PATCH /api/admin/me/profile/.
 * Reset por test: server.resetHandlers() no lo limpia porque vive a scope
 * de módulo; el `resetMockData()` que ya existe debe re-asignarlo desde
 * `initialProfile` (ver abajo).
 */
interface MockProfile {
  id: string;
  full_name: string;
  email: string;
  specialty: string;
  professional_license: string;
  phone: string;
  location: string;
  avatar_url: string;
  updated_at: string;
  /** P2 — DD-ADMIN-002 §3.2. */
  two_factor_enabled: boolean;
}

const initialProfile: MockProfile = {
  id: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
  full_name: 'María García López',
  email: 'maria.garcia@biomed.umss.bo',
  specialty: 'Citogenética Clínica',
  professional_license: 'MED-4452-BO',
  phone: '+591 2 2154847',
  location: 'UMSS · Hospital del Norte',
  avatar_url: '',
  updated_at: '2026-06-15T10:00:00Z',
  two_factor_enabled: false,
};

const mockProfiles: Record<string, MockProfile> = { '1': { ...initialProfile } };

/**
 * Estado mock de 2FA (P2 — DD-ADMIN-002 §3.4). MSW no implementa TOTP real
 * (no hay librería cliente): /2fa/setup/ genera un secret+QR fijo y
 * /2fa/toggle/ acepta un código mágico ('123456') como "válido" — el
 * backend real sí valida contra pyotp/RFC 6238, esto es solo para que la
 * UI de demo pueda ejercitar el flujo completo sin backend.
 */
const MOCK_VALID_TOTP_CODE = '123456';
const MOCK_TOTP_SECRET = 'JBSWY3DPEHPK3PXP';
// PNG 1x1 transparente en base64 — suficiente para <img> renderizar sin 404.
const MOCK_QR_CODE_B64 =
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=';
let mockTwoFactorSetupPending = false;
/** Contraseña actual "conocida" por el mock — usada por /me/password/. */
const MOCK_CURRENT_PASSWORD = 'CurrentPass1';

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

// ===========================================================================
// ADR-0017 — Login unificado /api/auth/*
// ===========================================================================

interface DemoAccount {
  email: string;
  password: string;
  role: 'admin' | 'analista' | 'supervisor';
  full_name: string | null;
}

/** Cuentas demo — únicas credenciales que aceptan /api/auth/login/ en MSW. */
const DEMO_ACCOUNTS: DemoAccount[] = [
  { email: 'demo_admin@biomed.umss.bo', password: 'demo12345', role: 'admin', full_name: 'Demo Admin' },
  { email: 'demo_analista@biomed.umss.bo', password: 'demo12345', role: 'analista', full_name: 'Demo Analista' },
  { email: 'demo_supervisor@biomed.umss.bo', password: 'demo12345', role: 'supervisor', full_name: 'Demo Supervisor' },
];

let tokenCounter = 0;
/** access/refresh token → cuenta demo dueña de ese token, para que /me/ y el
 * rotado de /refresh/ devuelvan SIEMPRE el usuario realmente logueado (no
 * un admin hardcodeado) — mismo comportamiento que el backend real. */
let accessTokenOwners = new Map<string, DemoAccount>();
let refreshTokenOwners = new Map<string, DemoAccount>();

/** Fabrica un JWT con forma válida (header.payload.signature) para que authClient.decodeExp() lo lea. */
function makeFakeJwt(expSecondsFromNow: number): string {
  const header = btoa(JSON.stringify({ alg: 'none', typ: 'JWT' }));
  const payload = btoa(
    JSON.stringify({ exp: Math.floor(Date.now() / 1000) + expSecondsFromNow, jti: `${tokenCounter++}` }),
  );
  return `${header}.${payload}.mock-signature`;
}

function issueTokens(account: DemoAccount): { access: string; refresh: string } {
  const access = makeFakeJwt(30 * 60);
  const refresh = makeFakeJwt(24 * 60 * 60);
  accessTokenOwners.set(access, account);
  refreshTokenOwners.set(refresh, account);
  return { access, refresh };
}

/** Restaura la base de datos mock al estado inicial. Tests lo llaman en beforeEach. */
export function resetMockData(): void {
  nextId = 4;
  baseUsers = initialUsers.map((u) => ({ ...u }));
  // mockProfiles también vive a scope de módulo (DD-ADMIN-002 P1): re-asignar
  // desde `initialProfile` para que cada test vea el estado original.
  mockProfiles['1'] = { ...initialProfile };
  mockTwoFactorSetupPending = false;
  auditLog = Object.fromEntries(
    Object.entries(initialAuditLog).map(([k, v]) => [k, v.map((e) => ({ ...e }))]),
  );
  accessTokenOwners = new Map<string, DemoAccount>();
  refreshTokenOwners = new Map<string, DemoAccount>();
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

  // ===========================================================================
  // DD-ADMIN-002 P1 — /api/admin/me/profile/
  // ===========================================================================
  // mockProfiles está declarado a scope de módulo (ver arriba) para que
  // GET y PATCH compartan estado mutable entre handlers.

  http.get('/api/admin/me/profile/', () => {
    // En demo MSW siempre devolvemos el perfil del userId=1.
    return HttpResponse.json(mockProfiles['1']);
  }),

  http.patch('/api/admin/me/profile/', async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    // Validación mock: full_name 3-80, email formato básico
    if (typeof body.full_name === 'string' &&
        (body.full_name.length < 3 || body.full_name.length > 80)) {
      return HttpResponse.json(
        { full_name: ['Nombre 3-80 caracteres'] },
        { status: 400 },
      );
    }
    if (typeof body.email === 'string' && !/^[^@]+@[^@]+\.[^@]+$/.test(body.email)) {
      return HttpResponse.json({ email: ['Email inválido'] }, { status: 400 });
    }
    if (typeof body.phone === 'string' && body.phone !== '' &&
        !/^\+?[\d\s\-()]{6,30}$/.test(body.phone)) {
      return HttpResponse.json({ phone: ['Teléfono inválido'] }, { status: 400 });
    }
    const current = mockProfiles['1'];
    const updated = {
      ...current,
      ...Object.fromEntries(
        Object.entries(body).filter(([, v]) => v !== undefined),
      ),
      updated_at: new Date().toISOString(),
    };
    mockProfiles['1'] = updated as typeof current;
    return HttpResponse.json(updated);
  }),

  // ===========================================================================
  // DD-ADMIN-002 P2 — /api/admin/me/password/ y /api/admin/me/2fa/*
  // ===========================================================================

  http.post('/api/admin/me/password/', async ({ request }) => {
    const body = (await request.json()) as { current?: string; new?: string; confirm?: string };
    if (body.current !== MOCK_CURRENT_PASSWORD) {
      return HttpResponse.json({ current: ['Contraseña actual incorrecta'] }, { status: 400 });
    }
    if (body.new !== body.confirm) {
      return HttpResponse.json({ confirm: ['No coincide con la nueva contraseña'] }, { status: 400 });
    }
    const pw = body.new ?? '';
    if (pw.length < 12 || !/[A-Z]/.test(pw) || !/[0-9]/.test(pw)) {
      return HttpResponse.json(
        { new: ['Mínimo 12 caracteres, 1 mayúscula, 1 dígito'] },
        { status: 400 },
      );
    }
    return HttpResponse.json({ detail: 'Contraseña actualizada' });
  }),

  http.post('/api/admin/me/2fa/setup/', () => {
    mockTwoFactorSetupPending = true;
    return HttpResponse.json({ secret: MOCK_TOTP_SECRET, qr_code_b64: MOCK_QR_CODE_B64 });
  }),

  http.post('/api/admin/me/2fa/toggle/', async ({ request }) => {
    const body = (await request.json()) as { enabled?: boolean; code?: string };
    if (body.enabled && !mockTwoFactorSetupPending && !mockProfiles['1'].two_factor_enabled) {
      return HttpResponse.json(
        { code: ['No hay 2FA configurado. Ejecute el setup primero.'] },
        { status: 400 },
      );
    }
    if (body.code !== MOCK_VALID_TOTP_CODE) {
      return HttpResponse.json({ code: ['Código de verificación inválido'] }, { status: 400 });
    }
    mockProfiles['1'].two_factor_enabled = Boolean(body.enabled);
    return HttpResponse.json({ two_factor_enabled: mockProfiles['1'].two_factor_enabled });
  }),

  // ===========================================================================
  // ADR-0017 — Login unificado /api/auth/*
  // ===========================================================================

  http.post('/api/auth/login/', async ({ request }) => {
    const body = (await request.json()) as { email?: string; password?: string };
    const account = DEMO_ACCOUNTS.find(
      (a) => a.email === body.email && a.password === body.password,
    );
    if (!account) {
      return HttpResponse.json({ detail: 'Credenciales inválidas' }, { status: 401 });
    }
    const { access, refresh } = issueTokens(account);
    return HttpResponse.json({
      access,
      refresh,
      role: account.role,
      email: account.email,
      full_name: account.full_name,
    });
  }),

  http.post('/api/auth/logout/', async ({ request }) => {
    const body = (await request.json()) as { refresh?: string };
    if (!body.refresh) {
      return HttpResponse.json({ detail: 'refresh requerido' }, { status: 400 });
    }
    if (!refreshTokenOwners.has(body.refresh)) {
      return HttpResponse.json({ detail: 'Token inválido' }, { status: 400 });
    }
    refreshTokenOwners.delete(body.refresh);
    return new HttpResponse(null, { status: 205 });
  }),

  http.post('/api/auth/refresh/', async ({ request }) => {
    const body = (await request.json()) as { refresh?: string };
    const account = body.refresh ? refreshTokenOwners.get(body.refresh) : undefined;
    if (!account) {
      return HttpResponse.json({ detail: 'Token is invalid or expired' }, { status: 401 });
    }
    // Rotación: el refresh usado se invalida, se emite uno nuevo para la MISMA cuenta.
    refreshTokenOwners.delete(body.refresh as string);
    const { access, refresh } = issueTokens(account);
    return HttpResponse.json({ access, refresh });
  }),

  http.get('/api/auth/me/', ({ request }) => {
    const auth = request.headers.get('Authorization');
    const token = auth?.startsWith('Bearer ') ? auth.slice('Bearer '.length) : null;
    const account = token ? accessTokenOwners.get(token) : undefined;
    if (!account) {
      return HttpResponse.json({ detail: 'Authentication credentials were not provided.' }, { status: 401 });
    }
    return HttpResponse.json({
      email: account.email,
      role: account.role,
      full_name: account.full_name,
      username: account.email,
    });
  }),
];
