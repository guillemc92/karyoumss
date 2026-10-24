---
id: DD-SSO-001
titulo: "SSO real — backend-admin como autoridad única de JWT, 2 SPAs con sesión compartida"
producto: "BIOMED UMSS — Intelligent Karyotyping Platform"
grupo: "G04"
fsd_uc:
  - "FSD-UC-ADMIN-001"
  - "FSD-UC-CRUD-MUESTRA-001"
prd_refs:
  - "PRD-US-014"
adrs:
  - "ADR-0011"  # Rol administrador
  - "ADR-0015"  # Stack Django+React clínico — D5 derogado parcialmente
  - "ADR-0017"  # Login unificado backend-admin — resuelve D7
  - "ADR-0018"  # Permisos por rol backend-clinic — preservado sin cambios
  - "ADR-0019"  # RBAC jerárquico backend-clinic — preservado sin cambios
  - "ADR-0020"  # SSO (este DD)
release: "release/2.0.0"
status: proposed
fecha: "2026-07-20"
autores:
  - "Ing. Guillermo Mamani Chambi"
---

# Design Doc `DD-SSO-001` — SSO real entre `backend-admin` y `backend-clinic`

## 0. Relación con ADR-0020

Este DD implementa D1-D5 de `docs/adr/0020-sso-backend-admin-autoridad-jwt.md`.
No repite la justificación (ya está en el ADR) — se enfoca en el
**cómo**: archivos concretos, código, configuración de dev y prod, y
plan de pruebas.

**Regla de oro de esta migración:** ningún usuario que hoy puede
loguearse en `frontend-clinic` (vía su login propio) debe perder esa
capacidad — solo cambia *dónde* inicia sesión (ahora en
`frontend-admin`) y *cómo* llega el token a `backend-clinic` (ahora
validado, no emitido localmente).

## 1. Trazabilidad SDD

```
Pedido del arquitecto (2026-07-20): "un solo logueo, navegar todo el sistema"
  → ADR-0020 (accepted): backend-admin autoridad JWT, 2 SPAs sesión compartida
    → este DD: diseño de componentes, migración, plan de pruebas
      → código (backend-admin, backend-clinic, frontend-admin, frontend-clinic)
        → tests (ambos backends + ambos frontends)
          → verificación E2E real con Playwright (login único, navegar ambas SPAs sin re-login)
            → PROMPT_MAPPING (PM-SSO-001)
```

## 2. Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│  Usuario                                                            │
└─────────────────────────────────────────────────────────────────┘
              │ 1. login (única vez)
              ▼
┌─────────────────────────┐
│  frontend-admin            │  LoginPage.tsx (sin cambios de UI)
│  (:5173 en dev)             │
└─────────────────────────┘
              │ 2. POST /api/auth/login/
              ▼
┌─────────────────────────┐
│  backend-admin              │  AdminTokenObtainPairSerializer.get_token()
│  (:8001)                     │  ahora embebe {email, role} EN el JWT (D3)
│  AUTORIDAD ÚNICA             │  Firma con AUTH_ADMIN_JWT_SECRET
└─────────────────────────┘
              │ 3. {access, refresh, role, email, full_name}
              ▼
   localStorage['biomed.auth.access']  ← ÚNICO storage de sesión real
              │
              │ 4. usuario navega a frontend-clinic (mismo origen lógico, ver §4)
              ▼
┌─────────────────────────┐
│  frontend-clinic            │  Lee biomed.auth.access (ya existe, sin
│  (:5174 en dev)             │  pedir login — SessionProvider ajustado, §5)
└─────────────────────────┘
              │ 5. request con Authorization: Bearer <token de backend-admin>
              ▼
┌─────────────────────────┐
│  backend-clinic              │  SharedJWTAuthentication (nuevo, D2)
│  (:8002)                     │  - Valida firma con AUTH_ADMIN_JWT_SECRET (D1)
│  YA NO EMITE, SOLO VALIDA    │  - Lee claims {email, role} del token
└─────────────────────────┘  - get_or_create(User local) + sync is_staff/is_superuser
              │
              ▼
   role_for_user()/tiene_opcion() (ADR-0018/0019) — SIN CAMBIOS,
   siguen operando sobre el User local ya sincronizado
