---
id: ADR-0020
title: SSO real — backend-admin como autoridad única de JWT para todo el sistema (deroga parcialmente ADR-0015 D5 y ADR-0017 D7)
date: 2026-07-20
status: accepted
supersedes: ninguno (deroga parcialmente ADR-0015 D5 y resuelve el gap diferido en ADR-0017 D7)
related: [ADR-0011, ADR-0013, ADR-0015, ADR-0017, ADR-0018, ADR-0019, docs/AUTH_BRIDGE.md]
fase: diseño
autor: Ing. Guillermo Mamani Chambi
---

# ADR-0020: SSO real — `backend-admin` como autoridad única de JWT

## Contexto

El arquitecto pidió explícitamente: **"debería ser un solo logueo y
con esa sesión navegar todo el sistema"**. Hoy eso no es posible.

### Estado actual (por qué esto es un cambio real, no cosmético)

El sistema tiene **dos backends con autenticación JWT completamente
independiente**, por diseño explícito de dos ADRs previos:

- **ADR-0015 D5**: `backend-clinic` emite su propio JWT con secreto
  propio (`AUTH_CLINIC_SECRET`), independiente del admin "por diseño".
- **ADR-0017 D7**: el login unificado (`backend-admin`) resuelve la
  autenticación *dentro* del bounded context admin, pero documenta
  explícitamente como gap diferido: *"redirecciones cross-app sin
  SSO"* — es decir, ya se sabía que este problema existía y se pateó
  para después. Este ADR es ese "después".

Estado técnico verificado en `settings.py` de ambos backends:

```python
# backend-admin/admin_backend/settings.py
SIMPLE_JWT = {'SIGNING_KEY': AUTH_ADMIN_JWT_SECRET, 'ALGORITHM': 'HS256', ...}
AUTH_USER_MODEL = 'users.User'  # CustomUser: email, role (analista/supervisor/admin)

# backend-clinic/clinic_backend/settings.py
SIMPLE_JWT = {'SIGNING_KEY': env('AUTH_CLINIC_SECRET'), 'ALGORITHM': 'HS256', ...}
# Sin AUTH_USER_MODEL propio → usa django.contrib.auth.User default
# (rol derivado de is_staff/is_superuser, ADR-0018 — NO tiene campo role)
```

Ambos usan HS256 (simétrico): **firma y verificación usan la misma
clave**. Un JWT firmado por `backend-admin` con `AUTH_ADMIN_JWT_SECRET`
solo puede validarse con esa misma clave — hoy `backend-clinic` no la
conoce ni la usa.

### Precedente ya construido: `auth_bridge.py` (exchange F0)

`backend-admin/apps/users/auth_bridge.py` ya resuelve un problema
estructuralmente idéntico, pero en la dirección opuesta: valida un JWT
externo (de FastAPI, con `AUTH_BRIDGE_SECRET` compartido), y hace
`get_or_create` de un `User` local a partir de los claims (`email`,
`role`). Este ADR **reutiliza el mismo patrón**, en la dirección
`backend-admin → backend-clinic`.

### Por qué `frontend-admin` es la SPA "canónica" para navegar todo

El arquitecto confirmó (sesión 2026-07-20): **login único en
`backend-admin`**, no en `backend-clinic`. Razón implícita: `backend-admin`
ya es la autoridad de identidad del sistema (`CustomUser` con `role`,
`AdminUser` con perfil, `django-auditlog`) — `backend-clinic` nunca
tuvo un concepto de "usuario" propio más allá de lo mínimo para que
Django funcione (ADR-0018 lo confirma: deriva rol de `is_staff`, sin
tabla de perfil).

## Decisión

### D1 — `backend-admin` firma, `backend-clinic` valida (no emite)

