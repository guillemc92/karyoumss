---
id: ADR-0013
title: Stack de Administración — React 18 + Django REST Framework + PostgreSQL schema admin
date: 2026-06-27
status: accepted
supersedes: Alcance MVP localStorage (PR-IMPL-ADMIN-001) + ADR-0012 (FastAPI para dominio admin)
related: [ADR-0011, ADR-0001, ADR-0004, DD-ADMIN-001]
fase: desarrollo
autor: Ing. Guillermo Mamani Chambi
---

# ADR 0013: Stack de Administración — React 18 + Django REST Framework + PostgreSQL

## Contexto

El proyecto BIOMED UMSS arrastra una deuda técnica que el equipo ha decidido resolver al entrar en etapa de desarrollo formal (release/2.0.0 congelado, foco ahora en construcción):

1. **Frontend declarado en AGENTS §3** es React 18 + Vite 5 + Konva.js 9 + Zustand + TypeScript 5. Sin embargo, la única superficie entregada hasta ahora es HTML+JS vanilla (`configuracion.html`, `correccion de cariotipo.html`, `dashboard.html`, etc.). React está declarado pero **no operacionalizado**.

2. **Backend declarado en AGENTS §3** es FastAPI + Celery + Redis + PostgreSQL. Sin embargo, las historias de usuario relacionadas con administración institucional (US-14 `Gestión de usuarios`) y la decisión de ADR-0011 (separación del rol Administrador TI) requieren una superficie de gestión CRUD que se entrega más naturalmente en **Django + Django REST Framework (DRF)** por:
   - Admin UI autogenerado de Django (`django.contrib.admin`) acelera iteraciones internas.
   - DRF serializers + ViewSets cubren CRUD estándar con menos boilerplate que FastAPI routers.
   - ORM Django (migrations + admin) reduce fricción para crear schema `admin` separado.
   - Ecosistema maduro de paquetes de autenticación, RBAC, audit (`django-auditlog`, `django-guardian`).

3. **ADR-0012** (persistencia en PostgreSQL via FastAPI) se aprobó tres turnos antes de este ADR. La decisión de stack cambia el **cómo** pero conserva el **qué** (PostgreSQL schema `admin` separado, soft-delete, `user_audit_log` Append-Only).

4. El equipo entra en etapa de desarrollo y el arquitecto Ing. Guillermo Mamani Chambi ha sugerido como directriz del proyecto: "el frontend debo hacer en React y el backend en Django con PostgreSQL de base de datos, ya debo entrar en etapa de desarrollo". Esta directriz se adopta formalmente.

## Decisión

Adoptar el siguiente stack para la fase de desarrollo del proyecto BIOMED UMSS:

| Capa | Stack | Justificación |
|:---|:---|:---|
| **Frontend admin (este DD)** | **React 18 + Vite 5 + TypeScript 5** | Ya declarado en AGENTS §3; se operacionaliza. Componente `AdminUsersPanel` autocontenido. |
| **Backend admin (este DD)** | **Django 5.x + Django REST Framework 3.15+** | ORM maduro, admin UI gratis, migrations reproducibles. |
| **Base de datos admin** | **PostgreSQL 15 schema `admin`** | Sin cambios vs ADR-0012. Schema separado del clínico. |
| **Auth** | **django.contrib.auth + DRF TokenAuth + django-guardian para RBAC** | Roles `analista`/`supervisor`/`admin` mapeados a Django Groups + Permissions. |
| **Auditoría** | **django-auditlog** | Append-Only automático sobre `admin.users` + tabla `LogEntry`. |
| **Tests backend** | **pytest-django + pytest-cov + factory_boy** | Cobertura ≥90% (RN-09). |
| **Tests frontend** | **Vitest 1.x + MSW 2.x + @vitest/coverage-v8** | Reemplaza jsdom-mocks por MSW. |
| **API client frontend** | **fetch nativo** o TanStack Query si se requiere caché | Sin axios para minimizar deps. |

### Lo que **no cambia**

- **AGENTS §3 stack clínico**: la pipeline de IA (U-Net + EfficientNet-B3 + Grad-CAM) sigue en FastAPI + Celery + Redis + TorchServe. **Django se introduce solo para el bounded context `admin`**, no reemplaza FastAPI globalmente.
- **PostgreSQL 15** sigue siendo el motor único de base de datos. Django usa el mismo cluster con un schema distinto (`admin`).
- **React 18 + Vite** se mantienen según AGENTS §3; no se introduce Next.js ni Remix.
- **Konva.js 9 + Zustand** siguen siendo el stack del EditorCanvas clínico (ortogonal a este ADR).
- **RN-09 (cobertura ≥90%)** sigue siendo invariante.

