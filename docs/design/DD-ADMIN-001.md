---
id: DD-ADMIN-001
titulo: "Rol de Administrador Institucional — Tab Usuarios (React + Django REST + PostgreSQL schema admin)"
producto: "BIOMED UMSS — Intelligent Karyotyping Platform"
grupo: "G04"
fsd_uc:
  - "FSD-UC-ADMIN-001"
prd_refs:
  - "PRD-REQ-013"
adrs:
  - "ADR-0011"
  - "ADR-0012"
  - "ADR-0013"
prompts:
  - "PR-IMPL-ADMIN-001"
  - "PR-IMPL-ADMIN-002"
  - "PR-IMPL-ADMIN-003"
release: "release/2.0.0"
status: aprobado
fecha: "27/06/2026"
autores:
  - "Ing. Guillermo Mamani Chambi"
---

# Design Doc `DD-ADMIN-001` — Rol de Administrador Institucional (Tab Usuarios)

**Qué es**: documento de diseño del vertical slice que materializa el **Rol Administrador Institucional (TI)** declarado en ADR-0011, mediante una nueva pestaña **"Usuarios"** accesible vía frontend **React 18 + Vite** que consume un backend **Django REST Framework** sobre **PostgreSQL 15 schema `admin`** (separado del clínico). Auth bridge con FastAPI (clínico) vía token exchange. UI alineada con la paleta CSS vars y el estilo visual de la app existente.

**Relación con otros documentos**:

- **Trazabilidad al FSD**: `fsd_uc: FSD-UC-ADMIN-001` — caso de uso creado en `docs/fsd/FSD_vFinal.md` §4.8 (v1.1, Junio 2026) a partir de la persona "Personal de TI Institucional" del BRD §3.2, el rol Administrador de AGENTS.md §2.3 y la decisión de ADR-0011. Ver §4 para deltas aplicados.
- **Decisiones arquitectónicas vigentes**: ADR-0011 (separación del rol), ADR-0012 (persistencia PostgreSQL schema `admin` + soft-delete + audit Append-Only — **qué**), ADR-0013 (stack Django + React acotado al bounded context admin — **cómo**).
- **MVP vigente (no romper)**: `PR-IMPL-ADMIN-001` (localStorage en `configuracion.html`) sigue funcionando hasta que el bounded context admin esté listo (F9). La transición MVP → stack Django/React es transparente para el usuario final.
- Alimenta el **DTP** vía `dtp-sync` (ver §4).

## 1. Objetivo y contexto

- **Qué resuelve este feature** (2–4 líneas): el Rol Administrador (ADR-0011) carece de superficie UI. Este DD añade la pestaña **"Usuarios"** como componente React autocontenido (`AdminUsersPanel.tsx`) servido desde `frontend-admin/`, que consume una API REST en Django sobre PostgreSQL schema `admin` separado del clínico. Permite al Admin TI listar, crear, editar y desactivar usuarios institucionales (Analistas y Supervisores) sin tocar el flujo clínico.
- **Caso(s) de uso del FSD que implementa**: `FSD-UC-ADMIN-001` (Gestión de usuarios institucionales por Administrador TI), enlace: `docs/fsd/FSD_vFinal.md#fsd-uc-admin-001`.
- **Alcance**:
  - **Dentro**: CRUD de usuarios (Analista, Supervisor, Admin) con nombre, email, rol, estado activo/inactivo, fecha de alta. Persistencia **PostgreSQL schema `admin` tabla `admin_users`** (ADR-0012). Soft-delete vía `deactivated_at`. Auditoría Append-Only vía `django-auditlog` (reemplaza el `user_audit_log` propio del ADR-0012 con librería battle-tested). Validación de unicidad de email a nivel DB (`UNIQUE` constraint). Confirmación al desactivar. Restricción de visibilidad: solo usuarios con rol `admin` ven el panel.
  - **Fuera** (explícito): autenticación real (sigue mock hasta F7 auth bridge), MFA, reset de contraseñas, importación masiva CSV, multi-tenant.

## 2. Diseño (el "cómo") `[humano+máquina]`

