---
id: SPEC-010
titulo: "Sistema de Autenticación (Login) — JWT unificado en backend-admin"
bounded_context: admin
documento_driving: ADR-0017
stack:
  backend: "Django 5 + DRF 3.15 + djangorestframework-simplejwt 5.3 + SQLite (dev)"
  frontend: "React 18 + Vite 5 + TypeScript 5 + React Router 6"
  ui_contract: "index.html (raíz del repo, modal #loginModal líneas 724-811)"
version: 0.1
fecha: "2026-07-12"
autor: "Ing. Guillermo Mamani Chambi"
estado: proposed
agents_conformance: "§11 (PR a release/2.0.0), §2.3 (Actores y Roles), RN-06"
refs:
  - "ADR-0017 (backend-admin como autoridad JWT única)"
  - "ADR-0011 (Rol Administrador)"
  - "ADR-0013 (Stack Django+React admin)"
  - "ADR-0015 (SimpleJWT independiente en backend-clinic, precedente de namespace)"
  - "RN-06, RN-09"
---

# SPEC-010 — Sistema de Autenticación (Login)

> Implementa el flujo de login descrito en el modal `#loginModal` de `index.html`,
> conectándolo a un `CustomUser`+JWT real en `backend-admin` según ADR-0017.
> Reemplaza el mecanismo de credenciales hardcodeadas en JS + `localStorage.setItem('biomed_user', ...)`.

## §0. Contexto y motivación

Hoy no existe ningún login real conectado a un backend: `index.html` valida contra un mapa de credenciales embebido en JavaScript. `backend-admin` tiene un `CustomUser` con `role` ya maduro (usado por el CRUD de usuarios), pero sin mecanismo de login por password. Esta spec traduce el contrato de UI del modal a un contrato técnico Django/React con JWT real, logout con blacklist, y redirecciones por rol hacia las 3 aplicaciones del sistema (`frontend-admin`, `frontend-clinic`, `supervisor.html` legacy).

## §1. Alcance y no-alcance

### Incluye
- 4 endpoints en `backend-admin`: `POST /api/auth/login/`, `POST /api/auth/logout/`, `POST /api/auth/refresh/`, `GET /api/auth/me/`.
- `LoginPage.tsx` en `frontend-admin` replicando el modal de `index.html` (header, selector de rol cosmético, campos usuario/contraseña, banner de error, submit).
- `AuthContext`/`useAuth()` con persistencia en `localStorage`, hidratación al montar vía `/me`, refresh automático antes de expirar el `access` token.
- `PrivateRoute` con soporte de `allowedRoles`.
- Redirección post-login por rol (D7 de ADR-0017): `admin` se queda en `frontend-admin`; `analista`/`supervisor` navegan fuera vía `window.location.href`.
- Botón "Salir" en `BiomedNavbar` (replica `configuracion.html:728`), logout real con blacklist del refresh token.

### NO incluye
- SSO cross-backend (que el token de `backend-admin` autentique además contra `backend-clinic`) — gap documentado en ADR-0017 D7, fuera de alcance.
- Módulo React de Supervisor — el redirect apunta al `supervisor.html` legacy, sin sesión propagada (gap documentado).
- Flujo de alta/invitación de password para `AdminUser` creados vía CRUD — ADR-0017 D9, fuera de alcance.
- Cambios en `backend-clinic`/`frontend-clinic` — no se tocan en este feature.
- Recuperación de contraseña ("¿olvidó su contraseña?") — no está en el modal HTML original, no se inventa.

## §2. Mapeo campo-por-campo: HTML → contrato JSON

### Modal de login (`index.html` líneas 724-750)

| Elemento HTML (`id`) | Tipo HTML | Campo en request | Comportamiento nuevo |
|---|---|---|---|
| `roleSelector` / `.role-option[data-role]` | tabs clickeables (citogenetista/supervisor/admin) | — (no se envía) | Cosmético (ADR-0017 D8) — preselección visual únicamente, no viaja en el request ni valida contra el rol real |
| `loginUser` | `input type="text"` | `email` | Se etiqueta "Usuario" en UI pero el valor viaja como `email` (consistente con `USERNAME_FIELD='email'` ya fijado en `backend-admin`) |
| `loginPass` | `input type="password"` | `password` | Sin cambios de comportamiento visual |
| `loginError` | `div.alert-error` (oculto por defecto) | — | Se muestra en cualquier fallo de login (credenciales inválidas, usuario inactivo) — mensaje genérico, no distingue causa |
| botón `.login-submit` "Ingresar al Sistema" | `button onclick` | dispara `POST /api/auth/login/` | Antes llamaba a `handleLogin()` (comparación JS contra mapa hardcodeado) |
| `close-modal` (×) | — | — | No aplica — `LoginPage` es una página de ruta completa (`/login`), no un modal superpuesto sobre un landing page (ver Nota UX §3) |

