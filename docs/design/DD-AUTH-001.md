---
id: DD-AUTH-001
titulo: "Sistema de Autenticación (Login) — JWT unificado en backend-admin"
producto: "BIOMED UMSS — Intelligent Karyotyping Platform"
grupo: "G04"
fsd_uc:
  - "FSD §9 (ruta /login documentada)"
  - "FSD-UC-ADMIN-001 (precondición de rol admin, hoy vía localStorage)"
prd_refs:
  - "PRD-US-001"
adrs:
  - "ADR-0011"  # Rol Administrador
  - "ADR-0013"  # Stack Django+React admin
  - "ADR-0015"  # SimpleJWT independiente en backend-clinic (precedente de namespace)
  - "ADR-0017"  # backend-admin como autoridad JWT única (este feature)
prompts:
  - "PM-AUTH-001"   # a crear en PROMPT_MAPPING.md, T14
specs:
  - "SPEC-010-autenticacion-login.md"
ui_contract: "index.html"  # HTML aprobado, raíz del repo, modal #loginModal
release: "release/2.0.0"
status: proposed
fecha: "2026-07-12"
autores:
  - "Ing. Guillermo Mamani Chambi"
---

# Design Doc `DD-AUTH-001` — Sistema de Autenticación (Login)

## 0. Relación con el resto del sistema de auth

Este DD **no reemplaza** ni deroga `docs/AUTH_BRIDGE.md` (exchange F0, `POST /api/admin/auth/exchange`) ni el SimpleJWT propio de `backend-clinic` (ADR-0015). Es un **cuarto mecanismo**, coexistente: el primero en dar acceso end-to-end a un usuario que solo tiene email+password, sin depender de un FastAPI externo inexistente. `AUTH_BRIDGE.md` se marca como desactualizado para el flujo primario (ver nota de cabecera agregada en T3), pero el código del exchange no se elimina.

## 1. Trazabilidad SDD

```
BRD §3.2 (Actores) / FSD §3, §9
  → index.html (HTML Contract, modal #loginModal)
    → ADR-0017 (backend-admin como autoridad JWT única)
      → SPEC-010-autenticacion-login.md (Gherkin + contratos)
        → este DD (arquitectura de componentes)
          → código (backend-admin/, frontend-admin/)
            → tests (≥90% RN-09)
```

## 2. Arquitectura de flujo JWT

```
┌────────────┐   POST /api/auth/login/    ┌──────────────────────────┐
│ LoginPage   │ ─────────────────────────► │ AdminTokenObtainPairView  │
│ (React)     │  {email, password}         │ (backend-admin)           │
│             │ ◄───────────────────────── │                            │
└─────┬──────┘  {access, refresh,          │ AdminTokenObtainPairSerializer
      │          role, email, full_name}   │   → authenticate(email,pw) │
      │                                    │   → User.role, admin_profile
      │ localStorage.setItem               └──────────────────────────┘
      ▼
┌────────────┐   Authorization: Bearer <access>
│ AuthContext │ ─────────────────────────► GET /api/auth/me/  (hidratación al montar)
│ (React)     │
│             │ ─────────────────────────► POST /api/auth/refresh/  (auto, antes de expirar)
│             │ ─────────────────────────► POST /api/auth/logout/   ({refresh} → blacklist)
└─────┬──────┘
      │  role === 'admin'?
      ▼
┌────────────┐  sí → PrivateRoute renderiza BiomedShell (misma SPA)
│ roleRedirect│  analista → window.location.href a frontend-clinic /clinic/samples
│             │  supervisor → window.location.href a /supervisor.html (legacy)
└────────────┘
```

Namespace de secreto: `AUTH_ADMIN_JWT_SECRET` (nuevo, independiente de `AUTH_BRIDGE_SECRET` y `AUTH_CLINIC_SECRET` — ver ADR-0017 D2).

## 3. Componentes backend (`backend-admin/apps/users/`)

