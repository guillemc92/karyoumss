---
id: ADR-0018
title: Permisos por rol en backend-clinic — mapeo analista/supervisor/admin a is_staff/is_superuser
date: 2026-07-13
status: accepted
supersedes: ninguno (implementa lo ya especificado en SPEC-008 §6, nunca cerrado en código)
related: [ADR-0015, ADR-0017, SPEC-008, AGENTS.md §3 RN-06]
fase: desarrollo
autor: Ing. Guillermo Mamani Chambi
---

# ADR 0018: Permisos por rol en backend-clinic — mapeo analista/supervisor/admin a is_staff/is_superuser

## Contexto

Al auditar la trazabilidad del PR #1 (CRUD Muestras + Registro + Login) se encontró un gap real entre lo especificado y lo implementado: `SPEC-008-crud-muestra-react.md` §6 define una tabla de permisos de 3 roles × 6 endpoints (`analista`/`supervisor`/`admin`, con `DELETE` restringido a `admin` y `GET`/`PATCH` scoped a "solo propias" para el analista) — pero el código real de `backend-clinic/apps/samples/` nunca implementó ese modelo de rol:

1. `clinic_backend/settings.py` **no define `AUTH_USER_MODEL`** — usa el `User` por defecto de Django, que no tiene campo `role`.
2. `SampleListCreateView.get_queryset()` (`views.py:20-24`) usa `user.is_staff` como proxy: si es staff ve todas las muestras, si no, solo las propias. Esto colapsa `supervisor` y `admin` en una sola categoría indistinguible — no hay forma de que un endpoint futuro (ej. `DELETE`, admin-only per SPEC-008) diferencie entre ambos.
3. `CanRegisterSample` (`permissions.py`) solo verifica `is_authenticated`, sin relación con el modelo de rol de SPEC-008.
4. No existen los endpoints `GET /samples/{id}/`, `PATCH /samples/{id}/`, `DELETE /samples/{id}/` — quedaron documentados como pendientes en el propio commit `d2eba8f` ("T9-T25 restante de backend-clinic") y nunca se cerraron.

Este ADR resuelve cómo se deriva el rol de un usuario dentro de `backend-clinic` — un bounded context que, a diferencia de `backend-admin` (ADR-0017, `CustomUser.role`), nunca tuvo un concepto de rol explícito en su modelo de datos ni en el JWT que emite.

## Decisión

### D1 — Rol derivado de `is_staff`/`is_superuser`, sin campo nuevo ni migración

Se define una función pura `role_for_user(user) -> Literal['analista', 'supervisor', 'admin']` en `apps/samples/permissions.py`:

```python
def role_for_user(user) -> str:
    if user.is_superuser:
        return 'admin'
    if user.is_staff:
        return 'supervisor'
    return 'analista'
```

Mapeo:

| Django field | Rol clínico |
|---|---|
| `is_superuser=True` | `admin` |
| `is_staff=True, is_superuser=False` | `supervisor` |
| `is_staff=False, is_superuser=False` | `analista` |

**Por qué no un campo `role` explícito (alternativa rechazada, ver §Alternativas):** `is_staff`/`is_superuser` son campos que **ya existen** en el `User` por defecto de Django (heredados de `AbstractUser`), usados desde el primer commit de `backend-clinic` (`01f968b`) para la distinción binaria analista/staff. Extenderlos a una jerarquía de 3 niveles no requiere migración, no introduce un segundo lugar donde el rol pueda quedar desincronizado, y es exactamente el patrón que Django recomienda para jerarquías simples de permisos (`is_staff` = acceso ampliado, `is_superuser` = acceso total).

### D2 — Permission classes explícitas, reemplazan el `IsAuthenticated` genérico

```python
class IsClinicRole(BasePermission):
    """Cualquier usuario autenticado del contexto clínico (los 3 roles)."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

class IsAdminRole(BasePermission):
    """Solo admin (is_superuser) — usado en DELETE."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)
```