```

## 3. Componentes backend

### 3.1 `backend-admin/apps/users/auth_serializers.py` (modificado)

```python
class AdminTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['email'] = user.email
        token['role'] = user.role
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data['role'] = self.user.role
        data['email'] = self.user.email
        data['full_name'] = _full_name_for(self.user)
        return data
```

Único cambio: `get_token()` nuevo (antes no existía override; SimpleJWT
usaba el default que no incluye `email`/`role` en el payload firmado).
`validate()` no cambia — el body de la respuesta HTTP ya traía esos
campos para el frontend.

### 3.2 `backend-clinic/clinic_backend/settings.py` (modificado)

```python
SIMPLE_JWT = {
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': env('AUTH_ADMIN_JWT_SECRET', required=True),  # antes: AUTH_CLINIC_SECRET
    'AUTH_HEADER_TYPES': ('Bearer',),
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),  # debe coincidir con backend-admin
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),      # debe coincidir con backend-admin
}

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'apps.samples.auth_bridge.SharedJWTAuthentication',  # antes: JWTAuthentication directo
    ],
    # resto sin cambios
}
```

`AUTH_CLINIC_SECRET` deja de usarse para el login humano. **No se
borra la variable de entorno todavía** (puede quedar reservada por si
algún flujo interno la sigue referenciando — confirmar con
`grep -rn AUTH_CLINIC_SECRET` antes de eliminarla del `.env.example`).

### 3.3 `backend-clinic/apps/samples/auth_bridge.py` (nuevo)

```python
"""SSO (ADR-0020) — SharedJWTAuthentication valida el JWT firmado por
backend-admin (mismo secreto, AUTH_ADMIN_JWT_SECRET) y sincroniza el
User local de backend-clinic a partir de los claims {email, role}.

Mismo patrón que backend-admin/apps/users/auth_bridge.py (exchange F0),
en la dirección inversa: aquí no hay un endpoint de exchange explícito,
la sincronización ocurre transparentemente en cada request autenticado
vía get_user() (override de JWTAuthentication)."""
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken


class SharedJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        email = validated_token.get('email')
        role = validated_token.get('role')
        if not email:
            raise InvalidToken('Token sin claim email — no es un token válido de backend-admin')

        User = get_user_model()
        user, _created = User.objects.get_or_create(
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

**Nota de RN-06 (segregación):** la sincronización de `is_staff`/
`is_superuser` ocurre en *cada* request autenticado — si un admin
cambia el `role` de un usuario en `backend-admin`, el cambio se
refleja en `backend-clinic` en la siguiente request de ese usuario
(no requiere re-login). Esto es una mejora respecto al estado actual
(hoy, cambiar el rol en un backend no afecta al otro en absoluto).

### 3.4 `backend-clinic/clinic_backend/urls.py` (modificado)

```python
from django.contrib import admin
from django.urls import include, path
# TokenObtainPairView/TokenRefreshView eliminados del import y de urlpatterns

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/clinic/', include('apps.samples.urls')),
]
```

Las rutas `api/clinic/auth/login/` y `api/clinic/auth/refresh/` se
**eliminan**. Cualquier cliente que las llame recibe 404 — es
intencional, fuerza a que todo login pase por `backend-admin`.

## 4. Componentes frontend

### 4.1 Proxy dev unificado (resuelve el problema de origen cruzado del ADR-0020 D5)

**Problema:** `frontend-admin` (`:5173`) y `frontend-clinic` (`:5174`)
son dos orígenes distintos en dev — `localStorage` no se comparte
entre ellos de forma nativa.

**Solución elegida: un tercer proceso, Caddy en modo dev, como
reverse proxy sobre ambos Vite dev servers.** Esto además adelanta
trabajo del F8 pendiente de ADR-0013 (`docker-compose` con Caddy/nginx
como reverse proxy unificado, nunca implementado) — se construye la
versión mínima aquí y se reutiliza en F8 cuando se retome.

```caddyfile
# Caddyfile.dev (nuevo, raíz del repo)
:3000 {
	handle /clinic/* {
		reverse_proxy localhost:5174
	}
	handle /api/clinic/* {
		reverse_proxy localhost:8002
	}
	handle /api/admin/* {
		reverse_proxy localhost:8001
	}
	handle /api/auth/* {
		reverse_proxy localhost:8001
	}
	handle {
		reverse_proxy localhost:5173
	}
}
```

Con esto, `http://localhost:3000/` sirve `frontend-admin`,
`http://localhost:3000/clinic/` sirve `frontend-clinic`, y ambos
comparten `document.location.origin = http://localhost:3000` →
`localStorage` compartido nativamente. Los `vite.config.ts` de ambos
frontends **no necesitan cambiar sus proxies internos** (siguen
proxyando `/api/admin`→`:8001` y `/api/clinic`→`:8002` para cuando se
accede directo a `:5173`/`:5174` sin Caddy, útil para debug aislado).

`frontend-clinic` necesita `base: '/clinic/'` en su `vite.config.ts`
para que sus assets resuelvan correctamente detrás del path prefix
(cambio de 1 línea).

**Alternativa de prod:** en producción, ambos frontends ya se compilan
a estático (`vite build`) y se sirven detrás de un servidor único
(nginx/Caddy) — este mismo patrón de path-based routing aplica
directamente, sin el Caddyfile de dev (se reemplaza por la config de
prod que F8/ADR-0013 ya tenía planeada).

### 4.2 `frontend-clinic/src/clinic/auth/SessionProvider.tsx` (modificado)

Deja de llamar a `authClient.login()` (que pegaba a
`/api/clinic/auth/login/`, ahora inexistente). En su lugar, lee
`biomed.auth.access` directamente (mismo storage que `frontend-admin`
ya escribe tras el login único):

```tsx
// frontend-clinic/src/clinic/auth/SessionProvider.tsx (ajustado)
const SESSION_ACCESS_KEY = 'biomed.auth.access';  // antes: biomed.clinic.access

export function SessionProvider({ children, forceAnalystOnMount = false }: SessionProviderProps) {
  const [session, setSession] = useState<Session>(() => ({
    isAuthenticated: Boolean(localStorage.getItem(SESSION_ACCESS_KEY)),
    role: decodeRoleFromJwt(localStorage.getItem(SESSION_ACCESS_KEY)),  // nuevo: decodifica claim `role` del JWT
    username: decodeEmailFromJwt(localStorage.getItem(SESSION_ACCESS_KEY)),
  }));
  // login()/doLogin ya no llama a authClient.login() — si no hay sesión,
  // redirige a frontend-admin (o muestra "inicie sesión en el panel admin")
  // en vez de mostrar un form de login propio.
  // forceAnalystOnMount (modo MSW) se mantiene para tests, sin cambios.
  ...
}
```

`decodeRoleFromJwt`/`decodeEmailFromJwt`: mismo patrón que
`authClient.ts::decodeExp()` ya existente en `frontend-admin` (decodificar
el payload del JWT sin verificar firma — la firma ya la verificó el
backend, el frontend solo lee claims para UX).

### 4.3 `frontend-clinic/src/clinic/api/samplesClient.ts` (modificado)

```ts
// antes: getAccessToken() leía 'biomed.clinic.access'
// ahora: lee 'biomed.auth.access' (mismo storage que frontend-admin)
const ACCESS_KEY = 'biomed.auth.access';
```

### 4.4 Redirect cuando no hay sesión

Si `frontend-clinic` se accede sin sesión activa (`biomed.auth.access`
ausente), redirige a `frontend-admin`'s `/login` (vía el path
compartido del Caddy, ej. `window.location.href = '/'`) en vez de
mostrar un form de login propio — coherente con "un solo logueo".

## 5. Migración de datos (usuarios ya existentes en `backend-clinic`)

