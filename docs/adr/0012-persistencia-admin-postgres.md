---
id: ADR-0012
title: Persistencia de Usuarios Administrador en PostgreSQL con API Dedicada
date: 2026-06-27
status: accepted
supersedes: PR-IMPL-ADMIN-001 (alcance MVP localStorage)
related: [ADR-0011, ADR-0001, ADR-0004]
fase: post-MVP
---

# ADR 0012: Persistencia de Usuarios Administrador en PostgreSQL con API Dedicada

## Contexto

`PR-IMPL-ADMIN-001` (alcance MVP) implementó el CRUD de cuentas institucionales sobre `localStorage` del navegador. Esta decisión fue deliberada y documentada en `DD-ADMIN-001.md` §1.3, `PR-IMPL-ADMIN-001.md` §2 y `FSD-UC-ADMIN-001` §4.8 con la justificación de **aislar al Administrador TI del flujo clínico** (ADR-0011, RN-06 segregación de funciones).

Sin embargo, al pasar el MVP a un entorno multi-institución (módulo FHIR/REST + acceso concurrente de N admins TI desde distintas terminales), la persistencia en `localStorage` exhibe cuatro limitaciones que bloquean el despliegue productivo:

| # | Limitación | Impacto | Detonante |
|:-:|:---|:---|:---|
| L1 | **Visibilidad por dispositivo** | Cambios de un admin en su laptop no se reflejan en la laptop del supervisor TI hasta que cada uno edite manualmente | 2+ admins TI simultáneos |
| L2 | **Pérdida por limpieza de caché** | Un usuario institucional se borra si el navegador limpia storage (IT support, navegador nuevo, modo privado) | Onboarding de nuevos admins |
| L3 | **Sin auditoría centralizada** | No se puede responder "¿quién desactivó la cuenta X el día Y?" porque los cambios viven en el navegador del actor | Auditoría Ley 164 (BRD §6) |
| L4 | **Sin enforcement de unicidad cross-institución** | Dos laptops pueden tener el mismo email registrado si trabajaron desconectadas | Migración a multi-tenant |

ADR-0011 establece que el dominio `admin` está **separado** del dominio clínico. PostgreSQL ya es la base de datos del sistema (ADR-0001 §21 DTI), pero las tablas clínicas (`cases`, `samples`, `edits`, ISCN) son Append-Only por RN-05. La tabla `admin_users` es el **primer caso** de tabla PostgreSQL con ciclo CRUD completo legítimo (UPDATE/DELETE permitidos para soft-delete y desactivación). Esto requiere justificación arquitectónica explícita.

## Decisión

Migrar la persistencia del CRUD de cuentas institucionales (UserStore) de `localStorage` a una **API REST dedicada** sobre **PostgreSQL 15**, manteniendo intacta la separación del dominio clínico (ADR-0011). El cambio se aplica solo a la capa de persistencia; la UI (`#users-tab` en `configuracion.html`) y el módulo `frontend/src/admin/userStore.ts` conservan su contrato externo (`list/save/update/remove/validateEmail/canDelete/validateName`) — solo cambia el adapter.

### Componentes nuevos

| Componente | Responsabilidad | Stack |
|:---|:---|:---|
| `admin_users` table | Almacén único de cuentas institucionales | PostgreSQL 15 (misma instancia, schema distinto) |
| `POST /api/admin/users` | Alta de cuenta (solo admin) | FastAPI + AuthJWT |
| `GET /api/admin/users` | Listado paginado | FastAPI + AuthJWT |
| `PATCH /api/admin/users/{id}` | Modificación parcial (rol, active, full_name) | FastAPI + AuthJWT + RBAC `admin` |
| `DELETE /api/admin/users/{id}` | Soft-delete (setea `deactivated_at`) | FastAPI + AuthJWT + RBAC `admin` |
| `GET /api/admin/users/email/{email}` | Validación de unicidad (excluye `id`) | FastAPI + AuthJWT |
| `backend/app/services/admin_user_service.py` | Lógica de negocio (validación email, canDelete, normalización) | Python 3.11+, Pydantic v2 |
| `backend/app/models/admin_user.py` | Modelo SQLAlchemy 2.0 con `deactivated_at` (soft-delete) | SQLAlchemy 2.0 |
| `frontend/src/admin/userStore.ts` (mod) | Reemplazar `localStorage` por `fetch` a `/api/admin/users/*` con manejo de errores 401/403/404/500 | TypeScript ES2020, `fetch` nativo |
| `frontend/tests/userStore.spec.ts` (mod) | Reemplazar jsdom-mocks por MSW (Mock Service Worker) + tests de integración contra TestClient FastAPI | Vitest + MSW |

