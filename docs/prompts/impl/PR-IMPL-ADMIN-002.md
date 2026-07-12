# Prompt de Implementación — PR-IMPL-ADMIN-002

| Campo | Valor |
| :--- | :--- |
| ID del prompt | `PR-IMPL-ADMIN-002` |
| Título | Migración del CRUD de usuarios admin de localStorage a PostgreSQL schema `admin` + API REST FastAPI |
| Artefacto origen | ADR-0012 |
| ID origen | `ADR-0012` (§Decisión) · `FSD-UC-ADMIN-001` (§4.8 FSD_vFinal.md v1.1) · `DD-ADMIN-001` |
| Tipo de prompt | generación (backend + frontend async + migración de datos + tests) |
| Modelo recomendado | Sonnet |
| Temperatura | 0.2 |
| Versión | v0.1 |
| Fecha | 27/06/2026 |
| Autor(es) | Ing. Guillermo Mamani Chambi |
| Estado | Aprobado (pendiente de ejecución; no romper MVP vigente de PR-IMPL-ADMIN-001) |

---

## 1. Anatomía del prompt

### 1.1 Role

Eres un **desarrollador full-stack senior** especializado en FastAPI + PostgreSQL (SQLAlchemy 2.0, Alembic) + frontend TypeScript vanilla. Conoces a fondo la arquitectura hexagonal del backend BIOMED (ADR-0004), el patrón Append-Only en `edits` (ADR-0001, RN-05), y el código de `PR-IMPL-ADMIN-001` ya entregado (módulo `frontend/src/admin/userStore.ts` síncrono sobre localStorage, panel `#users-tab` en `configuracion.html`, tests Vitest con jsdom). Tu prioridad es **migrar la capa de persistencia sin romper el contrato externo** del módulo `userStore.ts` salvo el cambio síncrono→asíncrono.

### 1.2 Task

Migrar el CRUD de cuentas institucionales de `localStorage` a **PostgreSQL schema `admin`** con **API REST FastAPI** dedicada (`/api/admin/users/*`), preservando:
- El contrato externo `list/save/update/remove/validateEmail/canDelete/validateName` del módulo frontend (cambia de síncrono a asíncrono).
- La UI del panel `#users-tab` en `configuracion.html` (zero diff excepto adapter async).
- La cobertura Vitest ≥90% (RN-09) — pero ahora vía MSW + tests de integración contra TestClient FastAPI.
- El aislamiento del dominio clínico (ADR-0011) reforzado a nivel DB (schema separado, rol Postgres con privilegios mínimos).

### 1.3 Context

- **Documento fuente principal**: `docs/adr/0012-persistencia-admin-postgres.md` (decisión arquitectónica completa).
- **Diseño detallado**: `docs/design/DD-ADMIN-001.md` (origen del feature).
- **Especificación**: `docs/fsd/FSD_vFinal.md` §4.8 FSD-UC-ADMIN-001.
- **MVP vigente**: `configuracion.html` (panel `#users-tab` + UserStore IIFE localStorage), `frontend/src/admin/userStore.ts` (canónico síncrono), `frontend/tests/userStore.spec.ts` (32 tests jsdom).
- **Backend existente**:
  - FastAPI app en `backend/app/main.py` con routers por bounded context (clinical, ai, audit).
  - SQLAlchemy 2.0 + Alembic para migraciones.
  - AuthJWT con claims `role` (`analista`/`supervisor`/`admin`).
- **Reglas del proyecto que aplican**:
  - **RN-03**: No PII clínica. Las cuentas admin son PII del personal TI, no de pacientes — se documenta en ADR-0012 §Justificación.
  - **RN-05**: Append-Only en `edits` (clínica). `admin_users` es tabla **separada** con regla distinta (UPDATE/DELETE legítimos + `user_audit_log` Append-Only como contraparte).
  - **RN-06**: Segregación de funciones. El rol Postgres `admin_user_service` debe tener CERO permisos sobre schemas clínicos.
  - **RN-09**: Cobertura ≥90% en módulo `userStore.ts` (frontend) y `admin_user_service.py` (backend).
  - **AGENTS §11**: Rama de trabajo `feature/admin-postgres-migration` (no main, no release/2.0.0 directo).
- **Restricciones técnicas**:
  - Stack backend: Python 3.11+, FastAPI 0.110+, SQLAlchemy 2.0, Alembic 1.13+, Pydantic v2, AuthJWT 4.x, pytest + httpx.AsyncClient.
  - Stack frontend: TS ES2020, `fetch` nativo (no axios), MSW para tests, Vitest 1.x.
  - PostgreSQL 15 (misma instancia del sistema, schema nuevo `admin`).
  - Rate limiting: 60 req/min por admin vía middleware FastAPI.