`backend-clinic` ya tiene usuarios locales creados por
`create_user()`/tests/demos previos (`demo_analista`, `e2e_admin`,
etc. — ver memoria de sesiones previas). Estos usuarios **no
desaparecen**, pero dejan de ser alcanzables por login directo (ya no
existe `/api/clinic/auth/login/`). Tras este cambio, el único modo de
"convertirse" en esos usuarios es que `backend-admin` tenga un
`CustomUser` con el mismo `email` — `SharedJWTAuthentication` hace
`get_or_create(username=email)`, así que:

- Si el email coincide exactamente con un `User` ya existente en
  `backend-clinic` → se reutiliza esa fila, se sincronizan
  `is_staff`/`is_superuser`.
- Si no existe → se crea uno nuevo automáticamente (idéntico al
  comportamiento de `auth_bridge.py` de `backend-admin`, que ya hace
  `get_or_create`).

**No requiere migración de datos explícita** — es autosanable en el
primer request de cada usuario. Documentar en el runbook de deploy
que los usuarios demo (`demo_analista@...`, etc.) deben existir
también como `CustomUser` en `backend-admin` con el `role` correcto
para que el mapeo tenga sentido end-to-end.

## 6. Plan de pruebas (RN-09 ≥90%)

### 6.1 Backend `backend-admin` (extender `test_auth_views.py` o similar)

| Test | Verifica |
|---|---|
| `test_login_incluye_email_role_en_jwt_payload` | Decodificar el `access` token (sin verificar firma, solo payload) y confirmar `email`/`role` presentes |
| `test_login_body_sigue_igual` | El body de la respuesta HTTP no cambia (regresión) |

### 6.2 Backend `backend-clinic` (`test_shared_jwt_auth.py`, nuevo)

| Test | Verifica |
|---|---|
| `test_token_sin_email_claim_rechazado` | Token válido en firma pero sin claim `email` → `InvalidToken` |
| `test_usuario_nuevo_se_crea_automaticamente` | Primer request con email nunca visto → `User.objects.get_or_create` crea la fila |
| `test_usuario_existente_se_reutiliza` | Email ya existente → misma fila, no duplica |
| `test_sincroniza_is_staff_admin` | claim `role=admin` → `is_staff=True, is_superuser=True` |
| `test_sincroniza_is_staff_supervisor` | claim `role=supervisor` → `is_staff=True, is_superuser=False` |
| `test_sincroniza_is_staff_analista` | claim `role=analista` → ambos `False` |
| `test_cambio_de_role_se_refleja_en_siguiente_request` | Usuario ya sincronizado como analista, token nuevo con `role=admin` → se actualiza sin recrear la fila |
| `test_endpoints_login_clinic_ya_no_existen` | `POST /api/clinic/auth/login/` → 404 |
| `test_tiene_opcion_sigue_funcionando_sobre_user_sincronizado` | Regresión: crear `UsuarioGrupo` para el `User` sincronizado, confirmar que `tiene_opcion()` (ADR-0019) sigue resolviendo igual que antes |

### 6.3 Frontend `frontend-clinic` (ajustar tests existentes de `SessionProvider`)

| Test | Verifica |
|---|---|
| `test_lee_sesion_de_biomed_auth_access` | Ajustar tests existentes que mockeaban `biomed.clinic.access` |
| `test_sin_sesion_redirige_a_admin` | Nuevo: sin token, redirige en vez de mostrar login propio |
| `test_decodifica_role_del_jwt` | Nuevo: `decodeRoleFromJwt` extrae correctamente el claim |

### 6.4 Verificación E2E real (Playwright, sin mocks)

1. Levantar Caddy dev + ambos backends + ambos frontends.
2. Login único en `http://localhost:3000/` (frontend-admin).
3. Navegar a `http://localhost:3000/clinic/` — confirmar que **no**
   pide login de nuevo y que la lista de muestras carga (llamada real
   a `backend-clinic` con el token de `backend-admin`).
4. Confirmar en Django Admin de `backend-clinic` (`/admin/`) que el
   `User` sincronizado tiene `is_staff`/`is_superuser` coherentes con
   el `role` del usuario logueado.
