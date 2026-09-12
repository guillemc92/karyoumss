---
id: ADR-0017
title: Sistema de Autenticación (Login) — backend-admin como autoridad JWT única
date: 2026-07-12
status: accepted
supersedes: ninguno (extiende ADR-0013, deja sin tocar ADR-0015)
related: [ADR-0011, ADR-0012, ADR-0013, ADR-0015, docs/AUTH_BRIDGE.md, SPEC-010, AGENTS.md §2.3/§3 RN-06]
fase: desarrollo
autor: Ing. Guillermo Mamani Chambi
---

# ADR 0017: Sistema de Autenticación (Login) — backend-admin como autoridad JWT única

## Contexto

El arquitecto pidió un módulo de Login real (Django+DRF+SimpleJWT / React+TS) con `CustomUser.role`, endpoints `POST /api/auth/login/`, `POST /api/auth/logout/`, `POST /api/auth/refresh/`, `GET /api/auth/me/`, `AuthContext`, `PrivateRoute` y redirecciones por rol, bajo el mismo flujo Antirracionalización ya aplicado en ADR-0016.

Al aplicar el flujo de verificación documental (Pasos 1-3, agente Explore + lectura directa del HTML), se confirmó:

1. **El HTML Contract existe** (`index.html`, raíz del repo, líneas 724-811): modal `#loginModal` con header "BIOMED UMSS / Iniciar Sesión", selector de 3 roles en tabs (`citogenetista`/`supervisor`/`admin`), campos "Usuario"/"Contraseña", banner de error `#loginError`, botón "Ingresar al Sistema". Hoy valida contra un mapa de credenciales hardcodeado en JS y hace `localStorage.setItem('biomed_user', ...)` — no hay backend real. No se activa el gate de detención del Paso 3.
2. **Existen tres sistemas de auth en paralelo, ninguno conectado a una pantalla de login real:**
   - `backend-admin` tiene `CustomUser` real (`apps/users/models.py:99-130`) con campo `role` (`ROLE_CHOICES = admin/analista/supervisor`, ya usado en producción por `AdminUserViewSet`), pero su único mecanismo de auth es `POST /api/admin/auth/exchange` (`apps/users/views.py:158-192`), que espera un JWT de un **FastAPI clínico que no existe commiteado en este repo** (confirmado también por ADR-0015 §Contexto punto 4). `docs/AUTH_BRIDGE.md` (no trackeado en git) describe ese puente pero quedó desactualizado por ADR-0015, que introdujo un tercer namespace de token sin reusarlo.
   - `backend-clinic` tiene SimpleJWT nativo funcionando (`TokenObtainPairView`/`TokenRefreshView` de librería, `clinic_backend/urls.py:7-8`), pero usa el `User` por defecto de Django **sin campo `role`**.
   - Ningún frontend (`frontend-admin`, `frontend-clinic`) tiene `AuthContext`, `PrivateRoute` ni componente `Login`. `frontend-admin` ni siquiera tiene `react-router-dom` instalado — es una SPA de una sola vista montada directamente sobre `BiomedShell` (`src/App.tsx:143-147`).
3. **Discrepancia de vocabulario de rol:** el prompt del arquitecto pide `admin`/`especialista`/`supervisor`. Ningún documento del repo (BRD, FSD, AGENTS.md) ni el código (`ROLE_CHOICES`) usa "especialista" — todos usan `analista` (o "Analista Citogenetista"/"citogenetista" como sinónimos de etiqueta).
4. **Los endpoints pedidos (`/api/auth/*`, sin prefijo de bounded context) no encajan literalmente en ninguno de los dos backends existentes**, que están deliberadamente separados por namespace desde ADR-0013/ADR-0015.

Estas 4 tensiones se resolvieron con el arquitecto vía `AskUserQuestion` (evidencia: 3 preguntas, 3 respuestas explícitas, todas la opción recomendada):

- **Backend-admin es la autoridad única** del nuevo login unificado. Se extiende (no se reemplaza) con SimpleJWT + blacklist + `/me`, reutilizando el único `CustomUser`+`role` real que ya existe en el repo. `backend-clinic` sigue con su propio SimpleJWT sin tocar.
- **Vocabulario de rol: `analista`** (se descarta "especialista").
- **Redirecciones post-login:** `admin` → raíz `frontend-admin`; `analista` → `frontend-clinic` `/clinic/samples`; `supervisor` → `supervisor.html` legacy (gap conocido, documentado en D7).

Este ADR fija el diseño resultante.

## Decisión

### D1 — `backend-admin` como autoridad única de `/api/auth/*`

Los 4 endpoints (`login/`, `logout/`, `refresh/`, `me/`) viven en `backend-admin/apps/users/` (mismo app que ya gestiona `CustomUser`+`role`) y se montan en `admin_backend/urls.py` bajo `path('api/auth/', include('apps.users.auth_urls'))` — namespace neutro, distinto de `/api/admin/*` (CRUD de cuentas) y de `/api/clinic/*` (muestras). `backend-clinic` no se modifica.