`backend-clinic` **deja de emitir su propio JWT** para el flujo de
usuario final. `TokenObtainPairView`/`TokenRefreshView` (SimpleJWT,
hoy montados en `backend-clinic/clinic_backend/urls.py`) se
**eliminan** del flujo de login humano. `backend-clinic` pasa a
**validar** JWT firmados por `backend-admin`, usando el mismo secreto
(`AUTH_ADMIN_JWT_SECRET`, compartido vía variable de entorno, mismo
mecanismo que `AUTH_BRIDGE_SECRET` ya usa para el exchange F0).

```python
# backend-clinic/clinic_backend/settings.py (cambio)
SIMPLE_JWT = {
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': env('AUTH_ADMIN_JWT_SECRET', required=True),  # compartido con backend-admin
    'AUTH_HEADER_TYPES': ('Bearer',),
    # ACCESS/REFRESH_TOKEN_LIFETIME deben coincidir con backend-admin
    # para que un token válido en uno no expire "antes" en el otro
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
}
```

**Por qué "validar, no re-emitir" y no un servicio de SSO externo
(ej. un IdP tipo Keycloak):** menor blast radius. Ya existen 2 apps
Django con SimpleJWT configurado; introducir un tercer servicio (IdP)
sería sobre-ingeniería para 2 backends internos del mismo producto,
sin requisito de terceros externos consumiendo el login. Ver
Alternativas A1.

### D2 — Mapeo de identidad: `AuthBridgeMiddleware` en `backend-clinic`

`backend-clinic` no tiene ni necesita el modelo `CustomUser` de
`backend-admin` — sigue usando `django.contrib.auth.User` (ADR-0018
no se deroga). Lo que cambia es **de dónde sale ese `User` local**:
en vez de que el usuario haga login directo contra `backend-clinic`,
un middleware/authentication class custom:

1. Recibe el JWT (firmado por `backend-admin`, mismo secreto).
2. Extrae claims: `email`, `role` (viene del token de `backend-admin`,
   valores `analista`/`supervisor`/`admin` — mismo vocabulario que
   `CustomUser.role`).
3. Hace `get_or_create(username=email)` sobre el `User` local de
   `backend-clinic` — **mismo patrón exacto** que
   `auth_bridge.py::exchange_fastapi_jwt()`, adaptado a Django
   `JWTAuthentication` en vez de a una vista de exchange explícita.
4. Sincroniza `is_staff`/`is_superuser` del `User` local a partir del
   `role` del claim (`admin`→ambos True, `supervisor`→`is_staff` True,
   `analista`→ninguno) — **esta sincronización es la pieza que hace
   que ADR-0018 (`role_for_user()` deriva de `is_staff`/`is_superuser`)
   siga funcionando sin cambios**, y que el RBAC de ADR-0019
   (`tiene_opcion()`, que usa `roles_for_user()`/`UsuarioGrupo`) siga
   operando sobre el mismo `User` de siempre.

```python
# backend-clinic/apps/samples/auth_bridge.py (nuevo, mismo patrón que backend-admin)
class SharedJWTAuthentication(JWTAuthentication):
    """Extiende JWTAuthentication de SimpleJWT: valida el token con el
    secreto compartido (ya lo hace JWTAuthentication vía settings), y
    además sincroniza el User local a partir de los claims del token
    de backend-admin (email, role) — mismo patrón que auth_bridge.py
    de backend-admin (exchange F0), aplicado aquí como authentication
    class en vez de vista explícita."""

    def get_user(self, validated_token):
        email = validated_token.get('email')  # claim custom (ver D3)
        role = validated_token.get('role')
        if not email:
            raise InvalidToken('Token sin claim email — no es de backend-admin')

        User = get_user_model()
        user, created = User.objects.get_or_create(
            username=email, defaults={'email': email},
        )
        is_staff = role in ('supervisor', 'admin')
        is_superuser = role == 'admin'
        if user.is_staff != is_staff or user.is_superuser != is_superuser:
            user.is_staff = is_staff
            user.is_superuser = is_superuser
            user.save(update_fields=['is_staff', 'is_superuser'])
        return user
```

### D3 — El JWT de `backend-admin` necesita el claim `role` embebido en el token (no solo en el body de login)