- **Enfoque elegido**: bounded context `admin` con stack **React 18 + Vite + TypeScript** (frontend) y **Django 5 + DRF 3.15 + django-auditlog + django-guardian** (backend). PostgreSQL 15 mismo motor del sistema, schema `admin` separado del clínico. Auth bridge entre FastAPI (clínico, donde el usuario hace login) y Django (admin, donde se hacen las mutaciones) vía token exchange. Frontend servido por Vite dev server (desarrollo) o nginx (producción). Backend Django por gunicorn detrás de Caddy/nginx reverse proxy.

- **Stack por componente** (ver ADR-0013 §Decisión para detalle):

  | Componente | Stack | Ruta en repo |
  |:---|:---|:---|
  | UI panel React | React 18 + Vite 5 + TypeScript 5 | `frontend-admin/src/admin/components/` |
  | State management local | React `useState` + `useReducer` + TanStack Query opcional | `frontend-admin/src/admin/state/` |
  | HTTP client | `fetch` nativo (sin axios) con wrapper `adminClient.ts` | `frontend-admin/src/admin/api/` |
  | Backend API | Django 5 + DRF 3.15 | `backend-admin/apps/users/` |
  | ORM + migrations | Django ORM + `python manage.py makemigrations` | `backend-admin/apps/users/migrations/` |
  | Auth | django.contrib.auth + django-guardian (RBAC) + DRF TokenAuth | `backend-admin/apps/users/auth.py` |
  | Audit Append-Only | django-auditlog (signals → tabla `LogEntry`) | `backend-admin/apps/audit/` |
  | Tests backend | pytest-django + pytest-cov + factory_boy | `backend-admin/tests/` |
  | Tests frontend | Vitest 1.x + MSW 2.x + @vitest/coverage-v8 | `frontend-admin/tests/` |

- **Componentes React** (frontend-admin):

  ```
  frontend-admin/src/admin/components/
  ├── AdminUsersPanel.tsx        # Container principal, lazy-loaded por ruta /admin/users
  ├── UserTable.tsx              # Tabla con columnas: Nombre, Email, Rol, Estado, Alta, Acciones
  ├── UserForm.tsx               # Modal de alta/edición con validación inline
  ├── UserDeleteConfirm.tsx      # Modal de confirmación de desactivación
  ├── RoleBadge.tsx              # Badge colorido por rol (analista/supervisor/admin)
  ├── StatusToggle.tsx           # Switch on/off para active
  └── EmptyState.tsx             # Estado vacío "No hay usuarios registrados"
  ```

- **Modelo de datos** (Django ORM, `backend-admin/apps/users/models.py`):

  ```python
  # admin_users table — schema 'admin' (no 'public')
  class AdminUser(models.Model):
      ROLES = [('analista', 'Analista'), ('supervisor', 'Supervisor'), ('admin', 'Administrador')]
      id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
      full_name = models.CharField(max_length=80, validators=[MinLengthValidator(3)])
      email = models.EmailField(unique=True)  # case-insensitive unique via UNIQUE LOWER(email)
      role = models.CharField(max_length=16, choices=ROLES, default='analista')
      active = models.BooleanField(default=True)
      created_at = models.DateTimeField(auto_now_add=True)
      updated_at = models.DateTimeField(auto_now=True)
      deactivated_at = models.DateTimeField(null=True, blank=True)
      created_by = models.ForeignKey('self', null=True, on_delete=models.SET_NULL,
                                     related_name='created_users')
      
      class Meta:
          db_table = 'admin\".\"users'  # schema admin
          constraints = [
              models.CheckConstraint(check=models.Q(role__in=['analista','supervisor','admin']),
                                     name='admin_users_role_valid'),
          ]
          indexes = [
              models.Index(fields=['active'], name='admin_users_active_idx',
                           condition=models.Q(deactivated_at__isnull=True)),
          ]
      
      def clean(self):
          # RN-09 + ADR-0011: full_name trimmed 3-80 chars, email lowercased
          self.full_name = self.full_name.strip()
          self.email = self.email.strip().lower()
          if len(self.full_name) < 3 or len(self.full_name) > 80:
              raise ValidationError({'full_name': 'Nombre 3-80 caracteres'})
      
      def soft_delete(self, actor):
          self.deactivated_at = timezone.now()
          self.active = False
          self.save(update_fields=['deactivated_at', 'active', 'updated_at'])
      
      def __str__(self):
          return f'{self.full_name} <{self.email}> ({self.role})'
  ```

