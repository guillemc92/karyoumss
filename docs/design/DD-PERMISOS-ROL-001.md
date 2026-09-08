---
id: DD-PERMISOS-ROL-001
titulo: "Permisos por rol en backend-clinic — is_staff/is_superuser (ADR-0018)"
producto: "BIOMED UMSS — Intelligent Karyotyping Platform"
grupo: "G04"
fsd_uc:
  - "FSD-UC-001"
  - "FSD-UC-CRUD-MUESTRA-001"
prd_refs:
  - "PRD-US-001"
adrs:
  - "ADR-0015"  # Stack Django+React para Muestras (contexto donde vive el gap)
  - "ADR-0017"  # Login unificado (precedente: backend-admin sí tiene CustomUser.role)
  - "ADR-0018"  # Permisos por rol en backend-clinic (este DD)
prompts:
  - "PM-CRUD-MUESTRA-002"
specs:
  - "SPEC-008-crud-muestra-react.md"  # §6 tabla de roles, §6.1 addendum de este feature
release: "release/2.0.0"
status: accepted
fecha: "2026-07-13"
autores:
  - "Ing. Guillermo Mamani Chambi"
---

# Design Doc `DD-PERMISOS-ROL-001` — Permisos por rol en backend-clinic

## 0. Relación con `DD-CRUD-MUESTRA-001`

Este DD es **complementario**, no reemplaza a `DD-CRUD-MUESTRA-001.md`. Aquel documento cubre el modelo de datos y el diseño original (hoy superseded) del CRUD de Muestras; este documento cubre específicamente el cierre del gap de permisos que `SPEC-008 §6` ya especificaba pero que el código nunca implementó — detectado en la auditoría de trazabilidad del PR #1 (2026-07-13), no en el diseño original.

No introduce modelos nuevos ni migraciones — extiende `apps/samples/permissions.py` y `apps/samples/views.py`, ambos ya existentes.

## 1. Trazabilidad SDD

```
SPEC-008 §6 (tabla de 3 roles × 6 endpoints, redactada en 1256576, nunca cerrada en código)
  → Auditoría de trazabilidad del PR #1 (2026-07-13)
    → ADR-0018 (accepted)
      → este DD (arquitectura de componentes)
        → SPEC-008 §6.1 (addendum: mapeo rol → campos Django)
          → código (permissions.py, views.py, urls.py)
            → tests (24 nuevos, 59/59 total en backend-clinic)
```

## 2. Arquitectura de permisos

```
┌─────────────────────────┐        ┌──────────────────────────────┐
│  User (Django, sin       │        │  role_for_user(user)          │
│  campo role propio)      │───────►│  is_superuser → "admin"       │
│  - is_staff               │        │  is_staff     → "supervisor"  │
│  - is_superuser            │        │  ninguno      → "analista"    │
└─────────────────────────┘        └──────────────────────────────┘
                                                  │
                    ┌─────────────────────────────┼─────────────────────────────┐
                    ▼                             ▼                             ▼
          ┌──────────────────┐         ┌──────────────────┐         ┌──────────────────┐
          │  IsClinicRole      │         │  IsOwnerOrStaff    │         │  IsAdminRole       │
          │  (has_permission)  │         │  (has_object_perm) │         │  (has_permission)  │
          │  los 3 roles       │         │  analista: solo    │         │  solo admin        │
          │  autenticados      │         │  propias (403)     │         │  (DELETE)          │
          └──────────────────┘         └──────────────────┘         └──────────────────┘
                    │                             │                             │
                    ▼                             ▼                             ▼
          SampleListCreateView          SampleDetailView              SampleDetailView
          GET (list) / POST             GET / PATCH (scoped)          DELETE (soft-delete,
                                                                        rechaza VALIDATED)
```

**Por qué `has_object_permission` y no `get_queryset()` filtrado, para GET/PATCH de un id específico:** filtrar por queryset (como ya hace `SampleListCreateView` para el listado) convierte "existe pero no es tuya" en un `404` — correcto para un listado, pero `SPEC-008 CA-5` exige `403` explícito con semántica de "no autorizado", distinto de "no existe". Por eso `SampleDetailView` usa `queryset` sin filtrar + `IsOwnerOrStaff.has_object_permission()`, mientras que `SampleListCreateView` sigue filtrando en `get_queryset()` — son dos mecanismos DRF distintos, elegidos a propósito según el verbo.

## 3. Componentes backend (`backend-clinic/apps/samples/`)