### Nota de adaptación de layout (no es una desviación del contrato, es la única forma de que la UI funcione como ruta)

El `#loginModal` en `index.html` es un overlay que aparece sobre una landing page de marketing. Esa landing page (hero, secciones "El Problema"/"La Solución", roles, CTA, footer) **no forma parte del alcance de este feature** — no fue pedida, y replicarla sería expandir el alcance sin ADR. `LoginPage.tsx` porta únicamente la tarjeta del modal (`.login-modal` con su `.modal-header`/`.modal-body`) como el contenido completo de la ruta `/login`, centrada en viewport completo con el mismo fondo/paleta de colores (`--blue-primary`, etc., ya definidos en `tokens.css`). Layout, colores, tipografía y campos de la tarjeta se replican exactamente; lo que cambia es que ya no es un overlay `position: fixed` sobre otro contenido, sino el contenido único de la ruta.

## §3. Wireframe ASCII — `LoginPage`

```
┌──────────────────────────────────────────┐
│                                            │
│         ┌──────────────────────┐         │
│         │   🧬 BIOMED UMSS      │         │
│         │   Iniciar Sesión      │         │
│         ├──────────────────────┤         │
│         │ ⚠️ Credenciales       │ (oculto │
│         │    incorrectas        │  hasta  │
│         │                        │  error) │
│         │ [Citogenetista][Supervisor][Admin]│
│         │        (cosmético, no gatea)     │
│         │                        │         │
│         │ USUARIO                │         │
│         │ [________________]     │         │
│         │                        │         │
│         │ CONTRASEÑA             │         │
│         │ [••••••••••••••]      │         │
│         │                        │         │
│         │ [Ingresar al Sistema]  │         │
│         └──────────────────────┘         │
│                                            │
└──────────────────────────────────────────┘
```

## §4. Gherkin

### UC-A-001: Login exitoso

```gherkin
Feature: Login con credenciales válidas
  Como usuario del sistema (admin/analista/supervisor)
  Quiero autenticarme con usuario y contraseña
  Para acceder a la aplicación que corresponde a mi rol

  Scenario: Login exitoso como admin
    Given estoy en /login sin sesión activa
    And existe un User con email "demo_admin@biomed.umss.bo" y role="admin"
    When ingreso email y password correctos y hago click en "Ingresar al Sistema"
    Then POST /api/auth/login/ retorna 200 con {access, refresh, role: "admin", email, full_name}
    And los tokens se guardan en localStorage
    And permanezco en frontend-admin, veo BiomedShell (PrivateRoute allowedRoles=['admin'])

  Scenario: Login exitoso como analista redirige fuera
    Given existe un User con role="analista"
    When ingreso credenciales correctas
    Then el login retorna 200 con role: "analista"
    And la app navega (window.location.href) a "${VITE_CLINIC_APP_URL}/clinic/samples"

  Scenario: Login exitoso como supervisor redirige a legacy
    Given existe un User con role="supervisor"
    When ingreso credenciales correctas
    Then la app navega a "/supervisor.html"
```

### UC-A-002: Login fallido

```gherkin
Feature: Rechazo de credenciales inválidas
  Scenario: Password incorrecta
    When ingreso un email válido con password incorrecta
    Then POST /api/auth/login/ retorna 401 {"detail": "Credenciales inválidas"}
    And se muestra el banner "⚠️ Credenciales incorrectas"
    And ningún token se guarda

  Scenario: Email inexistente
    When ingreso un email que no existe en el sistema
    Then retorna 401 con el MISMO mensaje genérico que password incorrecta
    And no se revela si el email existe o no (anti-enumeración)

  Scenario: Usuario desactivado (soft-delete vía AdminUser)
    Given el User asociado tiene is_active=False
    When ingreso credenciales correctas de ese usuario
    Then retorna 401 con el mismo mensaje genérico
```

### UC-A-003: Selector de rol es cosmético