- **API REST** (DRF ViewSets, `backend-admin/apps/users/views.py`):

  ```
  GET    /api/admin/users/                  → 200 [AdminUser] (filtra WHERE deactivated_at IS NULL)
  POST   /api/admin/users/                  → 201 AdminUser | 400 ValidationError | 409 EmailExists
  GET    /api/admin/users/{uuid}/           → 200 AdminUser | 404
  PATCH  /api/admin/users/{uuid}/           → 200 AdminUser | 400 | 403 | 404 | 409
  DELETE /api/admin/users/{uuid}/           → 204 (soft-delete, set deactivated_at) | 404
  GET    /api/admin/users/{uuid}/history    → 200 [LogEntry] (django-auditlog)
  POST   /api/admin/auth/exchange           → 200 {django_token} (FastAPI JWT → Django token)
  ```

  **Auth middleware**:
  - Verifica header `Authorization: Bearer <django_token>`.
  - Verifica `request.user.role === 'admin'` para mutaciones (GET permitido para supervisor en modo solo-lectura futuro).
  - Rate limiting 60 req/min por user vía `django-ratelimit`.

- **Cliente HTTP** (frontend-admin, `src/admin/api/adminClient.ts`):

  ```typescript
  // Wrapper con manejo de errores HTTP y auth header
  export const adminClient = {
    async list(): Promise<AdminUser[]> { ... },
    async create(input: AdminUserCreate): Promise<AdminUser> { ... },
    async update(id: string, patch: AdminUserUpdate): Promise<AdminUser> { ... },
    async softDelete(id: string): Promise<void> { ... },
    async history(id: string): Promise<AuditLogEntry[]> { ... }
  };
  ```

  - Manejo de errores: 401 → refresh token, 403 → "Sin permisos", 404 → "Usuario no existe",
    409 → "Email duplicado" o "Ya desactivado", 500 → "Error del servidor, reintente".
  - Spinners en `UserForm` y `UserDeleteConfirm` durante requests.
  - Polling cada 30s para detectar cambios cross-browser (alternativa más simple que WebSocket para MVP).

- **Auth bridge FastAPI ↔ Django** (F0, crítico):

  1. Usuario hace login en FastAPI (`POST /api/v1/auth/login`) → recibe JWT con claim `role`.
  2. Frontend llama `POST /api/admin/auth/exchange` con el JWT FastAPI en header.
  3. Django valida el JWT con secret compartido (config en env vars).
  4. Django devuelve `Token` (django-rest-framework-authtoken) válido por 24h.
  5. Frontend usa el Django token para todas las llamadas a `/api/admin/users/*`.

  **Secret compartido**: `AUTH_BRIDGE_SECRET` en env vars de ambos backends. Rotación documentada.

- **Esquema de datos afectado**:

  | Capa | Cambio | Migración |
  |:---|:---|:---|
  | PostgreSQL schema `admin` | NUEVO. Tabla `admin.users` + tabla `audit.log_entry` (django-auditlog) | Django migrations: `0001_initial.py` |
  | PostgreSQL schema clínico | Sin cambios | Ninguna |
  | Redis | Sin cambios (sigue siendo broker del clínico) | Ninguna |
  | localStorage | Sin cambios (sigue siendo fallback MVP si backend admin está caído) | Ninguna |