5. Cambiar el `role` del usuario en `backend-admin` (vía su Admin o
   API), sin re-login, y confirmar que el siguiente request desde
   `frontend-clinic` refleja el nuevo rol (ej. ve más/menos muestras
   según scoping).

## 7. Riesgos

| Riesgo | Mitigación |
|---|---|
| `ACCESS_TOKEN_LIFETIME` diverge entre backends con el tiempo | Comentario cruzado en ambos `settings.py` señalando que deben coincidir; considerar extraerlo a una env var compartida en el futuro |
| Caddy dev no instalado en la máquina del desarrollador | Documentar instalación en README; alternativa de fallback: seguir usando `:5173`/`:5174` directos para desarrollo aislado de un solo frontend (pierde el SSO real en ese modo, aceptable para iteración rápida de UI) |
| Usuario con mismo email pero rol distinto en cada backend antes de la migración | Documentado en §5 — el primer request post-deploy sincroniza, no requiere intervención manual salvo casos de datos inconsistentes preexistentes (raro, pero auditar antes de desplegar a producción) |
| `frontend-clinic` con tests que asumían `biomed.clinic.access` | Todos los tests de `SessionProvider`/`samplesClient` que referencian esa key deben actualizarse — barrido explícito con grep antes de dar por cerrada la tarea |

## 8. Plan de implementación

| # | Tarea | Estado |
|---|---|---|
| T1 | ADR-0020 | ✅ accepted |
| T2 | Este DD | ✅ |
| T3 | `backend-admin`: `get_token()` override en `AdminTokenObtainPairSerializer` | ⏸ |
| T4 | `backend-clinic`: `auth_bridge.py` nuevo (`SharedJWTAuthentication`) | ⏸ |
| T5 | `backend-clinic`: `settings.py` (SIGNING_KEY compartida, auth class) + `urls.py` (eliminar login/refresh propios) | ⏸ |
| T6 | Tests backend-admin (2) + backend-clinic (9) | ⏸ |
| T7 | `Caddyfile.dev` + ajuste `base: '/clinic/'` en `frontend-clinic/vite.config.ts` | ⏸ |
| T8 | `frontend-clinic`: `SessionProvider.tsx` + `samplesClient.ts` (leer `biomed.auth.access`) | ⏸ |
| T9 | Ajustar tests de frontend-clinic existentes que referencian `biomed.clinic.access` (grep + fix) | ⏸ |
| T10 | Tests frontend nuevos (redirect sin sesión, decode de JWT) | ⏸ |
| T11 | Suite completa ambos backends + ambos frontends, RN-09 ≥90%, cero regresión | ⏸ |
| T12 | Verificación E2E real con Playwright (§6.4, los 5 pasos) | ⏸ |
| T13 | `PROMPT_MAPPING.md` (`PM-SSO-001`), `DTI.md`, `AGENTS.md` §5, `docs/AUTH_BRIDGE.md` (nota cruzada) | ⏸ |
| T14 | Commit | ⏸ |

## 9. Trazabilidad

- **Sube a:** ADR-0020 → este DD.
- **Baja a:** archivos listados en §3/§4, tests §6.
- **Impacta:** `docs/PROMPT_MAPPING.md`, `docs/DTI.md`, `AGENTS.md` §5,
  `docs/AUTH_BRIDGE.md`, y **pausa** `docs/prompts/PROMPT-RBAC-ADMIN-UI.md`
  hasta que este SSO esté implementado (ver ADR-0020 §Notas).

## Notas

- No se toca `backend-clinic/apps/samples/models_rbac.py` ni
  `permissions.py` (ADR-0019) — el RBAC jerárquico sigue intacto.
- No se toca el exchange F0 (`backend-admin/apps/users/auth_bridge.py`,
  FastAPI→backend-admin) — es un mecanismo distinto, para un caso
  distinto (posible integración con el FastAPI clínico legacy, si
  aplica).
- Rama de trabajo: `feature/sso-backend-admin`.
- Este DD es `proposed` — implementar solo tras confirmar que el
  Caddyfile de dev (§4.1) es aceptable, o discutir alternativa si el
  arquitecto prefiere no depender de un proceso extra en desarrollo
  local.