### D2 — SimpleJWT se agrega, no reemplaza TokenAuthentication

`rest_framework_simplejwt.authentication.JWTAuthentication` se **agrega** a `DEFAULT_AUTHENTICATION_CLASSES`, antes de `TokenAuthentication` (que se deja intacta para no romper `auth_exchange`, que sigue emitiendo DRF `Token`). DRF prueba las clases de autenticación en orden hasta que una produzca una credencial válida — es aditivo, no hay regresión sobre el exchange F0 existente.

Nuevo secreto propio `AUTH_ADMIN_JWT_SECRET` (env, `required=True`), **independiente** de `AUTH_BRIDGE_SECRET` (exchange F0) y de `AUTH_CLINIC_SECRET` (`backend-clinic`, ADR-0015). Esto crea un **cuarto namespace de token** en el sistema, mismo patrón de aislamiento ya establecido por ADR-0015 §Decisiones técnicas #5 ("tres namespaces de token distintos, ninguno comparte secreto").

`SIMPLE_JWT`: `ACCESS_TOKEN_LIFETIME=30min`, `REFRESH_TOKEN_LIFETIME=1 día`, `ROTATE_REFRESH_TOKENS=True`, `BLACKLIST_AFTER_ROTATION=True`, `ALGORITHM=HS256` — mismos valores que `backend-clinic` (ADR-0015) para consistencia operativa entre bounded contexts.

### D3 — Logout real vía blacklist

`rest_framework_simplejwt.token_blacklist` se añade a `INSTALLED_APPS` (trae sus propias migraciones — no se toca el modelo `User` ni `AdminUser`). `POST /api/auth/logout/` recibe `{"refresh": "..."}` y lo blacklistea (`RefreshToken(token).blacklist()`); un intento posterior de `refresh/` con ese token devuelve `401`.

### D4 — `AdminTokenObtainPairSerializer`

Extiende `rest_framework_simplejwt.serializers.TokenObtainPairSerializer`. Como `User.USERNAME_FIELD = 'email'` ya está fijado (ADR-0012/modelo existente), el serializer de librería ya acepta `{"email": ..., "password": ...}` sin cambios — solo se sobreescribe `validate()` para agregar al **body de la respuesta** (no solo como claim JWT) los campos `role`, `email`, `full_name` (de `AdminUser.full_name` vía `user.admin_profile.full_name` si existe, `null` si el `User` no tiene `AdminUser` vinculado — ver D9). El frontend necesita el rol inmediatamente tras el login para decidir el redirect sin decodificar el JWT.

Respuesta `200`:
```json
{"access": "...", "refresh": "...", "role": "admin", "email": "demo_admin@biomed.umss.bo", "full_name": "Demo Admin"}
```
Falla (`401`): `{"detail": "Credenciales inválidas"}` — mensaje genérico, no distingue "usuario no existe" de "password incorrecta" (evita enumeración de usuarios, RN de seguridad Paso 9). `is_active=False` (usuario desactivado vía soft-delete de `AdminUser.soft_delete()`, que ya sincroniza `user.is_active=False`) produce el mismo `401` genérico — comportamiento heredado gratis del `ModelBackend`/`authenticate()` de Django, sin código adicional.

### D5 — `GET /api/auth/me/`

`IsAuthenticated`. Devuelve `{email, role, full_name, username}` desde `request.user` (+ `admin_profile.full_name` si existe). Usado por el frontend para hidratar la sesión al recargar la página (el `access` token vive en `localStorage`, no en una cookie — al montar la app se valida contra `/me` en vez de confiar ciegamente en el token guardado).

### D6 — Vocabulario de rol: `analista`

Se descarta "especialista" del prompt original. `ROLE_CHOICES` no cambia: `admin`/`analista`/`supervisor`. Consistente con BRD §3.2, FSD §3, AGENTS.md §2.3 y el código ya en producción.

### D7 — Redirecciones por rol (`roleRedirect.ts`)

| Rol | Destino | Mecanismo |
|---|---|---|
| `admin` | Raíz de `frontend-admin` (ya sirve `BiomedShell`) | Interno — `PrivateRoute allowedRoles={['admin']}` renderiza el shell existente sin navegación de página |
| `analista` | `frontend-clinic` `/clinic/samples` | `window.location.href` a `${VITE_CLINIC_APP_URL}/clinic/samples` (cross-app, apps en puertos Vite distintos) |
| `supervisor` | `supervisor.html` (legacy, raíz del repo) | `window.location.href` a `/supervisor.html` |