- **Diagrama**:

  ```mermaid
  flowchart LR
    A[Admin abre /admin/users] --> B{¿JWT FastAPI?}
    B -- no --> X[Redirect a /login]
    B -- sí --> C[POST /api/admin/auth/exchange]
    C --> D[Recibe Django token]
    D --> E[GET /api/admin/users/]
    E --> F[renderUserTable]
    F --> G{accion}
    G -- add --> H[POST /api/admin/users/]
    G -- edit --> I[PATCH /api/admin/users/{id}/]
    G -- delete --> J[DELETE /api/admin/users/{id}/]
    H --> K[LogEntry django-auditlog Append-Only]
    I --> K
    J --> K
    K --> F
  ```

- **Estilos y componentes UI**:
  - Paleta CSS vars existente (`--umss-blue`, `--umss-red`, `--green-success`, `--orange-warning`).
  - FontAwesome 6.4 (mismo CDN que el resto del proyecto).
  - Componentes accesibles: `aria-label` en botones de acción, focus trap en modales.
  - Responsive: tabla con scroll horizontal en pantallas <768px.

- **Gating de visibilidad**:
  - Frontend: si `auth.role !== 'admin'`, redirigir a `/dashboard` (no mostrar el panel).
  - Backend: middleware DRF `IsAdmin` rechaza toda request con `role !== 'admin'` con 403.

- **Validaciones**:
  - Backend (autoridad):
    - Email único case-insensitive vía `UNIQUE LOWER(email)` constraint a nivel DB (F1 Alembic raw migration).
    - `full_name.trim()` 3-80 chars (CharField + validator).
    - `role` ∈ `{analista, supervisor, admin}` (choices + CheckConstraint).
    - Soft-delete idempotente: si ya está `deactivated_at IS NOT NULL`, DELETE devuelve 409.
    - No se permite desactivar al usuario cuyo `id === request.user.id` (autoprotección via service).
  - Frontend (UX):
    - Validación inline en `UserForm` antes de submit.
    - Mensajes de error legibles en español, consistentes con backend.

## 3. Alternativas consideradas

| Alternativa | Pros | Contras | ¿Elegida? |
| :--- | :--- | :--- | :--- |
| **A. React + Django REST + PostgreSQL schema admin (este DD, ADR-0013)** | Operacionaliza React declarado en AGENTS §3, admin UI gratis (`/admin/`), django-auditlog battle-tested, migración incremental sin tocar clínico | Dos backends que mantener (FastAPI + Django), curva de aprendizaje Django si el equipo no lo domina | **sí** |
| B. FastAPI + React + PostgreSQL (ADR-0012 sin Django) | Sin curva de aprendizaje Django, un solo backend | Pierde admin UI gratis, ORM más boilerplate para CRUD simple, sin django-auditlog (reimplementación custom) | no |
| C. Tab nueva en `configuracion.html` + `localStorage` (PR-IMPL-ADMIN-001 vigente) | MVP ya entregado y funcionando | No escala a multi-institución, no auditable, no compartido entre admins | no (MVP vigente hasta F9, luego migrar) |
| D. Página separada `admin-usuarios.html` con HTML vanilla + Django template | Más simple que React | Duplica el trabajo de tener que migrar a React más adelante, peor DX para estado de UI | no |
| E. Django global (reemplaza FastAPI también en clínico) | Stack unificado | Riesgo crítico de regresión clínica (RN-01/02/04/05/06), 6+ sprints de reescritura sin valor inmediato | no |
| F. Next.js full-stack + React | Un solo lenguaje end-to-end | No coincide con sugerencia del arquitecto (pidió Django), menos maduro para admin UI que Django | no |

## 4. Impacto en las specs vivas `[máquina]`