### 1.4 Reasoning (chain-of-thought estructurado)

Sigue estos pasos en orden, validando F1→F7 según plan de implementación del ADR-0012 §Plan de implementación:

1. **F1 — Schema DB**:
   - Crear migración Alembic `0012_admin_schema.py` que cree schema `admin`, tablas `admin.users` y `admin.user_audit_log`, índices, constraints.
   - Verificar que el rol Postgres `admin_user_service` existe y tiene solo `GRANT SELECT, INSERT, UPDATE` sobre schema `admin`. Negar todo sobre `public` y schemas clínicos.
   - Test de migración: `alembic upgrade head` + `alembic downgrade -1` debe ser reversible.

2. **F2 — Backend FastAPI**:
   - Crear `backend/app/models/admin_user.py` con SQLAlchemy 2.0 `AdminUser` + `UserAuditLog` (Append-Only).
   - Crear `backend/app/schemas/admin_user.py` con Pydantic v2 (`AdminUserCreate`, `AdminUserUpdate`, `AdminUserOut`, `ValidationError`).
   - Crear `backend/app/services/admin_user_service.py` con la lógica de negocio que ahora vive en `frontend/src/admin/userStore.ts`: validación de email (regex), normalización (lowercase + trim), canDelete, soft-delete (`deactivated_at = now()`).
   - Crear `backend/app/api/v1/admin_users.py` con router FastAPI: `POST/GET/PATCH/DELETE/GET-by-email`.
   - Middleware de rate limiting 60 req/min por `sub` del JWT.
   - Tests pytest con `httpx.AsyncClient` + `TestClient` + DB de prueba (SQLite in-memory o schema dedicado).

3. **F3 — Frontend async**:
   - Reescribir `frontend/src/admin/userStore.ts` con funciones `async` que llaman a `/api/admin/users/*`. Manejar 401 (refresh token), 403 (mostrar "Sin permisos"), 404 (mostrar "Usuario no existe"), 409 (mostrar "Email duplicado" o "Ya desactivado"), 500 (mostrar "Error del servidor, reintente").
   - Actualizar `configuracion.html`: eliminar IIFE inline `window.biomed.admin`, reemplazar por `<script type="module">` que importa `frontend/src/admin/userStore.ts`. UI del panel `#users-tab` se mantiene idéntica (zero diff en HTML/CSS, solo se actualizan los handlers `renderUserTable/openEditModal/handleSave/handleDelete` para usar `await`).
   - Implementar spinners de carga en botones de "Agregar/Editar/Eliminar" durante requests.

4. **F4 — Tests MSW**:
   - Reemplazar jsdom-mocks en `frontend/tests/userStore.spec.ts` por MSW handlers que mockean `/api/admin/users/*`.
   - Añadir test de integración contra `TestClient` FastAPI en `backend/tests/test_admin_users.py`.
   - Cobertura objetivo: ≥90% en `userStore.ts` (frontend) y ≥90% en `admin_user_service.py` (backend).

5. **F5 — Migración de datos existentes**:
   - Crear `backend/scripts/migrate_localstorage_users.py` que lee `localStorage['biomed:admin:users']` desde un archivo JSON exportado por el admin inicial (UI de export en `configuracion.html` → "Exportar usuarios a JSON").
   - Script idempotente: si el email ya existe en DB, skip con warning.
   - Dry-run mode: `--dry-run` flag que imprime lo que haría sin tocar DB.

6. **F6 — Documentación**:
   - Actualizar `DD-ADMIN-001.md` §2 (Storage: localStorage → PostgreSQL schema admin) y §7 (DoD con cobertura real de F4).
   - Crear `docs/prompts/impl/PR-IMPL-ADMIN-002.md` (este archivo) y registrar en `PROMPT_MAPPING.md`.
   - Actualizar `AGENTS.md` §3 con referencia al schema admin (ya integrado en DTI §21).
   - Crear CHANGELOG.md entrada "Breaking Change: userStore async".

7. **F7 — Smoke E2E**:
   - Documentar en PR el procedimiento: alta desde navegador A → aparece en navegador B sin recargar (polling 30s o invalidación por timestamp `updated_at`).
   - Verificar auditoría: `SELECT * FROM admin.user_audit_log ORDER BY timestamp DESC LIMIT 10;` después de 5 mutaciones de prueba.

No expongas el razonamiento interno en el output final.

### 1.5 Stop condition