**Gap documentado, no resuelto en este ADR:** no existe módulo React de Supervisor (ni en `frontend-admin` ni en `frontend-clinic`) — el destino es el HTML estático legacy, sin sesión JWT (mismo problema estructural que tenía `index.html` antes de este feature). Construir un módulo Supervisor real está fuera de alcance de este ADR — no se pidió y no se inventa aquí.

**Gap documentado, no resuelto en este ADR:** el redirect a `frontend-clinic` es una navegación de página completa sin propagación de sesión (cross-backend SSO). El `analista` llega a `/clinic/samples` sin un token de `backend-clinic` válido — deberá autenticarse ahí también (o usar el modo demo MSW que ya existe en `frontend-clinic`). Esto es el mismo criterio YAGNI que ya dejó pendiente ADR-0015 línea 104 ("doble auth bridge... decisión pospuesta hasta que aparezca la necesidad"); resolverlo requeriría un ADR propio de SSO cross-backend, no forma parte de este feature.

### D8 — Selector de rol del modal: cosmético, no funcional

`LoginPage.tsx` replica visualmente los 3 tabs de rol del `index.html` (mismas clases, mismo layout, mismos íconos) — preserva el contrato de UI exactamente. Pero el submit solo envía `{email, password}`; el tab seleccionado **no se envía al backend ni se usa para validar nada**. El rol que decide el redirect es el que devuelve `AdminTokenObtainPairSerializer` en la respuesta real, no la selección manual del usuario.

Esto es la misma clase de adaptación que ADR-0016 D8 (modal de IA conectado a datos reales en vez de temporizador falso): se preserva la apariencia, se corrige la semántica que dependía de la ausencia de un backend real. En el `index.html` original el selector era necesario porque no había forma de que el sistema supiera el rol del usuario; con un backend real, el rol lo determina la base de datos, no una elección de UI. Mantener el selector como gate funcional (comparar tab elegido vs. rol real) sería **inventar una regla de negocio no documentada en ningún lado** — se descarta explícitamente esa opción.

### D9 — Provisión de password: fuera de alcance

El CRUD `AdminUsersPanel` (`frontend-admin`, ya entregado con cobertura RN-09 cerrada) y su service `create_admin_user()` (`backend-admin/apps/users/services.py:17-45`) **no se modifican**: siguen creando `AdminUser` sin `User` de auth vinculado (`user=None`) ni password. Este ADR no agrega un flujo de "invitación por email"/"set password" — no fue pedido, y añadirlo expandiría el alcance de un feature ya cerrado sin ADR propio.

Usuarios con login real (capaces de usar este módulo) se provisionan **fuera de este feature**: directamente vía Django shell/`User.objects.create_user(email=..., password=..., role=...)` o `set_password()`. Se documenta como limitación conocida. La factory de tests (`apps/users/factories.py`) se extiende con una `UserFactory` que sí setea password, exclusivamente para tests — no reemplaza ningún flujo de producción.

## Justificación

- **Backend-admin como autoridad única** es la opción de menor invención: reutiliza el único `CustomUser`+`role` real y probado del repo, en vez de construir uno nuevo desde cero en `backend-clinic` (que usa el `User` por defecto de Django) o levantar un tercer backend de identidad (blast radius mucho mayor, requeriría derogar ADR-0013 y ADR-0015).
- **Namespace de secreto propio (`AUTH_ADMIN_JWT_SECRET`)** sigue el patrón ya validado por ADR-0015: aislar el radio de explosión de una fuga de secreto a un solo bounded context.
- **Selector de rol cosmético (D8)** evita inventar una regla de autorización nueva; el sistema real de autorización es, y sigue siendo, el campo `role` en base de datos — exactamente lo que la migración de "demo con localStorage" a "login real" está diseñada para corregir.

## Consecuencias

### Positivas
- Cierra el gap real detectado en el flujo de verificación (Paso 2): existe ahora un login funcional, con JWT real, logout con blacklist y `/me`, donde antes solo había un modal de demo con credenciales en JS.
- `frontend-admin` gana enrutamiento real (`react-router-dom`) y un guard de rutas (`PrivateRoute`), infraestructura reutilizable para features futuros de esa SPA.
- El `CustomUser.role` ya existente (antes solo alimentado por el exchange F0, nunca ejercitado end-to-end) pasa a tener un flujo de autenticación real y testeado.

### Negativas
- Cuarto namespace de token JWT en el sistema (`AUTH_BRIDGE_SECRET`, `AUTH_CLINIC_SECRET`, ahora `AUTH_ADMIN_JWT_SECRET`, más el DRF `Token` legacy) — aumenta la superficie operacional de gestión de secretos.
- El redirect a `frontend-clinic`/`supervisor.html` no propaga sesión — UX fragmentada entre bounded contexts hasta que exista un ADR de SSO cross-backend (fuera de alcance).
- La provisión de password para usuarios reales queda manual (D9) — no apto para producción sin un ADR/feature posterior de gestión de credenciales.