### Estructura de repositorio propuesta

```
karyoumss/
├── backend-clinical/           # FastAPI + Celery (existente)
│   ├── app/
│   │   ├── api/                # routers clínicos
│   │   ├── tasks/              # Celery workers (AI)
│   │   └── services/           # ISCN, audit Merkle, etc.
│   └── alembic/                # migraciones clínicas
│
├── backend-admin/              # Django + DRF (NUEVO, este ADR)
│   ├── manage.py
│   ├── admin_backend/          # settings, urls, wsgi
│   ├── apps/
│   │   ├── users/              # modelo AdminUser, viewsets, serializers
│   │   ├── audit/              # django-auditlog config + LogEntry queries
│   │   └── core/               # auth custom, RBAC mixins
│   ├── migrations/             # Django migrations del schema admin
│   └── tests/                  # pytest-django + factory_boy
│
├── frontend-admin/             # React + Vite (NUEVO, este ADR, scope acotado)
│   ├── src/
│   │   ├── admin/
│   │   │   ├── components/
│   │   │   │   ├── AdminUsersPanel.tsx
│   │   │   │   ├── UserForm.tsx
│   │   │   │   └── UserTable.tsx
│   │   │   ├── api/
│   │   │   │   └── adminClient.ts  # fetch wrapper con auth header
│   │   │   └── types/
│   │   │       └── user.ts
│   │   ├── main.tsx
│   │   └── App.tsx
│   ├── package.json
│   ├── vite.config.ts
│   └── tests/                  # Vitest + MSW
│
├── frontend-clinical/          # Konva + Zustand + vanilla (existente, ortogonal)
│   └── ...
│
├── docs/
│   ├── adr/                    # este ADR vive aquí
│   ├── design/                 # DD-ADMIN-001 reescrito
│   └── ...
```

**Decisión de monorepo vs multirepo**: por ahora **monorepo** (carpetas separadas bajo misma raíz) por simplicidad operativa. Si el equipo crece se puede拆分 a multirepo sin reescribir nada (las URLs internas están namespaced).

## Justificación

### Por qué Django solo para admin, no global

- **Riesgo de regresión clínica**: el EditorCanvas (Konva), pipeline U-Net + EfficientNet-B3, audit Merkle y Celery ya están implementados en FastAPI. Reescribir todo a Django duplica trabajo y abre ventanas de bug en código clínico sensible (RN-01, RN-02, RN-04, RN-05, RN-06).
- **Coste/beneficio**: el bounded context `admin` es CRUD simple sobre 1 tabla. DRF aporta más valor relativo ahí que en la pipeline de inferencia.
- **Cohesión del bounded context**: ADR-0004 (hexagonal) ya prevee que cada bounded context tenga su stack óptimo. Este ADR formaliza que `admin` vive en Django, `clinical` vive en FastAPI.

### Por qué no reemplazar FastAPI completamente

- El equipo ya domina FastAPI (declarado en AGENTS §3 + ADR-0002 + código clínico existente).
- TorchServe + Celery + Redis están integrados con FastAPI nativo (`fastapi.BackgroundTasks`, `asyncio`).
- El cambio de stack total costaría ~6 semanas de reescritura sin valor clínico añadido.

### Por qué django-auditlog y no el `user_audit_log` Append-Only propio de ADR-0012

- `django-auditlog` ya implementa Append-Only vía signals de Django + tabla `LogEntry`.
- Cubre `actor` (FK a `auth_user`), `action` (`create/update/delete`), `object_repr`, `timestamp`, `changes_dict` (JSONField con diff).
- Reduce código custom; battle-tested con 2M+ descargas/mes.
- Se mantiene el espíritu del ADR-0012 (auditoría centralizada) pero se delega a librería.

### Por qué React solo para admin, no global

- Reescribir todo el frontend clínico (Konva EditorCanvas, dashboard, dashboard supervisor) a React es 4-6 semanas de trabajo sin valor de release.
- El panel `AdminUsersPanel` es CRUD tabular, donde React brilla (componentes, estado, hooks).
- **Estrategia de migración incremental**: cada release incorpora un bounded context más en React. Primero `admin`, luego `dashboard`, finalmente `editor` (cuando se justifique).

### Por qué monorepo

- Reutilizar `docs/`, `AGENTS.md`, `.cursor/rules/` entre los dos backends y los dos frontends.
- CI unificado puede correr tests de los 4 proyectos.
- Deploy puede separar: `backend-admin` a instancia EC2 pequeña, `backend-clinical` a ECS con GPU.

## Consecuencias

### Positivas