Detente cuando:
- `alembic upgrade head` aplica schema `admin` sin errores y es reversible (`downgrade -1` deja DB limpia).
- Los 5 endpoints REST pasan tests pytest con cobertura ≥90% en `admin_user_service.py`.
- El módulo `userStore.ts` async pasa tests MSW con cobertura ≥90%.
- El smoke test E2E F7 funciona: alta desde navegador A aparece en navegador B sin recargar.
- La auditoría registra las 5 mutaciones de prueba en `admin.user_audit_log`.
- Cero archivos clínicos (`cases`, `samples`, `edits`) son tocados.
- No se introducen archivos nuevos fuera de: `backend/app/{models,schemas,services,api/v1}/admin_*.py`, `backend/scripts/migrate_localstorage_users.py`, `backend/tests/test_admin_users.py`, `backend/alembic/versions/0012_admin_schema.py`, `frontend/src/admin/userStore.ts` (mod), `frontend/tests/userStore.spec.ts` (mod), `frontend/src/admin/msw/handlers.ts` (new).

### 1.6 Output

Formato: **bloque de código por archivo modificado/creado**, en este orden:

1. `backend/alembic/versions/0012_admin_schema.py` — migración completa reversible.
2. `backend/app/models/admin_user.py` — modelos SQLAlchemy 2.0.
3. `backend/app/schemas/admin_user.py` — schemas Pydantic v2.
4. `backend/app/services/admin_user_service.py` — lógica de negocio.
5. `backend/app/api/v1/admin_users.py` — router FastAPI con rate limiting.
6. `backend/tests/test_admin_users.py` — tests pytest + httpx.AsyncClient.
7. `frontend/src/admin/userStore.ts` — versión async con `fetch`.
8. `frontend/src/admin/msw/handlers.ts` — handlers MSW para tests.
9. `frontend/tests/userStore.spec.ts` — tests reescritos con MSW.
10. `backend/scripts/migrate_localstorage_users.py` — script de migración de datos.
11. `configuracion.html` — diff mínimo: eliminar IIFE inline, agregar `<script type="module" src="frontend/src/admin/userStore.ts">`.
12. **Reporte de cobertura** esperado (tabla con cobertura frontend + backend).

Al final, incluye:
- Lista de archivos modificados vs creados.
- Lista de archivos NO tocados (auditoría rápida).
- Snippet de comandos para correr tests localmente.

Ejemplo de output (estructura):

```text
=== ARCHIVO CREADO: backend/alembic/versions/0012_admin_schema.py ===
[código migración]

=== ARCHIVO MODIFICADO: frontend/src/admin/userStore.ts ===
[diff conceptual]

=== REPORTE DE COBERTURA ESPERADO ===
| file                              | lines | branches | funcs | statements |
|-----------------------------------|-------|----------|-------|------------|
| frontend/src/admin/userStore.ts   | 95%   | 92%      | 100%  | 95%        |
| backend/app/services/admin_user_service.py | 94% | 90%   | 100%  | 94%        |
```

---

## 2. Invariantes del prompt

- La salida **debe** preservar el contrato externo `list/save/update/remove/validateEmail/canDelete/validateName` (solo cambia síncrono→asíncrono).
- La salida **debe** crear schema `admin` separado del schema clínico. Cero permisos cruzados.
- La salida **debe** usar soft-delete (`deactivated_at`) — nunca `DELETE FROM admin.users`.
- La salida **debe** registrar toda mutación en `admin.user_audit_log` Append-Only.
- La salida **debe** alcanzar cobertura ≥90% (RN-09) tanto en frontend como backend.
- La salida **no debe** romper el MVP vigente de `PR-IMPL-ADMIN-001` (los 32 tests existentes deben seguir pasando con el adapter mockeado hasta F4, luego migrar).
- La salida **no debe** introducir un nuevo ORM ni un nuevo framework backend (SQLAlchemy 2.0 ya está en uso).
- La salida **no debe** exponer endpoints admin sin AuthJWT + RBAC `admin` verificado en middleware.
- La salida **debe** manejar errores HTTP 401/403/404/409/500 con UX clara en `configuracion.html`.
- La salida **debe** citar `ADR-0012`, `FSD-UC-ADMIN-001`, `DD-ADMIN-001`, `PR-IMPL-ADMIN-001` en comentarios del código.

## 3. Failure modes declarados