| Artefacto vivo | Cambio | ¿Delta vs DTI vFinal? |
| :--- | :--- | :--- |
| `docs/fsd/FSD_vFinal.md` | §4.8 `FSD-UC-ADMIN-001` ya agregado en v1.1 (Junio 2026) con criterios Gherkin. Sin cambios en este DD (alcance funcional idéntico). | no (ya estaba) |
| `docs/brd/BRD_vFinal.md` | Sin cambio. BRD §3.2 ya cubre la persona "Personal de TI Institucional". | no |
| `docs/adr/ADR-0011-rol-administrador.md` | Sin cambio de decisión. Sigue vigente. | no |
| `docs/adr/ADR-0012-persistencia-admin-postgres.md` | **Parcialmente superseded por ADR-0013**: el **qué** (PostgreSQL schema `admin`, soft-delete, audit) sobrevive; el **cómo** (backend FastAPI) cambia a Django. ADR-0012 mantiene su vigencia para el modelo de datos. | sí (referencia cruzada) |
| `docs/adr/ADR-0013-stack-django-react-admin.md` | **NUEVO**. Decisión arquitectónica del stack Django+React acotada al bounded context admin. | sí |
| `AGENTS.md` §3 (Stack Tecnológico) | **Actualizar** para declarar la división por bounded context: FastAPI para clínico + IA, Django+DRF para admin. Ver ADR-0013 §Plan F10. | sí |
| `AGENTS.md` §5 (ADRs) | Agregar fila ADR-0013. | sí |
| `docs/DTI.md` §2.2 (Actores) | Referenciar ADR-0013 para Admin TI. | sí |
| `docs/DTI.md` §21 (ADRs) | Agregar fila ADR-0013. | sí |
| `docs/PROMPT_MAPPING.md` | Agregar PM-ADMIN-003 (bootstrap Django+React). PM-ADMIN-001 y PM-ADMIN-002 vigentes como referencia histórica. | sí |
| `docs/design/DD-ADMIN-001.md` | **Este documento reescrito** (§2, §3, §4 reflejan el nuevo stack). | sí |
| `configuracion.html` (MVP vigente) | **Sin cambio en este DD**. Sigue funcionando con localStorage. Migración transparente en F9. | no |
| `frontend/src/admin/userStore.ts` (MVP vigente) | **Sin cambio en este DD**. Sigue siendo el adapter síncrono localStorage. Migración en F5 (frontend-admin separado). | no |
| `docs/design/DESIGN-006-semaforizacion.md` | Sin cambio (es el feature de Semaforización, ortogonal). | no |
| `docs/baseline/` | **No se toca** (regla de oro, baseline congelado). | no |

**Recordatorio (regla de oro)**: el baseline congelado de M4 (`docs/baseline/`) **no se toca**. Los cambios viven en `docs/product/` (o equivalente `docs/` en este repo, ya que el proyecto fusiona baseline + product en una sola rama `release/2.0.0`).

**Deltas resultantes que requieren acuerdo explícito**:
1. ✅ **FSD-UC-ADMIN-001 ya existe** en `FSD_vFinal.md` §4.8 (v1.1, Junio 2026). Bloqueante resuelto.
2. ✅ **ADR-0013 creado** y vigente. Divide el stack por bounded context.
3. ⚠️ **ADR-0012 parcialmente superseded**: el **qué** persiste (PostgreSQL schema `admin`, soft-delete, audit), el **cómo** (FastAPI) cambia. Mantener referencia cruzada en ambos.
4. ⚠️ **MVP vigente intacto**: `PR-IMPL-ADMIN-001` sigue funcionando; este DD **no lo rompe**. La transición es gradual.
5. 📋 **AGENTS §3 actualización pendiente** (F10 del ADR-0013): agregar "bounded context admin → Django + DRF".

## 5. Prompts usados `[humano+máquina]`

| Prompt | Tarea | Estado |
| :--- | :--- | :--- |
| `PR-IMPL-ADMIN-001` | Generación del bloque sidebar item + panel `#users-tab` + script de persistencia localStorage en `configuracion.html`. Tests Vitest del `UserStore` (mockeando `localStorage`). | ✅ Aprobado y ejecutado (MVP vigente, 32 tests pasando, cobertura 97.5% branches). |
| `PR-IMPL-ADMIN-002` | Migración del CRUD de localStorage a PostgreSQL schema admin + API REST FastAPI + soft-delete + user_audit_log Append-Only. | ✅ Aprobado (prompt versionado, **parcialmente superseded por ADR-0013** que cambia FastAPI → Django). El **qué** del prompt sobrevive; el **cómo** se reemplaza por PM-ADMIN-003. |
| `PR-IMPL-ADMIN-003` *(pendiente)* | Bootstrap Django 5 + DRF + django-auditlog + django-guardian en `backend-admin/`. Bootstrap React 18 + Vite + MSW en `frontend-admin/`. Implementación del auth bridge FastAPI↔Django. Tests pytest-django ≥90% + Vitest ≥90%. | ⏳ Por crear (F0-F8 del ADR-0013). |