`CanRegisterSample` se mantiene sin cambios de comportamiento (los 3 roles pueden registrar, per `registrarmuestrafinal.html`) pero se documenta explícitamente como alias semántico de `IsClinicRole`.

### D3 — Nuevo endpoint `SampleDetailView` (`GET`/`PATCH`/`DELETE /api/clinic/samples/{id}/`)

Cierra la brecha entre SPEC-008 §6 y el código: hasta este ADR, `GET`/`PATCH`/`DELETE` por id no existían.

| Verbo | Permiso | Scoping |
|---|---|---|
| `GET` | `IsClinicRole` | `analista`: solo propias (403 si no es dueño); `supervisor`/`admin`: todas |
| `PATCH` | `IsClinicRole` | Igual scoping que GET. Campos editables: solo `patient_ref`/`metadata_json` no-críticos — `status`/`chn_code`/`iscn_nomenclature` permanecen read-only (RN-04, ya enforced por `SampleUpdateSerializer` si existe, o se agrega validación explícita) |
| `DELETE` | `IsAdminRole` | Soft-delete (`is_active=False`). Rechaza con `409` si `status == 'VALIDATED'` (mismo criterio de riesgo que documentaba el DD-CRUD-MUESTRA-001 histórico) |

No se implementan en este ADR `POST /process/` ni `GET /status/` (SPEC-008 §6, columnas 6-7) — esos ya existen de facto a través de `SampleRegisterView`/`pipeline_client.py` (ADR-0016) para el flujo de registro; exponerlos como endpoints de re-proceso sobre una muestra ya existente queda fuera de alcance de este ADR (no fue solicitado, evita expandir scope sin pedido explícito).

## Justificación

- **RN-06 (segregación de funciones)** exige que un analista no pueda operar fuera de sus propias muestras y que ciertas acciones (eliminar) queden reservadas a un rol de mayor privilegio — sin un mapeo de rol explícito esto era estructuralmente imposible de aplicar más allá del list ya existente.
- **Menor invención posible**: reutilizar `is_staff`/`is_superuser` (ya presentes, ya usados parcialmente) es la opción de menor blast radius. Un campo `role` nuevo reabriría la pregunta — no resuelta y fuera de alcance de este PR — de cómo sincronizar ese rol con `backend-admin` (que sí tiene `CustomUser.role`, ADR-0017), dado que hoy son dos sistemas de autenticación independientes por diseño (ADR-0015 D5, ADR-0017 D1).
- **SPEC-008 §6 ya era la fuente de verdad** para este modelo de permisos; este ADR no inventa una tabla nueva, cierra la implementación de una que ya estaba aprobada y documentada, solo nunca comiteada como código.

## Consecuencias

### Positivas
- Cierra un gap de trazabilidad real (spec sin código) detectado en auditoría del PR #1.
- `DELETE` deja de ser una operación sin protección de rol — hoy no existe el endpoint en absoluto, por lo que este ADR **agrega** la restricción junto con el endpoint mismo, no la retrofittea sobre algo ya expuesto sin protección.
- Ningún cambio de esquema (no hay migración) — el riesgo de desplegar este cambio es bajo.

### Negativas
- El rol de un usuario en `backend-clinic` sigue siendo **independiente** del rol que el mismo usuario tenga en `backend-admin` — dos administradores del sistema (Django `is_superuser` en clinic vs. `CustomUser.role='admin'` en admin) deben provisionarse por separado, sin sincronización automática. Documentado como limitación conocida, no resuelto aquí (mismo criterio YAGNI que ADR-0015/ADR-0017 D7 sobre SSO cross-backend).
- `is_staff`/`is_superuser` son nombres de campo genéricos de Django que no comunican "supervisor"/"admin" a simple vista en el admin site de Django — mitigado documentando el mapeo en este ADR y en el docstring de `role_for_user()`.