### Esquema `admin_users`

```sql
CREATE SCHEMA IF NOT EXISTS admin;

CREATE TABLE admin.users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name       VARCHAR(80) NOT NULL CHECK (length(trim(full_name)) BETWEEN 3 AND 80),
    email           VARCHAR(255) NOT NULL CHECK (email ~* '^[^\s@]+@[^\s@]+\.[^\s@]+$'),
    role            VARCHAR(16) NOT NULL CHECK (role IN ('analista', 'supervisor', 'admin')),
    active          BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    deactivated_at  TIMESTAMPTZ,           -- soft-delete; NULL = cuenta activa
    created_by      UUID REFERENCES admin.users(id),  -- quién la dio de alta
    CONSTRAINT admin_users_email_unique UNIQUE (email)
);

CREATE INDEX admin_users_active_idx ON admin.users (active) WHERE deactivated_at IS NULL;
CREATE INDEX admin_users_role_idx ON admin.users (role);
```

**Nota crítica de aislamiento:** la tabla vive en schema `admin`, NO en schema `public` ni en el schema donde están `cases/samples/edits`. Esto refuerza ADR-0011 a nivel de DB: el rol `admin_user_service` de Postgres puede existir sin permisos de lectura sobre schemas clínicos.

### Justificación del modelo Append-Only *parcial*

A diferencia de `edits` (RN-05: Append-Only estricto), `admin_users` admite UPDATE y DELETE **pero**:

- **UPDATE** solo modifica `full_name/role/active/updated_at`. El `created_at` y `created_by` son inmutables (regla de tabla, no de API).
- **DELETE** es **soft-delete** obligatorio: nunca `DELETE FROM admin.users WHERE id = ?`, siempre `UPDATE admin.users SET deactivated_at = now() WHERE id = ?`. El endpoint `DELETE /api/admin/users/{id}` rechaza con 409 si ya está desactivado.
- **Toda mutación** registra fila en `admin.user_audit_log` (tabla Append-Only hermana), con: `actor_id`, `action` (`create/update/deactivate/reactivate`), `target_id`, `old_values_jsonb`, `new_values_jsonb`, `ip_address`, `timestamp`. Esto resuelve L3 sin romper RN-05 (porque vive en schema `admin`, no clínico).

### Tensión con reglas del proyecto y cómo se resuelve

| Regla | Tensión | Resolución |
|:---|:---|:---|
| **RN-03 (no PII)** | `full_name` y `email` son PII del personal TI | `admin_users` **no contiene PII de pacientes**. La anonimización CHN (ADR-0003) aplica al pipeline clínico, no a este dominio. Se documenta en este ADR. |
| **RN-05 (Append-Only en `edits`)** | Aquí se hace UPDATE/DELETE | `edits` (clínica) sigue Append-Only. `admin_users` es tabla separada con regla distinta documentada. Se agrega `user_audit_log` Append-Only como contraparte. |
| **RN-06 (segregación)** | ¿El admin TI necesita permisos DB sobre `cases`? | No. El rol Postgres `admin_user_service` solo tiene `GRANT SELECT, INSERT, UPDATE` sobre `admin.users` y `admin.user_audit_log`. Cero permisos sobre `public` o schema clínico. |
| **ADR-0011 (separación de funciones)** | ¿Esto rompe el aislamiento? | Lo refuerza. Antes el aislamiento era "depende del navegador del admin". Ahora es "schema Postgres dedicado + rol DB con privilegios mínimos". |

## Justificación

### Por qué PostgreSQL y no otro storage