Hoy `AdminTokenObtainPairSerializer` agrega `role`/`email`/`full_name`
al **body** de la respuesta HTTP de login, pero el JWT en sí (el
`access` token) usa los claims default de SimpleJWT (`user_id`,
`exp`, `jti`, ...) — **no incluye `role` ni `email` dentro del token
firmado**. `backend-clinic` (D2) necesita leer `role`/`email` **del
token mismo** (no del body de login, que nunca ve). Se agrega
`get_token()` override:

```python
# backend-admin/apps/users/auth_serializers.py (extensión)
class AdminTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['email'] = user.email
        token['role'] = user.role
        return token
    # validate() existente no cambia — sigue agregando al body para el frontend
```

### D4 — `frontend-admin` es la única SPA de login; `frontend-clinic` deja de tener sesión propia

`frontend-clinic` **no vuelve a emitir/pedir login propio**. Su
`SessionProvider`/`authClient.ts` (que hoy llaman a
`/api/clinic/auth/login/`) se **eliminan** del flujo real (quedan
solo para el modo MSW de tests, si conviene mantenerlos ahí — a
decidir en el DD). El único login real de todo el sistema es el de
`frontend-admin` (`LoginPage.tsx`, ya existente). Tras el login,
`frontend-clinic` **lee el mismo `biomed.auth.access`** de
`localStorage` (mismo origen si se sirven desde el mismo dominio;
si son puertos distintos en dev, requiere resolver cross-origin
storage — ver Riesgos).

### D5 — Dos SPAs separadas, sesión compartida (decisión confirmada 2026-07-20)

`frontend-admin` (`:5173`) y `frontend-clinic` (`:5174`) **siguen
siendo dos aplicaciones React distintas** — no se fusionan. Lo que
cambia es que ambas leen el **mismo JWT** (`biomed.auth.access`) tras
un único login en `frontend-admin`. `frontend-clinic` deja de tener
su propio flujo de login real (D4).

**Por qué no fusionar (alternativa rechazada):** fusionar 2 proyectos
Vite ya maduros (17+11 archivos de tests, dependencias propias,
convenciones de estilo distintas — `frontend-admin` con Tailwind-like
utilities propias, `frontend-clinic` calcado 1:1 de `crudmuestra.html`)
es un esfuerzo de refactor grande sin necesidad funcional: el problema
real era "un solo login", no "una sola base de código React". Mantener
2 SPAs con sesión compartida resuelve el pedido con mucho menor blast
radius.

**El problema de origen cruzado (`localStorage` no se comparte entre
`:5173` y `:5174` en dev) se resuelve así:** en dev, ambos Vite dev
servers corren detrás de un único **proxy reverso** (ya existe la
costumbre de usar Vite `server.proxy` en este proyecto — ver
`vite.config.ts` de ambos frontends) sirviendo bajo el mismo origen
lógico (ej. `http://localhost:3000/admin/*` → `frontend-admin`,
`http://localhost:3000/clinic/*` → `frontend-clinic`), de forma que
`document.location.origin` sea el mismo para ambos y `localStorage`
se comparta nativamente. En producción esto es aún más simple: ambos
frontends ya se sirven típicamente detrás del mismo dominio con
distinto path/subpath (patrón común de este tipo de despliegues) — el
DD debe confirmar la configuración real de despliegue vigente antes
de asumir cuál.

## Justificación

- **Pedido explícito del arquitecto**, no una mejora especulativa:
  "un solo logueo, navegar todo el sistema" es un requisito de UX
  claro, y hoy es imposible sin este cambio.
- **Reutiliza infraestructura ya construida**: el patrón
  `auth_bridge.py` (exchange F0) ya resuelve exactamente este
  problema en la dirección FastAPI→backend-admin; este ADR es la
  misma idea, dirección backend-admin→backend-clinic.