> **Acción previa al PR**: crear `docs/prompts/impl/PR-IMPL-ADMIN-003.md` siguiendo [`PROMPT_TEMPLATE.md`](../PROMPT_TEMPLATE.md) y registrarlo en `docs/PROMPT_MAPPING.md` como PM-ADMIN-003. Tareas del prompt (descomposición atómica, máx 3h, alineadas con F0-F9 del ADR-0013):
> 1. **F0**: Decidir auth bridge (FastAPI JWT → Django Token) y documentar en `docs/AUTH_BRIDGE.md`.
> 2. **F1**: Bootstrap `backend-admin` con `django-admin startproject` + DRF + django-auditlog + django-guardian. Settings con DB apuntando a PostgreSQL schema `admin`.
> 3. **F2**: App `apps/users`: modelo `AdminUser`, serializers DRF, viewsets, URLs, migraciones.
> 4. **F3**: App `apps/audit`: configuración django-auditlog + endpoint `GET /api/admin/users/{id}/history`.
> 5. **F4**: Bootstrap `frontend-admin` con Vite template react-ts. Configurar MSW para tests.
> 6. **F5**: Componentes React `AdminUsersPanel`, `UserTable`, `UserForm`, `UserDeleteConfirm`, `RoleBadge`, `StatusToggle`.
> 7. **F6**: Tests backend (pytest-django + ≥90%) + frontend (Vitest+MSW + ≥90%).
> 8. **F7**: Auth bridge: `POST /api/admin/auth/exchange` que canjea FastAPI JWT por Django Token.
> 9. **F8**: docker-compose: servicios `backend-admin` + `frontend-admin`. Caddy reverse proxy.
> 10. **F9**: Smoke E2E: login FastAPI → alta usuario en Django → verificación en admin UI Django.

Cada prompt sigue [`PROMPT_TEMPLATE.md`](../PROMPT_TEMPLATE.md), vive en `docs/prompts/impl/PR-IMPL-ADMIN-XXX.md` y se referencia desde `docs/PROMPT_MAPPING.md`.

## 6. Plan de pruebas y evals

- **Unit backend** (pytest-django + factory_boy + pytest-cov, RN-09 ≥90%):
  - `AdminUser.save/clean` con validación de email único case-insensitive.
  - `AdminUser.soft_delete` idempotente.
  - `AdminUserViewSet` con permisos RBAC (test 403 para role != admin).
  - `audit_log` Append-Only verifica que cada mutación registra fila.
- **Unit frontend** (Vitest + MSW + @vitest/coverage-v8, RN-09 ≥90%):
  - `adminClient.list/create/update/softDelete/history` mockeando respuestas HTTP.
  - `UserForm` valida inline (errores visibles antes de submit).
  - `AdminUsersPanel` renderiza tabla con N usuarios, vacío si 0.
- **Integration** (manual con browser):
  - Round-trip `create → list → reload page → list` mantiene datos.
  - Cross-browser: alta en A aparece en B sin recargar (polling 30s).
- **E2E / Gherkin** (deriva de criterios de aceptación del `FSD-UC-ADMIN-001`):

  ```gherkin
  DADO un usuario con rol admin autenticado (vía FastAPI login + Django token exchange)
  CUANDO abre el panel React /admin/users
  ENTONCES ve la tabla con todos los usuarios activos y el botón "Agregar usuario"

  DADO un admin en el formulario de alta
  CUANDO ingresa email duplicado
  ENTONCES el sistema rechaza con 409 "Email ya registrado" y muestra mensaje en UI

  DADO un admin que intenta desactivarse a sí mismo
  CUANDO confirma la acción
  ENTONCES el sistema bloquea con 403 "No puede desactivarse a sí mismo"

  DADO un usuario con rol analista o supervisor autenticado
  CUANDO intenta acceder a /admin/users
  ENTONCES el backend rechaza con 403 y el frontend redirige a /dashboard

  DADO dos navegadores autenticados como admin
  CUANDO el navegador A crea un usuario
  ENTONCES el navegador B lo ve en su próxima actualización (polling 30s o manual refresh)
  ```

