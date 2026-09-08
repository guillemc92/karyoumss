# Auth Bridge — FastAPI (clínico) ↔ Django (admin)

**Versión:** v0.1 | **Fecha:** 28/06/2026 | **Estado:** Aprobado para F0 del ADR-0013
**Autores:** Ing. Guillermo Mamani Chambi | **ADR origen:** [ADR-0013](adr/0013-stack-django-react-admin.md)

> ⚠️ **Nota de desactualización (2026-07-12, ADR-0017):** este documento asume un
> `backend-clinical` FastAPI que **no está commiteado en el repo** (confirmado también
> por ADR-0015 §Contexto punto 4). El flujo de login **primario** del sistema ya no es
> el exchange descrito aquí: [ADR-0017](adr/0017-sistema-autenticacion-login.md) agrega
> un login real por email/password directamente en `backend-admin` (`CustomUser` +
> SimpleJWT propio, namespace `AUTH_ADMIN_JWT_SECRET`), sin depender de un JWT externo.
> El endpoint `POST /api/admin/auth/exchange` descrito abajo **sigue existiendo en
> código** (`apps/users/views.py::auth_exchange_view`) y no se elimina, pero queda como
> mecanismo secundario sin uso activo. Ver ADR-0017 D1-D2 y DD-AUTH-001 §0.
>
> ⚠️ **Ver también (2026-07-20, ADR-0020):** el patrón de "shared JWT HS256 con clave
> simétrica compartida" descrito en este documento (§2) para FastAPI↔Django admin es
> **el mismo patrón** que [ADR-0020](adr/0020-sso-backend-admin-autoridad-jwt.md) aplica
> ahora entre `backend-admin`↔`backend-clinic` (Django↔Django) — `backend-admin` firma
> con `AUTH_ADMIN_JWT_SECRET`, `backend-clinic` valida con la misma clave vía
> `SharedJWTAuthentication` (`backend-clinic/apps/samples/auth_bridge.py`, nombre de
> archivo igual a este mecanismo por design, pero es código nuevo y distinto — no
> reemplaza ni se apoya en el exchange F0 descrito abajo). Ver DD-SSO-001 para el
> diseño completo de este SSO más reciente.

---

## 1. Contexto

El proyecto BIOMED UMSS tiene **dos backends** desde el ADR-0013:

- **backend-clinical** (FastAPI + Celery + Redis + TorchServe) — maneja login del usuario, JWT con claim `role`, todos los endpoints clínicos.
- **backend-admin** (Django 5 + DRF, este bootstrap) — maneja CRUD de cuentas institucionales vía `/api/admin/users/*`.

El usuario se loguea **una sola vez** en FastAPI. Los requests al bounded context admin deben reusar esa sesión sin pedir credenciales de nuevo.

## 2. Decisión

Implementar **shared JWT HS256** con clave simétrica compartida entre FastAPI y Django.

### Flujo

```
1. Usuario hace login en FastAPI:  POST /api/v1/auth/login  → JWT (HS256, claim role)
2. Frontend llama:  POST /api/admin/auth/exchange  con Authorization: Bearer <jwt_fastapi>
3. Django valida el JWT con la misma clave compartida (PyJWT).
4. Si válido: busca/crea User en Django, devuelve Django Token (DRF auth_token.Token).
5. Frontend guarda Django Token, lo usa para todos los requests /api/admin/users/*.
6. Django Token expira a las 24h; renewal vía re-exchange del JWT FastAPI.
```

### Claims del JWT FastAPI (lo que Django espera)

| Claim | Tipo | Ejemplo | Descripción |
|:---|:---|:---|:---|
| `sub` | string | `"uuid-1234"` | User ID en backend-clinical |
| `email` | string | `"admin@biomed.local"` | Para mapeo a Django User |
| `role` | string | `"admin"` / `"analista"` / `"supervisor"` | RBAC |
| `exp` | int (unix) | `1719500000` | Expiración |
| `iat` | int (unix) | `1719496400` | Issued at |

### Configuración

**Variable de entorno compartida** (en ambos backends):

```bash
# .env (backend-clinical Y backend-admin)
AUTH_BRIDGE_SECRET=<64+ chars random hex>
# Generar con: python -c "import secrets; print(secrets.token_hex(32))"
```

**NO** commitear `.env`. Solo `.env.example` con placeholder.

### Algoritmo

