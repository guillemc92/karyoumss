# backend-admin — Django + DRF (Bounded Context Admin)

**Versión:** v0.1 | **ADR origen:** [ADR-0013](../docs/adr/0013-stack-django-react-admin.md) | **Estado:** F0+F1+F2 ejecutados

---

## Stack

- **Django 5.0.6** + **Django REST Framework 3.15.2**
- **django-auditlog 3.0.0** — auditoría Append-Only
- **django-guardian 2.4.0** — RBAC per-object (preparado para futuro)
- **PyJWT 2.9.0** — auth bridge FastAPI ↔ Django (F0)
- **PostgreSQL 15** — schema `admin` separado del clínico
- **psycopg3** driver

## Setup (desarrollo)

### 1. Crear virtualenv e instalar deps

```bash
cd backend-admin
python -m venv venv
source venv/bin/activate    # Linux/Mac
# o: venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 2. Configurar `.env`

```bash
cp .env.example .env
# Editar .env y rellenar POSTGRES_* y AUTH_BRIDGE_SECRET.
# Generar secret: python -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Crear DB y schema `admin`

Conectarse a PostgreSQL como superuser:

```sql
CREATE DATABASE biomed;
\c biomed
CREATE SCHEMA admin;
CREATE USER biomed_admin_service WITH PASSWORD '...';
GRANT USAGE ON SCHEMA admin TO biomed_admin_service;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA admin TO biomed_admin_service;
ALTER DEFAULT PRIVILEGES IN SCHEMA admin GRANT SELECT, INSERT, UPDATE ON TABLES TO biomed_admin_service;
-- REVOKE todo sobre schemas clínicos:
REVOKE ALL ON SCHEMA public FROM biomed_admin_service;
```

### 4. Aplicar migraciones

```bash
python manage.py migrate
```

### 5. Crear superuser Django admin (CLI)

```bash
python manage.py createsuperuser
```

### 6. Correr server

```bash
python manage.py runserver 0.0.0.0:8001
```

Admin UI Django disponible en `http://localhost:8001/admin/`.
API REST en `http://localhost:8001/api/admin/`.

## Endpoints

| Método | URL | Auth | Body | Respuesta |
|:---|:---|:---|:---|:---|
| POST | `/api/admin/auth/exchange` | Bearer FastAPI JWT | (vacío) | `{token, role, email, expires_at}` |
| GET | `/api/admin/users/` | Django Token + role=admin | — | `[AdminUser]` |
| POST | `/api/admin/users/` | Django Token + role=admin | `{full_name, email, role, active?}` | `AdminUser` |
| GET | `/api/admin/users/{id}/` | Django Token | — | `AdminUser` |
| PATCH | `/api/admin/users/{id}/` | Django Token + role=admin | `{full_name?, role?, active?}` | `AdminUser` |
| DELETE | `/api/admin/users/{id}/` | Django Token + role=admin | — | `{id, deactivated_at}` (soft-delete) |
| GET | `/api/admin/users/{id}/history/` | Django Token + role=admin | — | `[LogEntry]` |
| GET | `/api/admin/audit/logs/` | Django Token + role=admin | — | `{total, results}` |

## Tests

F6 cerrado. Correr la suite:

```bash
# Suite completa con coverage (gate RN-09 = 90%)
DJANGO_SETTINGS_MODULE=admin_backend.settings_test python -m pytest

# Solo E2E auth bridge (F7)
DJANGO_SETTINGS_MODULE=admin_backend.settings_test python -m pytest apps/users/tests/test_auth_bridge_e2e.py -v

# Django system check
python manage.py check
```

## Estado del plan F0-F10 (ADR-0013)

- ✅ F0 — Auth bridge diseñado en `docs/AUTH_BRIDGE.md`
- ✅ F1 — Bootstrap Django + DRF + auditlog + guardian
- ✅ F2 — App `users` con modelo `User` + `AdminUser` + services + views + URLs
- ✅ F3 — Endpoint `/history` funcional (modelo listo, requiere Postgres para test E2E)
- ⏳ F4 — Bootstrap frontend-admin (pendiente)
- ⏳ F5 — Componentes React (pendiente)
- ✅ F6 — Tests pytest-django 99% cobertura (148 tests passing)
- ✅ F7 — Auth bridge E2E in-process (12 tests: happy path + 7 errores + 2 post-exchange)
- ⏳ F8 — docker-compose con PostgreSQL + backend-admin + frontend-admin + Caddy
- ⏳ F9 — Smoke E2E cross-backend
- ⏳ F10 — Actualizar AGENTS §3, DTI, CHANGELOG

## Limitaciones conocidas

- **Sin tests automatizados aún** (F6 cerrado — 148 tests, 99% cobertura).
- **Sin conexión real a PostgreSQL** — F8 proveerá docker-compose con PostgreSQL.
- **Sin frontend aún** — F4-F5. Por ahora se puede usar Django admin UI (`/admin/`) o curl para probar API.
- **Audit log FK hardcodeada** a `admin"."users_user` por django-auditlog. En SQLite (tests) requiere workaround.

## Trazabilidad

- Sube a: BRD §3.2 → MRD-13 → FSD §4.8 → DD-ADMIN-001 → ADR-0011 → ADR-0012 (parcial) → **ADR-0013** → este backend.
- Prompt de implementación: `docs/prompts/impl/PR-IMPL-ADMIN-003.md` (pendiente).
- MVP vigente (no roto): `frontend/src/admin/userStore.ts` + `configuracion.html` con localStorage.