| Componente | Responsabilidad |
|---|---|
| `permissions.py::role_for_user()` | Función pura: deriva `analista`/`supervisor`/`admin` de `is_staff`/`is_superuser` |
| `permissions.py::IsClinicRole` | `has_permission`: cualquier usuario autenticado (los 3 roles) |
| `permissions.py::IsAdminRole` | `has_permission`: solo `is_superuser` — usado en `DELETE` |
| `permissions.py::IsOwnerOrStaff` | `has_object_permission`: analista solo su propia muestra (403 si no), staff cualquiera |
| `permissions.py::CanRegisterSample` | Alias de `IsClinicRole` (ya usado por `SampleRegisterView`, ADR-0016 — sin cambio de comportamiento) |
| `views.py::SampleListCreateView` (modificada) | `permission_classes` pasa de `IsAuthenticated` genérico a `IsClinicRole` (mismo comportamiento, nombre explícito) |
| `views.py::SampleDetailView` (nueva) | `GET`/`PATCH`/`DELETE /samples/{id}/` — antes inexistente. Reutiliza `SampleReadSerializer`/`SampleUpdateSerializer`, ya existentes sin usar desde el vertical slice original |
| `urls.py` (modificada) | Ruta `samples/<uuid:pk>/` |

## 4. Riesgos (ver también ADR-0018 §Consecuencias)

| Riesgo | Mitigación |
|---|---|
| El rol de `backend-clinic` queda desincronizado del `CustomUser.role` de `backend-admin` (dos administradores distintos posibles) | Documentado como limitación conocida en ADR-0018 §Negativas — mismo criterio YAGNI que el gap de SSO cross-backend de ADR-0017 D7. No se resuelve en este DD. |
| `is_staff`/`is_superuser` no comunican "supervisor"/"admin" a simple vista en el admin site de Django | Mitigado con el docstring de `role_for_user()` y esta tabla de mapeo, referenciada también en `SPEC-008 §6.1`. |
| Confundir el scoping de `SampleListCreateView` (queryset filtrado, 404) con el de `SampleDetailView` (permiso de objeto, 403) | Documentado explícitamente en §2 de este DD — son dos mecanismos DRF distintos a propósito, no una inconsistencia. |

## 5. Plan de implementación (ya ejecutado)

| # | Tarea | Estado |
|---|---|---|
| T1 | ADR-0018 (decisión: `is_staff`/`is_superuser`, sin campo nuevo) | ✅ |
| T2 | `SPEC-008 §6.1` (addendum, mapeo rol → campos Django) | ✅ |
| T3 | `permissions.py`: `role_for_user`, `IsClinicRole`, `IsAdminRole`, `IsOwnerOrStaff` | ✅ |
| T4 | `views.py`: `SampleDetailView` (GET/PATCH/DELETE) + fix de nombre en `SampleListCreateView` | ✅ |
| T5 | `urls.py`: ruta `samples/<uuid:pk>/` | ✅ |
| T6 | Tests: `test_permissions.py` + `test_detail_view.py` (24 nuevos, 59/59 total) | ✅ |
| T7 | Verificación E2E con 3 usuarios reales (`e2e_analista`/`e2e_supervisor`/`e2e_admin`) contra servidor Django real | ✅ |
| T8 | Este DD + `PROMPT_MAPPING.md` (`PM-CRUD-MUESTRA-002`) + `DTI.md` §21 + `AGENTS.md` §5 | ✅ |

## 6. Trazabilidad

- **Sube a:** `SPEC-008 §6` (tabla de roles, redactada 2026-07-12, cerrada en código recién el 2026-07-13) → **ADR-0018** → este DD.
- **Baja a:** `backend-clinic/apps/samples/{permissions,views,urls}.py`, `backend-clinic/apps/samples/tests/{test_permissions,test_detail_view}.py`.
- **Impacta:** `docs/PROMPT_MAPPING.md` (`PM-CRUD-MUESTRA-002`), `docs/DTI.md` §21, `AGENTS.md` §5, `docs/specs/SPEC-008-crud-muestra-react.md` §6.1.

## Notas

- Este DD **no crea** un modelo de rol nuevo — documenta la decisión de reutilizar campos ya existentes de Django, tomada explícitamente para minimizar la superficie de cambio (ver ADR-0018 §Alternativas evaluadas y rechazadas, A1).
- Si en el futuro se decide unificar el rol entre `backend-admin` y `backend-clinic` (SSO cross-backend), ese es un ADR nuevo — no se decide ni se prepara aquí.
- Rama de trabajo: `feature/clinic-django-stack`. PR #1 → `release/2.0.0`.