- **Evals de IA**: N/A (este feature no usa agente IA).
- **Seguridad**:
  - Test de SQL injection en campos de texto (Django ORM parametriza por defecto, verificar).
  - Test de cross-tenant: dos institutions no deben verse (multi-tenant fuera de alcance MVP).
  - Test de rate limiting: 61 requests en 1 minuto devuelve 429.

## 7. Definition of Done (checklist)

- [x] `fsd_uc` declarado y enlazado en frontmatter (trazabilidad al FSD).
- [x] `FSD-UC-ADMIN-001` creado en `docs/fsd/FSD_vFinal.md` §4.8 v1.1 con criterios Gherkin (Junio 2026).
- [x] Diseño (§2) y alternativas (§3) documentados con stack actualizado (Django + React, ADR-0013).
- [x] ADR-0011, ADR-0012, ADR-0013 enlazados en frontmatter.
- [x] §4 Impacto en specs vivas registrado (sin tocar baseline).
- [x] Prompt `PR-IMPL-ADMIN-001` versionado y ejecutado (MVP vigente, cobertura 97.5% branches RN-09).
- [x] Prompt `PR-IMPL-ADMIN-002` versionado (parcialmente superseded por ADR-0013).
- [ ] Prompt `PR-IMPL-ADMIN-003` versionado y registrado en `PROMPT_MAPPING.md` (pendiente F0-F9 de ADR-0013).
- [ ] Bootstrap `backend-admin` (Django + DRF + django-auditlog + django-guardian) operativo.
- [ ] Bootstrap `frontend-admin` (React 18 + Vite + TypeScript) operativo.
- [ ] Modelo `AdminUser` con migración Django + constraints DB.
- [ ] Endpoints REST `GET/POST/PATCH/DELETE /api/admin/users/` + `/history` + `/auth/exchange` funcionales.
- [ ] Componentes React `AdminUsersPanel` + `UserTable` + `UserForm` + `UserDeleteConfirm` + `RoleBadge` + `StatusToggle` implementados.
- [ ] Auth bridge FastAPI JWT → Django Token funcional.
- [ ] Tests backend pytest-django con cobertura ≥90% sobre `admin_user_service` (RN-09).
- [ ] Tests frontend Vitest+MSW con cobertura ≥90% sobre `adminClient` y componentes (RN-09).
- [ ] docker-compose con servicios `backend-admin` + `frontend-admin` + reverse proxy.
- [ ] Smoke test E2E F9 ejecutado y documentado en PR.
- [ ] `skill-validation-agent` corrido y reporte adjuntado.
- [ ] DTP actualizado (changelog + estado del FSD-UC-ADMIN-001) vía `dtp-sync`.
- [ ] AGENTS.md §3 actualizado para declarar stack por bounded context (F10 ADR-0013).
- [ ] AGENTS.md §5 con fila ADR-0013.
- [ ] DTI.md §21 con fila ADR-0013.
- [ ] DTI.md §2.2 con referencia a ADR-0013.
- [ ] CHANGELOG.md con entrada "Stack admin: React + Django REST + PostgreSQL schema admin (ADR-0013)".
- [ ] MVP vigente `PR-IMPL-ADMIN-001` sigue funcionando durante toda la transición (verificado con smoke test).
- [ ] PR declara: prompts usados (001 + 002 + 003), archivos generados vs editados a mano, evidencia de cobertura, gating por rol verificado en 3 navegadores (Chrome, Edge, Firefox), auth bridge funcional cross-backend.
- [ ] Confirmación explícita del arquitecto (Guillermo) antes de merge a `release/2.0.0` (no a `main` — restricción AGENTS §11).