```gherkin
Feature: El tab de rol seleccionado no gatea el login
  Scenario: Selecciono un tab distinto al rol real del usuario
    Given existe un User con role="admin" real en base de datos
    When en el modal selecciono el tab "Supervisor" (cosmético)
    And ingreso las credenciales correctas de ese usuario admin
    Then el login es exitoso igual (200)
    And el redirect usa el rol REAL devuelto por el backend ("admin"), no el tab elegido
```

### UC-A-004: Sesión — hidratación, refresh, logout

```gherkin
Feature: Ciclo de vida de la sesión
  Scenario: Recargar la página con sesión activa
    Given hay un access/refresh token válidos en localStorage
    When recargo la aplicación
    Then AuthContext llama GET /api/auth/me/ con el access token
    And si responde 200, la sesión se hidrata sin pedir login de nuevo

  Scenario: Access token expirado se refresca automáticamente
    Given el access token está a punto de expirar
    When el temporizador interno de AuthContext dispara el refresh
    Then POST /api/auth/refresh/ con el refresh token devuelve un access nuevo
    And la sesión continúa sin interrupción visible

  Scenario: Refresh token inválido o expirado
    When POST /api/auth/refresh/ devuelve 401
    Then la sesión se limpia (localStorage) y navego a /login

  Scenario: Logout
    Given tengo una sesión activa
    When hago click en "Salir" (BiomedNavbar)
    Then POST /api/auth/logout/ con {refresh} blacklistea el token
    And localStorage se limpia
    And navego a /login
    And un intento posterior de usar ese refresh token devuelve 401
```

### UC-A-005: Protección de rutas

```gherkin
Feature: PrivateRoute protege frontend-admin
  Scenario: Usuario no autenticado intenta acceder a la raíz
    Given no hay sesión activa
    When navego a "/" (frontend-admin)
    Then PrivateRoute redirige a "/login"

  Scenario: Usuario autenticado con rol no admin intenta acceder a frontend-admin
    Given tengo una sesión activa con role="analista"
    When navego a "/" (frontend-admin)
    Then PrivateRoute detecta que "analista" no está en allowedRoles=['admin']
    And redirige fuera vía roleRedirect (no muestra BiomedShell)
```

## §5. Contratos JSON completos

### `POST /api/auth/login/`

Request:
```json
{"email": "demo_admin@biomed.umss.bo", "password": "demo12345"}
```