| Componente | Responsabilidad |
|---|---|
| `auth_serializers.py::AdminTokenObtainPairSerializer` | Extiende `TokenObtainPairSerializer`; agrega `role`/`email`/`full_name` al body de respuesta |
| `auth_serializers.py::MeSerializer` | Serializa `request.user` + `admin_profile.full_name` opcional |
| `auth_views.py::LoginView` | `POST /login/`, wrapper de `TokenObtainPairView` con el serializer custom + throttle scope `login` |
| `auth_views.py::LogoutView` | `POST /logout/`, blacklistea el `refresh` recibido |
| `auth_views.py::MeView` | `GET /me/`, `IsAuthenticated`, devuelve datos del usuario actual |
| `auth_urls.py` | Monta los 4 endpoints (`refresh/` reusa `TokenRefreshView` de librería sin wrapper) |
| `factories.py::UserFactory` (extendida) | Factory de `User` con `set_password()` real, exclusiva para tests |

Settings (`admin_backend/settings.py`): `INSTALLED_APPS` +`rest_framework_simplejwt`, +`rest_framework_simplejwt.token_blacklist`; bloque `SIMPLE_JWT`; `DEFAULT_AUTHENTICATION_CLASSES` +`JWTAuthentication` (aditivo, `TokenAuthentication` se mantiene).

## 4. Componentes frontend (`frontend-admin/src/admin/`)

| Componente | Responsabilidad |
|---|---|
| `auth/authClient.ts` | `login()`/`logout()`/`refresh()`/`me()`/`getAccessToken()`/`isAuthenticated()` contra `/api/auth/*` |
| `auth/AuthContext.tsx` | `AuthProvider`/`useAuth()`: estado de tokens+usuario, hidratación vía `/me`, auto-refresh por `setTimeout` antes de expirar |
| `auth/PrivateRoute.tsx` | Guard de rutas con `allowedRoles`; redirige a `/login` o fuera vía `roleRedirect` |
| `auth/roleRedirect.ts` | `getRedirectForRole(role)` — implementa la tabla D7 de ADR-0017 |
| `pages/LoginPage.tsx` | Replica el modal de `index.html` como página de ruta completa (ver SPEC-010 §2 nota de adaptación de layout) |
| `components/BiomedNavbar.tsx` (modificado) | Agrega botón "Salir" (`fa-sign-out-alt`, replica `configuracion.html:728`) |
| `App.tsx` (modificado) | `BrowserRouter` + rutas `/login` (pública) y `/*` (`PrivateRoute allowedRoles={['admin']}` envolviendo el bootstrap MSW + `BiomedShell` ya existente, sin tocar su contenido interno) |
| `msw/handlers.ts` (modificado) | Handlers de los 4 endpoints con un usuario demo seed, para que `npm run dev:msw` funcione punta a punta |

## 5. Riesgos (ver también ADR-0017 §Consecuencias)

| Riesgo | Mitigación |
|---|---|
| Usuarios `AdminUser` creados vía CRUD no tienen `User` de auth vinculado ni password | Documentado como limitación conocida (ADR-0017 D9) — fuera de alcance de este DD, requiere feature propio de provisión de credenciales |
| Redirect cross-app a `frontend-clinic`/`supervisor.html` sin sesión propagada | Documentado como gap conocido (ADR-0017 D7) — no se simula una integración SSO que no existe |
| Cuarto namespace de secreto JWT aumenta superficie operacional | Mismo patrón ya aceptado en ADR-0015; gestión de secretos vía `.env` gitignored, `required=True` en `env()` |

## 6. Plan de implementación

Ver plan file `C:\Users\Qubits\.claude\plans\sorted-seeking-thompson.md` — tabla de tareas T1-T15. Este DD corresponde a T3; T4-T11 son el código; T12 tests; T13 verificación E2E; T14-T15 trazabilidad y commit.

## 7. Trazabilidad

- **Sube a:** BRD §3.2 → `index.html` → ADR-0017 → SPEC-010 → este DD.
- **Baja a:** código en `backend-admin/apps/users/{auth_serializers,auth_views,auth_urls}.py` + `frontend-admin/src/admin/{auth,pages}/*`.
- **Impacta:** `docs/PROMPT_MAPPING.md`, `docs/DTI.md`, `AGENTS.md §5`, `docs/AUTH_BRIDGE.md` (nota de desactualización).

## Notas

- Este DD **no reemplaza** el exchange F0 (`docs/AUTH_BRIDGE.md`) ni el SimpleJWT de `backend-clinic` (ADR-0015); coexisten como mecanismos independientes por bounded context/propósito.
- Decisiones de arquitectura están en ADR-0017, no se repiten aquí en detalle — este documento es la vista de componentes, el ADR es la vista de decisión.