- Ya es la base del sistema (ADR-0001). No introduce nueva dependencia operativa.
- ACID transaccional: garantiza unicidad de email sin race conditions (L4).
- Soporte nativo de UUID v4 + JSONB (para `user_audit_log.old_values_jsonb`).
- Réplicas de lectura + backups PITR ya configurados (DTI §14).

### Por qué API dedicada y no acoplar al módulo `cases`

- Hexagonal (ADR-0004): el bounded context `admin` no debe compartir endpoints con `cases` ni `samples`.
- Endpoints `/api/admin/users/*` viven en router FastAPI separado, montado solo cuando el JWT contiene `role=admin`.
- Tests de integración pueden ejercitar el router admin sin tocar la DB clínica.

### Por qué soft-delete y no hard-delete

- Cumple L3 (auditoría "¿quién desactivó X?").
- Permite restaurar cuentas desactivadas por error (operación legítima de soporte TI).
- La columna `deactivated_at IS NULL` es la fuente de verdad para "¿está activa?". El endpoint `GET /api/admin/users` filtra `WHERE deactivated_at IS NULL` por defecto.

### Por qué ahora y no después

- El MVP ya está desplegado en 1 institución (sin usar el feature en producción todavía).
- La carga de migración de datos existentes es despreciable: el MVP no se ha usado con datos reales, solo smoke tests con emails `*.test@biomed.local`.
- Esperar a multi-institución obliga a hacer la migración bajo presión, con datos reales en `localStorage` que ya no se pueden recuperar tras limpieza de caché.

## Consecuencias

### Positivas

- L1 resuelto: cualquier admin ve los mismos datos en tiempo real.
- L2 resuelto: cambios sobreviven a limpieza de caché.
- L3 resuelto: `user_audit_log` Append-Only responde "¿quién hizo qué?" durante 3 años (alineado con política de retención Ley 164).
- L4 resuelto: `UNIQUE` constraint a nivel DB.
- Refuerza ADR-0011 con **separación física** (schema Postgres dedicado + rol DB con privilegios mínimos), no solo lógica.
- Habilita integración con LDAP institucional futuro (mismo endpoint, distinto adapter de autenticación).

### Negativas

- Nueva superficie de ataque: 5 endpoints REST adicionales. Mitigación: AuthJWT obligatorio + RBAC `admin` verificado en middleware FastAPI + rate limiting 60 req/min por admin.
- Tests más complejos: el spec actual con jsdom-mocks se reemplaza por MSW + tests de integración contra TestClient. Coste estimado: 8h adicionales de implementación de tests.
- Migración del código frontend: el módulo `userStore.ts` cambia de síncrono a asíncrono. Todos los handlers de UI (`renderUserTable`, `openEditModal`, `handleSave`) deben manejar `Promise`. Esto **rompe el contrato de retorno** del módulo — actualización Breaking-Change en CHANGELOG.
- Latencia de red: pasar de 0ms (localStorage) a ~50-200ms (DB local). La UI debe mostrar spinner durante `save/update/remove` (no solo en `list`).
- Nuevo ADR-0013 probable para documentar el rate limiting y la estrategia de autenticación de los endpoints admin (o se hace constar aquí como §anexa).

### Neutras

- La UI HTML/CSS del panel `#users-tab` no cambia (zero diff en `configuracion.html` excepto la implementación del adapter).
- El contrato externo del módulo `userStore.ts` (`list/save/update/remove/validateEmail/canDelete/validateName`) se mantiene. Solo cambia de síncrono a asíncrono.
- `vitest.config.ts` y `package.json` añaden MSW como devDependency.

## Plan de implementación

### Fases