- **No rompe ADR-0018/0019**: `role_for_user()`/`tiene_opcion()`
  siguen operando sobre `is_staff`/`is_superuser` del `User` local de
  `backend-clinic`, sin cambios — D2 solo cambia *cómo* ese `User` se
  crea/sincroniza, no la lógica de permisos que ya está construida y
  testeada (120 tests, commit `cf734c3`).

## Consecuencias

### Positivas
- Un solo login real para todo el sistema — resuelve el pedido
  explícito del arquitecto.
- Cierra el gap diferido documentado en ADR-0017 D7.
- Reutiliza el patrón `auth_bridge.py` ya probado en producción (F0),
  reduce riesgo de inventar un mecanismo nuevo.
- El RBAC de `backend-clinic` (ADR-0019, `tiene_opcion()`) sigue
  funcionando sin ningún cambio de código — solo cambia el origen del
  `User` sincronizado.

### Negativas
- **Deroga parcialmente ADR-0015 D5** ("JWT independiente del admin,
  por diseño") — el diseño original explícitamente valoraba la
  independencia; este ADR la revierte a pedido del arquitecto. Deja
  de haber "dos administradores posibles" (riesgo que ADR-0018
  §Negativas ya señalaba) — ahora hay una sola fuente de verdad de
  roles.
- **`backend-clinic` deja de ser autosuficiente para auth** — si
  `backend-admin` está caído, nadie puede autenticarse en
  `backend-clinic` tampoco (antes eran independientes). Es un
  acoplamiento nuevo real, no solo de UI.
- **Vida útil de tokens ya emitidos**: JWT firmados con
  `AUTH_CLINIC_SECRET` (viejo) dejan de validar en cuanto se despliega
  el cambio — cualquier sesión activa de `frontend-clinic` se
  invalida (aceptable: `ACCESS_TOKEN_LIFETIME` es 30 min, el impacto
  es un re-login, no pérdida de datos).
- Requiere sincronizar `ACCESS_TOKEN_LIFETIME`/`REFRESH_TOKEN_LIFETIME`
  entre ambos backends (hoy coinciden por casualidad: 30min/1día en
  ambos — deben mantenerse iguales deliberadamente de ahora en más,
  documentar en ambos `settings.py` con un comentario cruzado).
- Si `frontend-admin` y `frontend-clinic` corren en puertos distintos
  en dev (`:5173`/`:5174`), `localStorage` **no se comparte entre
  orígenes** — un JWT guardado por `frontend-admin` en `:5173` no es
  visible para JS corriendo en `:5174`. Esto es un problema real de
  D4 que el DD debe resolver (opciones: mismo dominio+path distinto en
  prod con proxy reverso, cookie compartida con dominio padre, o
  fusionar SPAs per D5(b) para que no haya 2 orígenes). **No asumido
  resuelto por este ADR** — el DD debe elegir explícitamente.

### Neutras
- `backend-admin` sigue siendo el único que emite tokens (login real);
  su lógica de negocio (`AdminUser`, `CustomUser.role`) no cambia.
- El exchange F0 (`auth_bridge.py`, FastAPI→backend-admin) no se toca
  — sigue siendo un mecanismo distinto para un caso distinto (FastAPI
  clínico legacy, si todavía se usa en algún flujo).

## Tensión con reglas del proyecto y cómo se resuelve

| Regla/ADR | Tensión | Resolución |
|---|---|---|
| **ADR-0015 D5** ("JWT independiente del admin, por diseño") | Este ADR lo revierte | Documentado explícitamente como derogación parcial; el arquitecto lo pidió con conocimiento del trade-off (menos independencia, más UX) |
| **ADR-0017 D7** (gap de SSO diferido) | Este ADR lo resuelve | Es la continuación natural, no una contradicción |
| **ADR-0018** (`role_for_user()` deriva de `is_staff`/`is_superuser`) | Riesgo de romperlo si se cambia el modelo de datos | D2 preserva el mecanismo exacto — solo cambia el *origen* de la sincronización de esos campos, la lógica de derivación de rol no se toca |
| **ADR-0019** (`tiene_opcion()`, RBAC jerárquico) | Riesgo de romper 120 tests existentes | D2 no modifica `models_rbac.py` ni `permissions.py` — el `User` que `UsuarioGrupo` referencia sigue siendo el mismo tipo de objeto, solo llega por otro camino |
| **No modificar ADRs sin uno nuevo** | Deroga ADR-0015 D5 | Este documento es el ADR nuevo requerido |

## Alternativas evaluadas

**A1. IdP externo (Keycloak, Auth0, etc.) como autoridad de identidad
para ambos backends.** Rechazada: sobre-ingeniería para 2 backends
internos del mismo producto sin consumidores externos del login;
introduce una pieza de infraestructura nueva (deploy, mantenimiento)
sin beneficio proporcional. El patrón `auth_bridge.py` ya resuelve el
problema con lo que existe.

**A2. `backend-clinic` sigue emitiendo su propio JWT, pero
`backend-admin` lo acepta también (bidireccional).** Rechazada:
duplica la superficie de mantenimiento (2 emisores en vez de 1) sin
necesidad — el arquitecto pidió explícitamente "un solo logueo", que
implica una sola autoridad, no dos que se validan mutuamente.

**A3. Cookie de sesión compartida (Django session, no JWT) en vez de
JWT compartido.** Rechazada: requeriría que ambos backends compartan
la misma tabla de sesiones (`django_session`) o un backend de sesión
común (ej. Redis compartido) — cambio de infraestructura mayor que
mantener JWT (stateless, ya funciona en ambos backends) y resolver
solo el secreto compartido.

**A4. No tocar backend, resolver "un solo logueo" solo en el
frontend con 2 llamadas de login transparentes (login contra admin,
y automáticamente un exchange contra clinic).** Es funcionalmente el
patrón F0 ya existente, aplicado al revés. Se descarta frente a D1-D3
porque mantener 2 emisores de JWT activos es más superficie que
tener 1 emisor + N validadores — el mismo argumento de A2.

## Trazabilidad

- **Sube a:** Pedido explícito del arquitecto (2026-07-20, "un solo
  logueo, navegar todo el sistema") → este ADR-0020.
- **Deroga parcialmente:** ADR-0015 D5, resuelve gap de ADR-0017 D7.
- **Genera:** `docs/design/DD-SSO-001.md` → cambios en
  `backend-clinic/clinic_backend/settings.py`,
  `backend-clinic/apps/samples/auth_bridge.py` (nuevo),
  `backend-admin/apps/users/auth_serializers.py` (extensión de
  `get_token()`), ajuste de proxy/config en `frontend-clinic`/
  `frontend-admin` (D5: 2 SPAs, sin fusionar).
- **Impacta:** `docs/PROMPT_MAPPING.md`, `docs/DTI.md`, `AGENTS.md` §5,
  `docs/AUTH_BRIDGE.md` (marcar como "ver también ADR-0020" para no
  confundir el exchange F0 legacy con este SSO nuevo).

## Notas

- **El prompt `docs/prompts/PROMPT-RBAC-ADMIN-UI.md`** (RBAC
  jerárquico portado a `backend-admin`) queda **pausado** hasta que
  este ADR se apruebe e implemente — decisión explícita del
  arquitecto (2026-07-20), para no construir una UI de gestión de
  permisos sobre un modelo de identidad que está a punto de cambiar.
- **No implica tocar `backend-clinic/apps/samples/models_rbac.py`
  ni `permissions.py`** (ADR-0019) — ese RBAC sigue intacto, solo
  cambia cómo llega el `User` sobre el que opera.
- Rama de trabajo: a definir — dado el alcance (2 backends + posible
  frontend), se recomienda `feature/sso-backend-admin`, separada de
  `feature/clinic-django-stack`.
- Este ADR es `proposed` — requiere sign-off del arquitecto,
  particularmente sobre D5, antes de generar el DD y tocar código.
