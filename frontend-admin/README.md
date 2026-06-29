# frontend-admin

Bounded context **admin** del BIOMED UMSS Intelligent Karyotyping Platform.
Stack: React 18 + Vite 5 + TypeScript 5 + MSW 2 + Vitest 1 (v8 coverage).

Decisión arquitectónica: **ADR-0013** · Documento de diseño: **DD-ADMIN-001**.
Auth bridge con FastAPI (clinical): ver `docs/AUTH_BRIDGE.md`.

## Estado del plan (ADR-0013 §Decisión)

| Fase | Descripción | Estado |
|---|---|---|
| F0 | Diseño auth_bridge (compartido HS256) | ✅ |
| F1 | Bootstrap backend-admin Django+DRF | ✅ |
| F2 | CRUD AdminUser + audit (backend) | ✅ |
| F3 | Endpoint `/history` | ✅ (F8 pendiente integración real) |
| **F4** | **Bootstrap frontend-admin** | **✅ este PR** |
| **F5** | **Componentes React** | **✅ este PR** |
| **F6** | **Tests Vitest+MSW con RN-09 ≥90%** | **🟡 parcial — F6.1 client+componentes ✅; F6.2 E2E pendiente** |
| F7 | Auth_bridge real FastAPI↔Django | ⏳ |
| F8 | docker-compose | ⏳ |
| F9 | Smoke E2E | ⏳ |
| F10 | Docs (AGENTS §3, CHANGELOG) | ⏳ |

## Scripts

```bash
npm install
npm run dev          # http://localhost:5173 (proxy /api → backend :8001)
npm test             # vitest run (sin watch)
npm run test:coverage
npm run build        # tsc + vite build
```

## Estructura

```
frontend-admin/
├── src/
│   ├── admin/
│   │   ├── api/adminClient.ts          # fetch wrapper + AdminApiException
│   │   ├── components/                 # AdminUsersPanel, UserTable, UserForm, ...
│   │   ├── msw/                        # handlers + server (node) + worker (browser)
│   │   ├── state/adminUsersStore.tsx   # reducer puro + Context
│   │   └── types/adminUser.ts          # espejo del serializer backend
│   ├── App.tsx
│   ├── main.tsx
│   ├── index.css
│   └── vite-env.d.ts
├── tests/
│   ├── setup.ts                        # MSW server.listen + jest-dom
│   ├── adminClient.spec.ts             # cobertura de los 7 endpoints + errores
│   ├── adminUsersStore.spec.tsx        # reducer + provider
│   └── components/
│       ├── atoms.spec.tsx              # RoleBadge, StatusToggle, EmptyState
│       ├── userForm.spec.tsx           # validaciones inline
│       └── adminUsersPanel.spec.tsx    # integración con MSW
└── public/
```

## Endpoints consumidos (espejo de backend-admin)

| Método | Ruta | Códigos esperados |
|---|---|---|
| GET | `/api/admin/users/` | 200, 401, 500 |
| GET | `/api/admin/users/{id}/` | 200, 401, 404 |
| POST | `/api/admin/users/` | 201, 400, 401, 403, 409 |
| PATCH | `/api/admin/users/{id}/` | 200, 400, 401, 403, 404 |
| DELETE | `/api/admin/users/{id}/` | 204, 401, 403, 404 |
| GET | `/api/admin/users/{id}/history` | 200, 401, 403, 404 |
| POST | `/api/admin/auth/exchange` | 200, 400, 401 |

## Cobertura RN-09 (≥90%)

`vitest.config.ts` aplica thresholds `lines/branches/functions/statements = 90` para
`src/admin/**/*.{ts,tsx}` (excluye `types/` y `msw/` por ser contratos/fixtures).

Correr:
```bash
npm run test:coverage
```

## Notas de seguridad (RN-03, RN-09)

- **RN-03** (zero PII): MSW handlers usan emails del dominio `@biomed.umss.bo` (ficticios),
  no se transmite PII real en dev ni en tests.
- **RN-09** (cobertura ≥90%): aplicado vía vitest v8 con thresholds. Tipos (`src/admin/types/`)
  excluidos por ser contratos espejo del serializer.