### Neutras
- `POST /api/admin/auth/exchange` (F0) no se elimina ni se deprecia formalmente; queda como mecanismo secundario sin uso activo desde este ADR en adelante. Decidir su remoción requiere un ADR propio.
- El vocabulario "especialista" del prompt original queda documentado aquí como descartado (D6), para que una futura sesión no lo reintroduzca sin revisar este ADR.

## Tensión con reglas del proyecto y cómo se resuelve

| Regla | Tensión | Resolución |
|---|---|---|
| **RN-06** (segregación analista/supervisor) | El login determina el rol que gobierna permisos aguas abajo | El rol viene de `CustomUser.role` en BD, no de una selección de UI (D8) — es la fuente de verdad ya usada por `IsAdminRole` y el resto del bounded context admin. |
| **AGENTS §2.3** (Admin TI sin acceso a datos clínicos) | `PrivateRoute allowedRoles={['admin']}` protege `frontend-admin` | Un `analista`/`supervisor` autenticado que caiga en `frontend-admin` es redirigido fuera inmediatamente (D7), nunca ve `BiomedShell`. |
| **Seguridad — no exponer información sensible** (Paso 9 del prompt) | Mensajes de error de login pueden filtrar existencia de cuentas | `401` genérico "Credenciales inválidas" para email inexistente, password incorrecta y usuario inactivo — sin distinción (D4). |
| **No cambiar arquitectura existente** (Antirracionalización) | Backend-admin gana un mecanismo de auth nuevo (SimpleJWT) | Es aditivo sobre `DEFAULT_AUTHENTICATION_CLASSES` (D2); `TokenAuthentication`/`auth_exchange` no se tocan ni se rompen. |
| **No modificar UX sin ADR** | El selector de rol del modal deja de ser funcional | D8 documenta explícitamente el porqué y lo encuadra como la misma clase de ajuste ya precedida por ADR-0016 D8. |

## Alternativas evaluadas y rechazadas

**A1. Extender `backend-clinic` como autoridad de login.** Rechazada por el arquitecto: ya tiene login/refresh reales pero necesitaría construir `CustomUser`+`role` desde cero (hoy usa el `User` por defecto de Django), mientras que `backend-admin` ya tiene ese modelo maduro y probado.

**A2. Backend de identidad nuevo (`backend-auth`, Identity Provider dedicado).** Rechazada: arquitectónicamente más "correcta" a largo plazo, pero requeriría derogar ADR-0013 **y** ADR-0015 (que fijaron namespaces de token separados a propósito) y migrar la validación en ambos backends existentes — blast radius desproporcionado para este feature.

**A3. Mantener la fragmentación actual, implementar solo `/api/clinic/auth/*`.** Rechazada: no cumple el requisito explícito del arquitecto de endpoints `/api/auth/*` sin prefijo de contexto, y no resuelve el caso de uso real (el modal de `index.html` necesita decidir entre 3 destinos de apps distintas, no solo una).

**A4. Selector de rol como gate de autorización real (comparar tab elegido vs. rol de BD, bloquear si no coincide).** Rechazada (ver D8): sería inventar una regla de negocio no documentada en ningún BRD/FSD/AGENTS.md — el sistema real de autorización es el campo `role`, punto.

## Trazabilidad

- **Sube a:** BRD §3.2 (Actores) → FSD §3 (Actores y roles) / FSD §9 (ruta `/login` documentada) → ADR-0011 (rol Administrador) → `index.html` (HTML Contract) → **este ADR-0017**.
- **Genera:** `docs/specs/SPEC-010-autenticacion-login.md`, `docs/design/DD-AUTH-001.md`, código en `backend-admin/apps/users/` y `frontend-admin/src/admin/auth/`.
- **Impacta:**
  - `docs/PROMPT_MAPPING.md` (nueva entrada `PM-AUTH-001`)
  - `docs/DTI.md` (registro de este ADR en §21)
  - `AGENTS.md §5` (tabla de ADRs, agregar 0017)
  - `docs/AUTH_BRIDGE.md` (nota de cabecera: desactualizado para el flujo de login primario, el exchange F0 que describe sigue existiendo en código pero deja de ser el mecanismo recomendado)

## Notas

- Este ADR **no deroga** ADR-0013 ni ADR-0015; los extiende (admin gana SimpleJWT además de TokenAuth) y los deja intactos (clinic no se toca) respectivamente.
- Este ADR **no resuelve** el SSO cross-backend admin↔clinic ni la ausencia de módulo Supervisor — ambos quedan documentados como gaps conocidos (D7), no simulados ni ocultados.
- Rama de trabajo: `feature/clinic-django-stack` (continuación). NO pushear a `main`. PR a `release/2.0.0`.