- **Operacionaliza React** declarado en AGENTS §3 sin reescribir el clínico.
- **Operacionaliza un ORM maduro** para el bounded context admin (Django ORM > SQLAlchemy raw para CRUD simple).
- **Admin UI gratis** para debug interno del equipo (`/admin/`).
- **Audit log maduro** out-of-the-box con `django-auditlog`.
- **Reduce código custom** del MVP localStorage y del `user_audit_log` propio.
- **Equipos pueden trabajar en paralelo**: clínico sigue en FastAPI, admin en Django, sin bloquearse.

### Negativas

- **Dos backends que mantener**: `backend-clinical` (FastAPI) + `backend-admin` (Django). Coste operativo: doble deploy, doble monitoring, doble secret management.
  - Mitigación: docker-compose con servicios separados + documentación de operaciones clara.
- **Dos frontends**: `frontend-clinical` (vanilla/React progresivo) + `frontend-admin` (React puro).
  - Mitigación: misma versión de React, mismo linter (ESLint + Prettier), mismas convenciones.
- **Autenticación compartida**: el JWT del clínico debe ser válido para Django también. Requiere un puente de auth.
  - Mitigación: usar `django-rest-framework-simplejwt` con secret compartido o un endpoint `/auth/bridge` en FastAPI que emite un token Django.
- **Catálogo de URLs**: cliente debe recordar dos bases (`https://api.biomed/clinico/v1/...` y `https://api.biomed/admin/v1/...`).
  - Mitigación: documentar en `docs/API.md` con tabla de endpoints por dominio.
- **ADR-0012 queda obsoleto en su §Decisión** (hablaba de FastAPI) pero se mantiene su §Justificación sobre PostgreSQL schema `admin` y soft-delete, que sí sobreviven. Este ADR lo supersede explícitamente.
- **Curva de aprendizaje Django** si el equipo solo conoce FastAPI.

### Neutras

- TypeScript 5 sigue siendo el lenguaje del frontend admin.
- PostgreSQL 15 sigue siendo el motor.
- Docker + docker-compose siguen siendo la estrategia de despliegue (ADR-0005).

## Plan de implementación

| Fase | Alcance | Esfuerzo | Bloqueante |
|:-:|:---|:---|:---|
| **F0** | Decidir estrategia de auth bridge (FastAPI JWT ↔ Django Token). Documentar en `docs/AUTH_BRIDGE.md`. | 4h | Sí |
| **F1** | Bootstrap `backend-admin` con `django-admin startproject admin_backend` + DRF + django-auditlog + django-guardian. Settings con DB apuntando a PostgreSQL `admin` schema. | 4h | F0 |
| **F2** | App `apps/users`: modelo `AdminUser`, serializers DRF, viewsets, URLs. Migración inicial Django. | 6h | F1 |
| **F3** | App `apps/audit`: configuración `django-auditlog` para modelo `AdminUser`. Endpoint `GET /api/admin/users/{id}/history`. | 4h | F2 |
| **F4** | Bootstrap `frontend-admin` con `npm create vite@latest -- --template react-ts`. Configurar MSW para tests. | 3h | F0 |
| **F5** | Componente `AdminUsersPanel.tsx` + `UserTable.tsx` + `UserForm.tsx` con TanStack Query o `fetch` nativo. | 8h | F2 + F4 |
| **F6** | Tests: backend pytest-django (≥90% cobertura) + frontend Vitest+MSW (≥90%). | 8h | F5 |
| **F7** | Auth bridge: usuario se loguea en FastAPI → recibe token → canjea por Django token vía `POST /api/admin/auth/exchange`. | 4h | F0 |
| **F8** | docker-compose: añadir servicios `backend-admin` y `frontend-admin`. Caddy/nginx como reverse proxy unificado. | 4h | F7 |
| **F9** | Smoke E2E manual cross-backend: login FastAPI → alta usuario en Django → verificación en admin UI Django (`/admin/`). | 2h | F8 |
| **F10** | Documentación: actualizar AGENTS §3 (agregar stack Django/React-admin), DTI §21 (este ADR), DTI §2.2 (Admin actor), DD-ADMIN-001 (este ADR es input), CHANGELOG (Breaking Change: nuevo stack admin). | 3h | F9 |
| **Total** | | **50h** (≈ 6 sprints de 8h) | |

### Riesgos y mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|:---|:---:|:---:|:---|
| Auth bridge introduce vulnerabilidad | Media | Crítico | Token exchange con TTL ≤ 60s; secret compartido solo en env vars; rotación documentada |
| Docker-compose con 4 servicios consume mucha RAM en CI | Alta | Bajo | matrix de CI: solo corre tests del stack modificado en cada PR |
| Equipo no domina Django | Alta | Medio | Pair programming primeras 2 semanas; tutorial interno `docs/DJANGO_CHEATSHEET.md` |
| `django-auditlog` agrega overhead en producción | Baja | Bajo | Índices en `LogEntry.timestamp DESC` y `LogEntry.action`; pruning job anual |
| Regresión clínica por cambio accidental | Baja | Crítico | Pipeline clínico en repo separado lógicamente; CI con gates: tests clínicos deben pasar antes de mergear cambios admin |