Response 200:
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "role": "admin",
  "email": "demo_admin@biomed.umss.bo",
  "full_name": "Demo Admin"
}
```

Response 401:
```json
{"detail": "Credenciales inválidas"}
```

### `POST /api/auth/refresh/`

Request: `{"refresh": "..."}`
Response 200: `{"access": "...", "refresh": "..."}` (con `ROTATE_REFRESH_TOKENS=True`, viene refresh nuevo)
Response 401 (blacklisteado/expirado): `{"detail": "Token is invalid or expired", "code": "token_not_valid"}` (formato estándar de SimpleJWT, sin modificar)

### `POST /api/auth/logout/`

Request: `{"refresh": "..."}`
Response 205: sin body (blacklist exitoso)
Response 400: `{"detail": "Token inválido"}` (refresh ya blacklisteado o malformado)

### `GET /api/auth/me/`

Headers: `Authorization: Bearer <access>`
Response 200:
```json
{"email": "demo_admin@biomed.umss.bo", "role": "admin", "full_name": "Demo Admin", "username": "demo_admin@biomed.umss.bo"}
```
Response 401: `{"detail": "Authentication credentials were not provided."}` (estándar DRF)

## §6. Tabla de roles/permisos

| Endpoint | AllowAny | IsAuthenticated |
|---|:---:|:---:|
| `POST /api/auth/login/` | ✓ | — |
| `POST /api/auth/refresh/` | ✓ (valida el refresh token en el body, no requiere header) | — |
| `POST /api/auth/logout/` | — | ✓ (cualquier rol autenticado puede cerrar su propia sesión) |
| `GET /api/auth/me/` | — | ✓ |

No hay distinción de permisos por rol dentro de este módulo — cualquier rol válido puede loguearse, refrescar y cerrar sesión. La distinción de rol ocurre **después** del login, a nivel de `PrivateRoute`/`allowedRoles` en el frontend y de los permisos ya existentes (`IsAdminRole`, etc.) en los endpoints de negocio de cada bounded context.

## §7. Casos de aceptación (CA-1 a CA-8)

| # | Caso | Pasos | Esperado |
|---|---|---|---|
| **CA-1** | Login exitoso admin | POST login con credenciales admin válidas | 200, `role: "admin"`, tokens en localStorage, permanece en frontend-admin |
| **CA-2** | Login exitoso analista/supervisor | POST login con esos roles | 200, redirect cross-app vía `window.location.href` (no interno) |
| **CA-3** | Rechazo credenciales inválidas | Password incorrecta / email inexistente | 401 con mensaje genérico idéntico en ambos casos |
| **CA-4** | Selector de rol no gatea | Tab "Admin" seleccionado con credenciales de un `analista` real | Login 200 igual, redirect usa rol real (analista), no el tab |
| **CA-5** | Logout invalida el refresh | Logout → reintentar refresh con el mismo token | Primer logout 205, refresh posterior 401 |
| **CA-6** | Auto-refresh sin interrupción | Simular access token a punto de expirar | AuthContext dispara refresh antes de que falle una request real |
| **CA-7** | PrivateRoute bloquea rol no admin | Sesión con role="supervisor" navega a frontend-admin raíz | Redirige fuera, no renderiza BiomedShell |
| **CA-8** | Cobertura RN-09 | `pytest --cov-fail-under=90` backend-admin, `npm run test:coverage` frontend-admin | Ambos ≥90/88/90/90 |

## §8. Seguridad (Paso 9 del prompt)

- **No exponer información sensible:** mensajes de error de login idénticos para email inexistente, password incorrecta y usuario inactivo (§4 UC-A-002).
- **Expiración de tokens:** `access` 30 min, `refresh` 1 día, con rotación (`ROTATE_REFRESH_TOKENS`) y blacklist de tokens rotados (`BLACKLIST_AFTER_ROTATION`) — un `refresh` usado una vez no puede reutilizarse.
- **Logout real:** blacklist explícito, no solo borrado de `localStorage` en cliente (que no invalida un token robado).
- **Rate limiting:** scope `login` en `ScopedRateThrottle` (mismo mecanismo ya usado por `auth_exchange`), mitiga fuerza bruta.
- **Protección de rutas doble capa:** `PrivateRoute` en frontend (UX, evita parpadeo de contenido protegido) + `IsAuthenticated`/`IsAdminRole` ya existentes en backend (la defensa real, el frontend nunca es la única barrera).
- **Persistencia:** `localStorage` (mandato explícito del prompt), con la limitación conocida de exposición a XSS ya documentada en `docs/AUTH_BRIDGE.md` — aceptada como parte del stack pedido, no se introduce `httpOnly` cookie (cambiaría la arquitectura de transporte, fuera de alcance).

## §9. Métricas de cobertura RN-09

| Stack | Threshold | Comando |
|---|:---:|---|
| `backend-admin/` (incluye `auth_serializers.py`, `auth_views.py` nuevos) | ≥90% lines/branches/funcs/statements | `pytest --cov-fail-under=90` |
| `frontend-admin/` (incluye `src/admin/auth/*`, `LoginPage.tsx` nuevos) | ≥90% lines/funcs/statements, ≥88% branches | `npm run test:coverage` |

Archivos con mayor riesgo de cobertura baja:
- `AuthContext.tsx`: rama de auto-refresh por `setTimeout` (requiere `vi.useFakeTimers()`), rama de `/me` fallando al hidratar.
- `auth_serializers.py`: rama `admin_profile` ausente (User sin AdminUser vinculado, caso D9).

## §10. Trazabilidad

- **Sube a:** BRD §3.2 (Actores) → FSD §3 (Actores y roles) / FSD §9 (ruta `/login`) → `index.html` (HTML Contract) → **ADR-0017** → esta SPEC-010.
- **Genera:** código en `backend-admin/apps/users/` (auth_serializers, auth_views, auth_urls, tests) y `frontend-admin/src/admin/auth/` + `src/admin/pages/LoginPage.tsx`.
- **Impacta:** `docs/PROMPT_MAPPING.md` (`PM-AUTH-001`), `docs/DTI.md` (§21 registro ADR-0017), `docs/design/DD-AUTH-001.md` (nuevo), `docs/AUTH_BRIDGE.md` (nota de desactualización).

## Notas finales

- El selector de rol cosmético (§2, §4 UC-A-003) es la única desviación de comportamiento respecto al modal original — está documentada en ADR-0017 D8, no es un descuido.
- SSO cross-backend y módulo Supervisor real quedan fuera de alcance (ADR-0017 D7) — si se requieren, abrir un ADR nuevo.