| Código | Descripción | Acción del consumidor |
| :--- | :--- | :--- |
| `E_MISSING_CONTEXT` | no se proporcionó `ADR-0012.md` o `DD-ADMIN-001.md` | abortar con error y solicitar archivos |
| `E_POLICY_CROSS_SCHEMA` | rol Postgres tiene permisos sobre schemas clínicos | rechazar y regenerar con REVOKE explícito |
| `E_POLICY_HARD_DELETE` | código hace `DELETE FROM admin.users` en vez de soft-delete | rechazar y regenerar |
| `E_POLICY_NO_AUDIT` | mutación no registra fila en `user_audit_log` | rechazar y regenerar |
| `E_POLICY_COVERAGE` | cobertura <90% detectada en CI | añadir tests hasta cumplir RN-09 |
| `E_BREAKING_UI` | diff en HTML/CSS del panel `#users-tab` mayor a 50 líneas | rechazar y refactorizar (solo adapter debe cambiar) |
| `E_RATE_LIMIT_MISSING` | endpoints admin sin rate limiting | rechazar y agregar middleware |

## 4. Guardrails

- **MUST**: ejecutar `alembic upgrade head` + `alembic downgrade -1` antes de declarar Done.
- **MUST**: ejecutar `pytest backend/tests/test_admin_users.py --cov=backend/app/services/admin_user_service.py --cov-fail-under=90` y adjuntar reporte.
- **MUST**: ejecutar `vitest run --coverage` y adjuntar reporte.
- **MUST**: smoke E2E F7 ejecutado y documentado en PR.
- **MUST NOT**: tocar tablas de los schemas clínicos (`cases`, `samples`, `edits`, `iscn_nomenclature`).
- **MUST NOT**: usar hard-delete. Toda baja es soft-delete con `deactivated_at`.
- **MUST NOT**: commitear archivos de credenciales, `.env`, o dumps de DB.
- **MUST**: registrar el prompt en `docs/PROMPT_MAPPING.md` con su salida (PM-ADMIN-002).
- **MUST**: trabajar en rama `feature/admin-postgres-migration`, abrir PR contra `release/2.0.0`.

## 5. Trazabilidad

| Origen | ID origen | Este prompt | Consumidor(es) | Artefacto generado |
| :--- | :--- | :--- | :--- | :--- |
| ADR + DD + FSD | `ADR-0012` · `DD-ADMIN-001` · `FSD-UC-ADMIN-001` | `PR-IMPL-ADMIN-002` | `dev-agent` (Claude Sonnet) | `backend/alembic/versions/0012_admin_schema.py` (new) · `backend/app/{models,schemas,services,api/v1}/admin_*.py` (new) · `frontend/src/admin/userStore.ts` (mod async) · `frontend/tests/userStore.spec.ts` (mod MSW) |

## 6. Pruebas del prompt (prompt tests)

### 6.1 Caso feliz

- **Input**: Schema `admin` creado, 0 usuarios en DB.
- **Output esperado**: Admin POST `/api/admin/users` con `{full_name, email, role, active}` → 201 con usuario creado. GET `/api/admin/users` → 200 con array de 1. Mismo admin en otro navegador ve el usuario sin recargar.

### 6.2 Caso borde (soft-delete idempotente)

- **Input**: Usuario existe con `deactivated_at = NULL`.
- **Output esperado**: DELETE `/api/admin/users/{id}` → 204. Nueva fila en `user_audit_log` con `action='deactivate'`. GET lista excluye al usuario (filtro `WHERE deactivated_at IS NULL`). DELETE otra vez → 409 "Usuario ya desactivado".

### 6.3 Caso adversarial (privilegios cruzados)

- **Input**: Token JWT con `role='analista'` intenta POST `/api/admin/users`.
- **Output esperado**: 403 Forbidden. Cero filas en `admin.users`. Cero filas en `admin.user_audit_log` (la auditoría solo registra intentos exitosos por el actor).

### 6.4 Caso adversarial (concurrencia)

- **Input**: Dos admins hacen POST simultáneo con mismo email.
- **Output esperado**: UNO gana con 201, el otro recibe 409 "Email ya registrado" por violation de `UNIQUE` constraint a nivel DB. Ambos requests registran fila en `user_audit_log` (uno con `action='create'`, el otro con `action='duplicate_attempt'` si se decide loguear).

## 7. Instrumentación

- **Tests backend**: `pytest@8.x` + `pytest-asyncio` + `pytest-cov` + `httpx.AsyncClient`.
- **Tests frontend**: `vitest@1.x` + `@vitest/coverage-v8@1.x` + `msw@2.x`.
- **Métricas**:
  - `coverage.lines ≥ 90%`, `coverage.branches ≥ 90%`, `coverage.funcs ≥ 90%`, `coverage.statements ≥ 90%` (RN-09) en `userStore.ts` (frontend) y `admin_user_service.py` (backend).
  - `test_count ≥ 25` (12 frontend + 13 backend como mínimo).
  - `audit_log_rows_after_smoke = 5` (las 5 mutaciones del F7 registradas).
  - `cross_schema_privileges = 0` (revocación verificada con `information_schema.role_table_grants`).