### Neutras
- `POST /process/` y `GET /status/` de SPEC-008 §6 siguen sin exponerse como endpoints de re-proceso — permanecen fuera de alcance, explícitamente diferido.

## Tensión con reglas del proyecto y cómo se resuelve

| Regla | Tensión | Resolución |
|---|---|---|
| **RN-06** (segregación analista/supervisor) | Sin rol explícito, no había forma de aplicar la regla más allá del list | `role_for_user()` + `IsAdminRole`/`IsClinicRole` aplicados a los 3 verbos nuevos |
| **No inventar arquitectura sin ADR** | Agregar un modelo de rol es una decisión arquitectónica | Este ADR la documenta explícitamente antes de tocar código, con alternativa de campo `role` evaluada y rechazada por ahora |
| **No modificar ADRs existentes sin uno nuevo** | ADR-0015 no especificó el modelo de rol de Django para Muestras | Este ADR no modifica ADR-0015, lo complementa — ADR-0015 sigue vigente sin cambios |

## Alternativas evaluadas y rechazadas

**A1. Campo `role` explícito en el `User` de backend-clinic (mismo patrón que backend-admin).** Rechazada por el arquitecto: reabre la pregunta de sincronización cross-backend sin necesidad inmediata — mayor alcance del estrictamente necesario para cerrar el gap de SPEC-008 §6.

**A2. Grupos de Django (`django.contrib.auth.models.Group`) en vez de `is_staff`/`is_superuser`.** Rechazada: agrega una tabla más (`auth_group`, `auth_user_groups`) para resolver una jerarquía de solo 3 niveles totalmente ordenada (`analista < supervisor < admin`) — sobre-ingeniería para el caso de uso; `is_staff`/`is_superuser` ya expresan exactamente esa jerarquía.

**A3. No implementar `DELETE`/`PATCH`/`GET` por id todavía, solo "agregar permisos" a lo que ya existe (list/create/register).** Rechazada: `list`/`create`/`register` ya son accesibles a los 3 roles por diseño (no hay nada que restringir ahí más allá del scoping por `is_staff` que ya existe); la única restricción de rol pendiente en SPEC-008 §6 (`DELETE` admin-only) requiere necesariamente el endpoint que hoy no existe.

## Trazabilidad

- **Sube a:** SPEC-008 §6 (tabla de roles/permisos, nunca cerrada en código) → **este ADR-0018**.
- **Genera:** `docs/design/DD-PERMISOS-ROL-001.md` (arquitectura de componentes), `apps/samples/permissions.py` (`role_for_user`, `IsClinicRole`, `IsAdminRole`, `IsOwnerOrStaff`), `apps/samples/views.py` (`SampleDetailView`), `apps/samples/urls.py` (ruta `samples/<uuid:pk>/`), tests.
- **Impacta:**
  - `docs/design/DD-PERMISOS-ROL-001.md` (nuevo, complementario a `DD-CRUD-MUESTRA-001.md`)
  - `docs/specs/SPEC-008-crud-muestra-react.md` (§6.1 nuevo, mapeo rol→campos Django)
  - `docs/PROMPT_MAPPING.md` (`PM-CRUD-MUESTRA-002`)
  - `docs/DTI.md` §21, `AGENTS.md` §5

## Notas

- Este ADR **no toca** `backend-admin` ni el login unificado (ADR-0017) — el rol de `backend-clinic` sigue siendo interno a ese bounded context, derivado de sus propios campos `is_staff`/`is_superuser`, sin relación con `CustomUser.role` de `backend-admin`.
- Si en el futuro se decide unificar el modelo de rol entre ambos backends (ej. propagar el `role` del JWT de `backend-admin` hacia `backend-clinic`), eso requiere un ADR de SSO cross-backend — ya señalado como gap conocido en ADR-0017 D7, no se resuelve aquí.
- Rama de trabajo: `feature/clinic-django-stack`. NO pushear a `main`. PR #1 ya abierto a `release/2.0.0`.