```python
# backend-admin/apps/users/auth.py (vista exchange)
import jwt
from django.conf import settings
from rest_framework.authtoken.models import Token

def exchange_fastapi_jwt(fastapi_jwt: str) -> Token:
    payload = jwt.decode(
        fastapi_jwt,
        settings.AUTH_BRIDGE_SECRET,
        algorithms=['HS256'],
        options={'require': ['sub', 'email', 'role', 'exp']}
    )
    user, _ = User.objects.get_or_create(
        username=payload['email'],
        defaults={
            'email': payload['email'],
            'role': payload['role'],
            'is_active': True,
        }
    )
    user.role = payload['role']  # sync role si cambió en FastAPI
    user.save()
    token, _ = Token.objects.get_or_create(user=user)
    return token
```

### Endpoints

```
POST /api/admin/auth/exchange
  Headers: Authorization: Bearer <jwt_fastapi>
  Body:    (vacío)
  Response 200: { "token": "<django_token_hex>", "role": "admin", "expires_at": "2026-06-29T..." }
  Response 401: { "error": "Invalid FastAPI JWT" }
```

## 3. Por qué HS256 (no RS256)

- **HS256**: clave simétrica. Ambos backends conocen el secret. Simple, 1 variable de entorno.
- **RS256**: clave pública/privada. FastAPI firmaría con privada, Django validaría con pública. Más seguro pero requiere distribuir clave pública sin exponer la privada.

Para MVP admin, HS256 es suficiente. La rotación de secret se hace invalidando todos los Django Tokens existentes (operación una vez al año o bajo incidente).

## 4. Seguridad

| Riesgo | Mitigación |
|:---|:---|
| Secret leak | `AUTH_BRIDGE_SECRET` solo en env vars, nunca en código. `.env` en `.gitignore`. |
| JWT replay | `exp` corto (24h en FastAPI). Django Token expira a las 24h también. |
| Token theft (HTTPS) | Asumir HTTPS en producción. En dev, CORS permite solo `localhost:*`. |
| Privilege escalation | Django re-valida `role` en cada request vía middleware DRF. Si FastAPI dice `role=admin`, Django confía pero RBAC middleware verifica en cada endpoint. |
| Token storage en cliente | Django Token en `sessionStorage` (no `localStorage`) para reducir ventana de exposición. |

## 5. Rotación de secret

Cuando se rota `AUTH_BRIDGE_SECRET`:

1. Generar nuevo secret: `python -c "import secrets; print(secrets.token_hex(32))"`.
2. Actualizar env var en backend-clinical y backend-admin.
3. Backend-clinical: el siguiente login emite JWT con nuevo secret.
4. Backend-admin: el siguiente exchange valida con nuevo secret.
5. **Invalidar todos los Django Tokens existentes** (para forzar re-exchange):
   ```python
   from rest_framework.authtoken.models import Token
   Token.objects.all().delete()
   ```
6. Frontend: detectar 401 en `/api/admin/users/*` → re-exchange automático.

Downtime esperado: 0 (rolling rotation, ambos backends pueden correr simultáneamente con secret viejo y nuevo durante la ventana de deploy).

## 6. Tests

- Unit: `exchange_fastapi_jwt()` con JWT firmado con secret válido → devuelve Token.
- Unit: JWT con firma inválida → raise `InvalidTokenError` → endpoint devuelve 401.
- Unit: JWT sin claim `role` → endpoint devuelve 401.
- Integration: flujo completo login FastAPI (mock) → exchange → request admin con Django Token → 200.

## 7. Limitaciones conocidas

- **No hay refresh token cross-backend.** Si Django Token expira, usuario hace re-exchange con FastAPI JWT (que también puede haber expirado → re-login en FastAPI).
- **No hay lista de revocación.** Un JWT FastAPI robado es válido hasta su `exp`. Aceptable para MVP admin (volumen bajo).
- **Single secret.** Si se quiere rotación sin downtime, se necesita JWKS con múltiples secrets activos (futuro).

## 8. Trazabilidad

- **Sube a:** ADR-0013 §Plan F0 + F7 → DD-ADMIN-001 §2.
- **Implementa:** vista `AuthExchangeView` en `backend-admin/apps/users/views.py`.
- **Test:** `backend-admin/tests/test_auth_bridge.py`.

---

*v0.1 — 28/06/2026 — Guillermo Mamani Chambi*