- **Migración DB**: `alembic upgrade head` + `alembic downgrade -1` ambos exit code 0.

## 8. Versionado

| Versión | Fecha | Autor | Cambio | Modelo validado |
| :--- | :--- | :--- | :--- | :--- |
| v0.1 | 27/06/2026 | G. Mamani | creación inicial | Sonnet |

## 9. Revisión humana

| Revisor | Fecha | Veredicto | Notas |
| :--- | :--- | :--- | :--- |
| G. Mamani | 27/06/2026 | aprobado | ADR-0012 consistente con DD-ADMIN-001 y FSD-UC-ADMIN-001 v1.1 |

---

## Plantilla express (copiar y pegar)

```
# Role
Desarrollador full-stack senior (FastAPI + SQLAlchemy 2.0 + TS vanilla) con criterio de migración incremental sin breaking changes.

# Task
Migrar CRUD de usuarios admin de localStorage a PostgreSQL schema admin + API REST FastAPI + soft-delete + user_audit_log Append-Only. Frontend pasa a async con fetch.

# Context
- ADR: docs/adr/0012-persistencia-admin-postgres.md (decisión completa)
- DD: docs/design/DD-ADMIN-001.md
- FSD: docs/fsd/FSD_vFinal.md §4.8 FSD-UC-ADMIN-001
- MVP vigente: frontend/src/admin/userStore.ts síncrono, configuracion.html IIFE, 32 tests jsdom pasando
- Backend: FastAPI 0.110, SQLAlchemy 2.0, Alembic, AuthJWT
- Frontend: TS ES2020, fetch nativo, MSW para tests
- Reglas: RN-03 PII no clínica, RN-05 Append-Only en edits (no en admin_users), RN-06 segregación via schema separado, RN-09 cobertura ≥90%

# Reasoning
1. F1: Migración Alembic crea schema admin + users + user_audit_log
2. F2: Backend FastAPI con router admin_users + service + tests pytest
3. F3: Frontend userStore.ts async con fetch + manejo de errores HTTP
4. F4: Tests MSW reemplazando jsdom + tests httpx.AsyncClient
5. F5: Script migración datos existentes desde localStorage JSON
6. F6: Docs: DD §2, PROMPT_MAPPING PM-ADMIN-002, CHANGELOG breaking change
7. F7: Smoke E2E cross-browser

# Stop condition
Detente cuando: schema admin reversible + endpoints pasan tests ≥90% + userStore async pasa MSW ≥90% + smoke F7 funciona + cero permisos cross-schema + cero breaking UI >50 líneas.

# Output
Bloques de código por archivo:
1. backend/alembic/versions/0012_admin_schema.py
2. backend/app/models/admin_user.py + schemas/admin_user.py + services/admin_user_service.py + api/v1/admin_users.py
3. backend/tests/test_admin_users.py
4. frontend/src/admin/userStore.ts (async)
5. frontend/src/admin/msw/handlers.ts + frontend/tests/userStore.spec.ts (MSW)
6. backend/scripts/migrate_localstorage_users.py
7. configuracion.html (diff mínimo: eliminar IIFE, agregar <script type="module">)
8. Reporte cobertura frontend + backend

# Invariants
- Preservar contrato externo list/save/update/remove/validateEmail/canDelete/validateName (solo síncrono→async)
- Schema admin separado del clínico, cero permisos cruzados
- Soft-delete (deactivated_at), nunca DELETE FROM
- Toda mutación registra en user_audit_log Append-Only
- Cobertura ≥90% frontend + backend (RN-09)
- No romper MVP vigente de PR-IMPL-ADMIN-001
- AuthJWT + RBAC admin obligatorio
- Manejar 401/403/404/409/500 con UX clara

# Failure modes
- E_MISSING_CONTEXT: abortar
- E_POLICY_CROSS_SCHEMA: rechazar (REVOKE explícito)
- E_POLICY_HARD_DELETE: rechazar (soft-delete obligatorio)
- E_POLICY_NO_AUDIT: rechazar (auditoría obligatoria)
- E_POLICY_COVERAGE: añadir tests
- E_BREAKING_UI: rechazar (diff HTML >50 líneas)
- E_RATE_LIMIT_MISSING: rechazar (middleware obligatorio)
```