| Fase | Alcance | Esfuerzo | Bloqueante |
|:-:|:---|:---|:---|
| **F1** | Migración DB: schema `admin`, tabla `users`, `user_audit_log`, índices, constraints | 4h | Sí (precondición para API) |
| **F2** | Backend FastAPI: `admin_user_service.py` + router + tests pytest | 8h | F1 |
| **F3** | Frontend: `userStore.ts` async con `fetch` + manejo de errores HTTP | 4h | F2 (necesita endpoints para testear) |
| **F4** | Tests MSW reemplazando jsdom-mocks | 4h | F3 |
| **F5** | Migración de datos existentes (si los hay): script one-shot que lee `localStorage` del navegador del admin inicial y siembra `admin.users`. Aceptar que datos creados después de F3 se pierden si el admin no exporta manualmente | 2h | F3 |
| **F6** | Documentación: actualizar `DD-ADMIN-001.md` §2 (Storage) y §7 (DoD), agregar `PR-IMPL-ADMIN-002.md` y registrar en `PROMPT_MAPPING.md`, actualizar `AGENTS.md` §3 con referencia al schema admin | 2h | F4 |
| **F7** | Smoke E2E manual: alta desde navegador A → aparece en navegador B sin recargar | 1h | F5 |

**Total estimado:** 25h (≈ 3 sprints de 8h).

### Riesgos y mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|:---|:---:|:---:|:---|
| Pérdida de datos en migración (F5) | Media | Alto | Script de migración dry-run + UI export/import JSON antes de F3 |
| Performance de la API en instituciones con 500+ admins | Baja | Medio | Índice `(active)` + paginación cursor-based (`LIMIT 50 OFFSET cursor`) |
| Divergencia entre `userStore.ts` canónico (TS) y IIFE inline en `configuracion.html` | Alta | Bajo | Misma política de "MANTENER 1:1" documentada en `configuracion.html` línea ~1376. Al pasar a async, el IIFE inline se elimina y solo queda el módulo TS cargado por `<script type="module">` |
| Auditoría incompleta por bypass de la API (UPDATE directo a DB) | Baja | Alto | REVOKE privilegios directos sobre `admin.users` para todos los roles excepto `admin_user_service`. Solo el servicio FastAPI puede mutar. |

## Alternativas evaluadas

### A1. Mantener `localStorage` + agregar sync con BroadcastChannel
- **Pro:** Cero backend.
- **Contra:** No resuelve L2 (limpieza de caché), no resuelve L3 (auditoría), no resuelve L4 (multi-institución). Solo L1 parcial.
- **Rechazado** porque L2/L3/L4 son bloqueantes para producción.

### A2. Migrar a SQLite local del navegador (sql.js / WASM)
- **Pro:** Sigue siendo local-first, sin backend.
- **Contra:** No resuelve ninguno de L1-L4 (es el mismo modelo que `localStorage` con más bytes).
- **Rechazado** por la misma razón.

### A3. Backend pero en MongoDB o Firestore
- **Pro:** Schemaless, fácil de evolucionar.
- **Contra:** El resto del sistema usa PostgreSQL (ADR-0001). Introducir segundo motor de DB aumenta complejidad operativa (backups, monitoring, migraciones).
- **Rechazado** por consistencia arquitectónica.

### A4. (Aceptada) PostgreSQL + API REST FastAPI
- Ya descrita en §Decisión.

## Trazabilidad

- **Sube a:** BRD §6 (auditoría Ley 164) → MRD-13 (multi-institución) → FSD §4.8 (FSD-UC-ADMIN-001) → DD-ADMIN-001 → ADR-0011 → **este ADR-0012**.
- **Genera:** `PR-IMPL-ADMIN-002` (prompt de implementación backend + frontend async).
- **Dependencias:** ADR-0001 (PostgreSQL ya desplegado), ADR-0004 (hexagonal: bounded context admin separado), ADR-0011 (separación de dominio).
- **Impacto:** DTI §21 (este ADR entra), AGENTS.md §5 (entrada nueva en tabla), DD-ADMIN-001 §2 (Storage cambia de localStorage a PostgreSQL).

## Notas

- Este ADR **no reemplaza** el alcance MVP de `PR-IMPL-ADMIN-001`. El MVP es correcto y se mantiene como está hasta que F1-F7 se ejecuten. No se solicita refactor inmediato del código ya entregado.
- La rama de trabajo es `feature/admin-postgres-migration` (no `main`, no `release/2.0.0` directo — restricción AGENTS §11).
- El ADR-0013 (rate limiting + autenticación de endpoints admin) se redactará durante F2 si surge la necesidad; por ahora la estrategia "AuthJWT + RBAC + 60 req/min" se documenta en este ADR como compromiso.