## Tensión con reglas del proyecto y cómo se resuelve

| Regla | Tensión | Resolución |
|:---|:---|:---|
| **AGENTS §3 "stack declarativo"** | AGENTS dice FastAPI para backend | Este ADR formaliza la **división por bounded context**: FastAPI para clínico, Django para admin. AGENTS §3 se actualizará en F10 para reflejar la excepción. |
| **ADR-0012 (PostgreSQL + FastAPI)** | Este ADR supersede el backend de ADR-0012 | ADR-0012 queda vigente para el **qué** (PostgreSQL schema `admin`, soft-delete, audit) pero no para el **cómo** (FastAPI → Django). |
| **RN-06 (segregación)** | ¿Django tiene acceso a schemas clínicos? | El rol Postgres del backend-admin solo tiene GRANT sobre schema `admin`. Cero permisos sobre `public` ni schemas clínicos. Configurado en `F1` settings Django. |
| **RN-09 cobertura ≥90%** | Dos stacks, dos suites de tests | Cada stack mantiene su gate: backend-admin ≥90% con pytest-django + coverage, frontend-admin ≥90% con Vitest v8. |
| **AGENTS §11 (no directo a main, PR a release/2.0.0)** | Este cambio es mayor | Rama `feature/django-admin-stack`, PR a `release/2.0.0` con reviewers obligatorios: Guillermo + 1 par. |

## Alternativas evaluadas

### A1. Mantener FastAPI + React (status quo + ADR-0012)
- **Pro:** Sin curva de aprendizaje, sin reescritura.
- **Contra:** Pierde las ventajas de Django (admin UI gratis, ORM maduro para CRUD). React queda "declarado pero no operacionalizado". Mantiene el "gap stack" entre intención y realidad.
- **Rechazado** porque el arquitecto explícitamente pidió transición.

### A2. Django global (reemplaza FastAPI también en clínico)
- **Pro:** Stack unificado, un solo ORM, una sola pipeline de tests.
- **Contra:** Reescritura de 6+ sprints del código clínico existente (EditorCanvas backend, Celery tasks, TorchServe integration, audit Merkle). Riesgo de regresión en código que cumple RN-01/02/04/05/06.
- **Rechazado** por coste/riesgo.

### A3. Next.js full-stack (Node.js en backend) + React
- **Pro:** Un solo lenguaje end-to-end.
- **Contra:** Introduce un tercer stack (Node); no usa Django que es lo solicitado; menos maduro para admin UI que Django.
- **Rechazado** porque no coincide con la sugerencia del arquitecto (Django + React, no Next.js).

### A4. (Aceptada) React + Django REST + PostgreSQL schema admin, acotado al bounded context admin
- Ya descrita en §Decisión.

## Trazabilidad

- **Sube a:** BRD §3.2 (Personal de TI Institucional) → MRD-13 (multi-institución) → FSD §4.8 (FSD-UC-ADMIN-001) → DD-ADMIN-001 → ADR-0011 → ADR-0012 (parcialmente) → **este ADR-0013**.
- **Genera:** `PR-IMPL-ADMIN-003` (prompt de bootstrap Django + DRF + django-auditlog).
- **Impacta:**
  - AGENTS §3 (nueva entrada: "bounded context admin → Django + DRF").
  - DTI §21 (este ADR entra).
  - DTI §2.2 (actor Admin TI ahora referencia este ADR).
  - DD-ADMIN-001 §2, §3, §4 (reescritura del stack y alternativas).
  - ADR-0012 (supersede parcial: backend cambia FastAPI → Django; el resto sobrevive).

## Notas

- Este ADR **no afecta** el MVP vigente de `PR-IMPL-ADMIN-001` (localStorage en `configuracion.html`). El MVP sigue funcionando hasta que el bounded context admin esté listo (F9). La transición de MVP → stack Django/React es transparente para el usuario final.
- La rama de trabajo es `feature/django-admin-stack` (no `main`, no `release/2.0.0` directo — restricción AGENTS §11).
- F0 (auth bridge) es la decisión técnica más delicada y debe resolverse ANTES de F1. Recomiendo workshop de 2h con Guillermo antes de empezar.
- Este ADR es **divisor de aguas**: a partir de acá, el proyecto tiene 2 backends y 2 frontends. Cualquier DD o ADR futuro debe declarar explícitamente a cuál stack aplica.