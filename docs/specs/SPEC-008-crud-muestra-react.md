---
id: SPEC-008
titulo: "CRUD de Muestras — Django 5 + React 18 (derogación parcial ADR-0013)"
bounded_context: muestras-clinico
documento_driving: ADR-0015
stack:
  backend: "Django 5 + DRF 3.15 + SimpleJWT 5 + SQLite (dev)"
  frontend: "React 18 + Vite 5 + TypeScript 5 + TanStack Query 5 + React Router 6"
  pipeline: "FastAPI (intacto, consumido vía httpx)"
version: 0.1
fecha: "2026-07-12"
autor: "Ing. Guillermo Mamani Chambi"
estado: proposed
agents_conformance: "§11 (PR a release/2.0.0)"
supersedes_dd: "DD-CRUD-MUESTRA-001 §2.2/§2.3/§2.4/§2.5/§3/§6/§7 (conservando §1, §2.1, §4, §5, §8)"
refs:
  - "ADR-0015 (derogación parcial ADR-0013)"
  - "ADR-0013 (derogado parcialmente, solo para Muestras)"
  - "ADR-0004 (hexagonal + Strangler)"
  - "DD-CRUD-MUESTRA-001 (superseded)"
  - "FSD-UC-001 (Ingesta + CHN)"
  - "FSD-UC-CRUD-MUESTRA-001 (a crear)"
  - "RN-04 (iscn_nomenclature read-only)"
  - "RN-05 (edits append-only)"
  - "RN-06 (segregación analista/supervisor)"
  - "RN-07 (modo degradado)"
  - "RN-09 (cobertura ≥90%)"
---

# SPEC-008 — CRUD de Muestras (Django 5 + React 18)

> **Spec técnica del stack moderno para Muestras.** Sustituye las
> secciones de implementación de `DD-CRUD-MUESTRA-001` (FastAPI +
> vanilla HTML) derogadas por `ADR-0015`.

## §0. Contexto y motivación

El `DD-CRUD-MUESTRA-001` (2026-07-11) proponía FastAPI + vanilla HTML
para el CRUD de Muestras. El arquitecto reconsideró y firmó
`ADR-0015` (2026-07-12) derogando parcialmente `ADR-0013` para mover
Muestras a Django + React, por 5 razones resumidas en el ADR
(consistencia con admin, DX, reuso de patrón, FastAPI intacto,
hallazgo de que el código FastAPI de Muestras no existe en el repo).

Esta spec define los **contratos técnicos** de la implementación:
6 endpoints REST en Django, 4 páginas React, 9 campos del modelo
`Sample`, y la integración con el pipeline FastAPI vía cliente HTTP
con circuit breaker (R6 del plan).

## §1. Alcance y no-alcance

### Incluye (este release 2.0.0)

- 6 endpoints REST en `backend-clinic/` (puerto `:8002`, namespace
  `/api/clinic/`):
  1. `POST /api/clinic/samples/` — crear muestra
  2. `GET /api/clinic/samples/` — listar con filtros + paginación
  3. `GET /api/clinic/samples/{id}/` — detalle
  4. `PATCH /api/clinic/samples/{id}/` — editar `patient_ref` (RN-04)
  5. `DELETE /api/clinic/samples/{id}/` — soft-delete (admin only)
  6. `POST /api/clinic/samples/{id}/process/` — encolar pipeline
- Auth: `POST /api/clinic/auth/login/`, `POST /api/clinic/auth/refresh/`,
  `POST /api/clinic/auth/logout/` (SimpleJWT)
- 4 páginas React en `frontend-clinic/` (puerto `:5174`):
  1. `SampleListPage` — tabla con filtros + paginación
  2. `SampleFormPage` — crear/editar con validación Zod
  3. `SampleDetailPage` — detalle + botón Procesar + polling
  4. `DegradedModePage` — RN-07 cuando FastAPI está caído
- Modelo `Sample` con 9 campos canónicos (id UUID, chn_code unique,
  patient_ref, image_path, status, analyst_id FK, supervisor_id FK,
  created_at, updated_at) + `metadata_json` (JSONField) + `is_active`
  (soft-delete) + `deleted_at`.

### NO incluye (queda para futuros releases)

- Reescritura del pipeline FastAPI (U-Net + EfficientNet) — intacto.
- Reescritura de `correccion de cariotipo.html`, `supervisor.html`,
  `informe.html` a React — siguen vanilla.
- Audit Merkle del clínico — sigue FastAPI per ADR-0008.
- ISCN auto-generation — sigue FastAPI per FSD-UC-006.
- WebSocket del clínico (ADR-0009) — el clínico usa polling cada 2s
  en `StatusPoller` por simplicidad; WS queda para release 2.1.
- Hard-delete (cascada) — solo soft-delete en este release.
- Multi-tenancy por institución (MRD-13) — release 2.1.

## §2. Gherkin por endpoint (6 endpoints)

### UC-S-001: Crear muestra

```gherkin
Feature: Crear muestra (POST /api/clinic/samples/)
  Como Analista Citogenetista
  Quiero registrar una nueva muestra
  Para iniciar el flujo de cariotipado

  Background:
    Given existe un usuario analista con JWT válido
    And el campo CHN no existe previamente

  Scenario: Creación exitosa
    When POST /api/clinic/samples/ con {patient_ref: "ANON-001", chn_code: "CHN-2026-07-12-0001", image_path: "s3://biomed/CHN-2026-07-12-0001.tiff"}
    Then retorna 201 con {id, chn_code, status: "PENDING_AI", patient_ref, analyst_id, created_at}
    And el evento "sample.created" se registra en audit log del clínico

  Scenario: CHN duplicado
    Given ya existe una muestra con chn_code "CHN-2026-07-12-0001"
    When POST con el mismo chn_code
    Then retorna 409 con {code: "CHN_DUPLICATE", detail: "CHN ya existe"}

  Scenario: Sin token JWT
    When POST sin Authorization header
    Then retorna 401 con {code: "UNAUTHENTICATED"}

  Scenario: Token expirado
    Given JWT access expirado hace 5 minutos
    When POST con Authorization: Bearer <expired>
    Then retorna 401 con {code: "TOKEN_EXPIRED"}

  Scenario: Rol sin permiso (no analista/supervisor/admin)
    Given un usuario externo (rol "externo") intenta crear
    When POST con su JWT
    Then retorna 403 con {code: "PERMISSION_DENIED"}
```

### UC-S-002: Listar muestras con filtros

```gherkin
Feature: Listar muestras (GET /api/clinic/samples/)
  Como Analista/Supervisor
  Quiero listar muestras con filtros
  Para encontrar el caso que necesito

  Background:
    Given existen 8 muestras en seed (3 PENDING_AI, 2 PROCESSING, 2 READY, 1 VALIDATED)

  Scenario: Listar sin filtros (analista)
    Given soy analista user_id=42
    And tengo 5 muestras asignadas y 3 de otro analista
    When GET /api/clinic/samples/ sin query params
    Then retorna 200 con {items: [5 muestras mías], total: 5, page: 1, page_size: 25}

  Scenario: Listar sin filtros (supervisor)
    Given soy supervisor
    When GET /api/clinic/samples/
    Then retorna 200 con {items: [8 muestras], total: 8, page: 1, page_size: 25}

  Scenario: Filtrar por status
    When GET /api/clinic/samples/?status=READY
    Then retorna solo las 2 muestras con status READY

  Scenario: Filtrar por CHN
    When GET /api/clinic/samples/?chn_query=CHN-2026-07
    Then retorna solo las muestras cuyo chn_code contiene "CHN-2026-07"

  Scenario: Filtrar por rango de fechas
    When GET /api/clinic/samples/?date_from=2026-07-01&date_to=2026-07-12
    Then retorna solo las muestras en ese rango

  Scenario: Paginación
    Given existen 30 muestras
    When GET /api/clinic/samples/?page=2&page_size=10
    Then retorna items 11-20, total: 30, page: 2, page_size: 10

  Scenario: Page size fuera de rango
    When GET /api/clinic/samples/?page_size=500
    Then retorna 400 con {code: "INVALID_PAGE_SIZE", detail: "max 100"}
```

### UC-S-003: Detalle de muestra

```gherkin
Feature: Detalle de muestra (GET /api/clinic/samples/{id}/)
  Scenario: Obtener muestra propia (analista)
    Given soy analista dueño de la muestra id=X
    When GET /api/clinic/samples/X/
    Then retorna 200 con SampleRead completo (incluye image_path, audit_log, chromosome_count)

  Scenario: Obtener muestra ajena (analista)
    Given soy analista user_id=42 y la muestra pertenece a user_id=99
    When GET /api/clinic/samples/X/
    Then retorna 403 con {code: "NOT_OWNER"}

  Scenario: Muestra inexistente
    When GET /api/clinic/samples/00000000-0000-0000-0000-000000000000/
    Then retorna 404 con {code: "NOT_FOUND"}

  Scenario: Muestra soft-deleted
    Given la muestra X tiene deleted_at no nulo
    When GET /api/clinic/samples/X/
    Then retorna 404 (soft-deleted se comporta como inexistente para GET)
```

### UC-S-004: Editar muestra (PATCH)

```gherkin
Feature: Editar muestra (PATCH /api/clinic/samples/{id}/)
  Scenario: Analista edita su propia muestra PENDING_AI
    Given soy analista dueño de muestra X en status PENDING_AI
    When PATCH /api/clinic/samples/X/ con {patient_ref: "ANON-002-actualizado"}
    Then retorna 200 con SampleRead actualizado

  Scenario: Analista intenta editar muestra ajena
    Given soy analista user_id=42 y la muestra es de user_id=99
    When PATCH con {patient_ref: "x"}
    Then retorna 403 con {code: "NOT_OWNER"}

  Scenario: Intentar cambiar status (RN-04: el analista NO puede)
    When PATCH con {status: "VALIDATED", patient_ref: "x"}
    Then retorna 400 con {code: "FIELD_READ_ONLY", field: "status"}
    And status no se modifica

  Scenario: Intentar cambiar chn_code (RN-04: chn_code inmutable)
    When PATCH con {chn_code: "CHN-FAKE"}
    Then retorna 400 con {code: "FIELD_READ_ONLY", field: "chn_code"}

  Scenario: Intentar cambiar iscn_nomenclature (RN-04: campo no expuesto)
    When PATCH con {iscn_nomenclature: "47,XY,+21"}
    Then retorna 400 con {code: "FIELD_NOT_ALLOWED", field: "iscn_nomenclature"}
    And audit log registra intento de violación RN-04

  Scenario: Muestra VALIDATED es inmutable
    Given muestra X en status VALIDATED
    When PATCH con {patient_ref: "x"}
    Then retorna 409 con {code: "IMMUTABLE_AFTER_VALIDATED"}

  Scenario: patient_ref demasiado corto
    When PATCH con {patient_ref: ""}
    Then retorna 400 con {code: "VALIDATION_ERROR", field: "patient_ref", detail: "min_length=1"}
```

### UC-S-005: Eliminar muestra (DELETE)

```gherkin
Feature: Soft-delete muestra (DELETE /api/clinic/samples/{id}/)
  Scenario: Admin elimina muestra PENDING_AI
    Given soy admin y muestra X está en PENDING_AI
    When DELETE /api/clinic/samples/X/
    Then retorna 204 No Content
    And la muestra tiene deleted_at no nulo en DB
    And GET /api/clinic/samples/X/ retorna 404 después

  Scenario: Analista intenta eliminar
    When DELETE /api/clinic/samples/X/ con JWT de analista
    Then retorna 403 con {code: "ADMIN_ONLY"}

  Scenario: Intentar eliminar muestra VALIDATED
    Given muestra X en status VALIDATED
    When DELETE con JWT de admin
    Then retorna 409 con {code: "CANNOT_DELETE_VALIDATED", detail: "muestra firmada, contactar al Director del Laboratorio"}
```

### UC-S-006: Procesar muestra (encolar pipeline)

```gherkin
Feature: Disparar pipeline (POST /api/clinic/samples/{id}/process/)
  Scenario: Analista procesa muestra propia en PENDING_AI
    Given soy analista dueño de muestra X en PENDING_AI
    And el FastAPI clínico está disponible en http://localhost:8000
    When POST /api/clinic/samples/X/process/ con {force_reprocess: false}
    Then retorna 202 con {sample_id, task_id, status: "queued"}
    And la muestra pasa a status PROCESSING (actualizado por Celery callback)
    And el frontend inicia polling cada 2s a GET /status/

  Scenario: Muestra ya está en PROCESSING
    Given muestra X en status PROCESSING
    When POST /process/
    Then retorna 409 con {code: "ALREADY_PROCESSING"}

  Scenario: Muestra en READY (reprocess permitido con force=true)
    Given muestra X en status READY
    When POST /process/ con {force_reprocess: true}
    Then retorna 202 con nuevo task_id

  Scenario: FastAPI clínico no disponible (RN-07: modo degradado)
    Given el FastAPI clínico está caído
    When POST /process/
    Then retorna 503 con {code: "ML_DEGRADED", detail: "Pipeline no disponible. Use el modo manual."}
    And el frontend muestra DegradedBanner con instrucciones de análisis manual

  Scenario: FastAPI responde lento (circuit breaker)
    Given el FastAPI ha fallado 3 veces consecutivas en los últimos 60s
    When POST /process/
    Then retorna 503 inmediatamente sin intentar el FastAPI
    And el circuit breaker se resetea después de 60s de cooldown
```

### UC-S-007 (polling): Estado del pipeline

```gherkin
Feature: Estado del pipeline (GET /api/clinic/samples/{id}/status/)
  Scenario: Polling durante procesamiento
    Given muestra X en PROCESSING con task_id=abc123
    When GET /api/clinic/samples/X/status/ cada 2s
    Then retorna {sample_id, status: "PROCESSING", progress: 0.45, task_id, last_event_at}
    And el frontend termina el polling cuando status pasa a READY/VALIDATED/REJECTED

  Scenario: Muestra completada
    Given muestra X en READY
    When GET /status/
    Then retorna {status: "READY", chromosome_count: 46, confidence_avg: 0.92, ...}

  Scenario: Muestra rechazada por confianza <0.85 (RN-01)
    Given muestra X en REJECTED
    When GET /status/
    Then retorna {status: "REJECTED", reason: "confidence_avg < 0.85", chromosomes_low_confidence: 12}
```

## §3. Wireframes ASCII (4 páginas React)

### §3.1 SampleListPage (`/clinic/samples`)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  [BIOMED UMSS]  Muestras     Usuario: Dra. García [analista]   [Salir] │
├─────────────────────────────────────────────────────────────────────────┤
│  Gestión de Muestras                          [+ Nueva Muestra]         │
│  8 muestras registradas                                                │
│                                                                         │
│  🔍 [Buscar CHN, paciente...]    Estado: [Todas ▾]  Fechas: [...—...] │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ CHN         │ Paciente   │ Estado      │ Fecha       │ Acciones │   │
│  ├─────────────────────────────────────────────────────────────────┤   │
│  │ CHN-2026-…  │ ANON-442   │ 🟠 Revisión │ 2026-04-10  │ Ver Proc │   │
│  │ CHN-2026-…  │ ANON-441   │ 🔵 Proceso  │ 2026-04-09  │ Ver Proc │   │
│  │ CHN-2026-…  │ ANON-440   │ 🟢 Validada │ 2026-04-08  │ Ver Info │   │
│  │ ...                                                              │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  Mostrando 1-8 de 8       [« ‹ 1 › »]                                 │
└─────────────────────────────────────────────────────────────────────────┘
```

### §3.2 SampleFormPage (modal o página dedicada)

```
┌──────────────────────────────────────────────────────────────┐
│  Nueva Muestra                                          [✕]  │
├──────────────────────────────────────────────────────────────┤
│  CHN *           [CHN-2026-07-12-0001        ]              │
│                                                              │
│  Paciente *       [ANON-001                    ]              │
│                                                              │
│  Imagen (S3 path) [s3://biomed/CHN-...-0001.tiff]            │
│                                                              │
│  Metadata (opcional, JSON):                                  │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ { "gender": "M", "age": 28, "notes": "..." }       │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
│                              [Cancelar]  [Guardar Muestra]   │
└──────────────────────────────────────────────────────────────┘
```

### §3.3 SampleDetailPage (`/clinic/samples/{id}`)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  [BIOMED UMSS]  Muestras / CHN-2026-07-12-0001     [analista]  [Salir]│
├─────────────────────────────────────────────────────────────────────────┤
│  CHN-2026-07-12-0001                                                   │
│  Paciente: ANON-001     Estado: 🟠 Revisión                            │
│  Creada: 2026-07-12 10:34   Por: Dra. García                          │
│                                                                         │
│  Metadata:                                                              │
│  • Género: M    • Edad: 28   • Notas: "Posible variante estructural"  │
│                                                                         │
│  [▶ Procesar]  [✏ Editar]  [🗑 Eliminar]  [📄 Ver cariotipo →]         │
│                                                                         │
│  Estado del pipeline:                                                   │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  ● PENDING_AI → ● PROCESSING (45%) → ○ READY                   │   │
│  │  task_id: abc123    chromosomes: 0/46    confidence_avg: —     │   │
│  │  ⏳ Polling cada 2s...                                         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### §3.4 DegradedModePage (RN-07)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ⚠️  Modo Degradado — Pipeline de IA no disponible                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  El pipeline de inferencia (U-Net + EfficientNet) no responde.         │
│  Esto puede deberse a mantenimiento programado o falla del servidor.   │
│                                                                         │
│  ¿Qué puede hacer?                                                     │
│  ─────────────────                                                      │
│  1. Las muestras existentes siguen disponibles para consulta.          │
│  2. Puede CREAR nuevas muestras (quedan en PENDING_AI).                │
│  3. NO puede disparar el pipeline automático.                          │
│  4. Para análisis manual, use el flujo clásico:                        │
│     • Descargue la imagen desde S3                                     │
│     • Use la herramienta de análisis externo (recurso IT)             │
│     • Ingrese el resultado manualmente en el visor vanilla             │
│                                                                         │
│  [↻ Reintentar]  [← Volver a la lista]                                │
│                                                                         │
│  Última verificación: 2026-07-12 10:42:15                             │
│  Cooldown: 60s entre reintentos                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## §4. Contratos JSON (request/response)

### SampleRead (GET detail)

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "chn_code": "CHN-2026-07-12-0001",
  "patient_ref": "ANON-001",
  "image_path": "s3://biomed/CHN-2026-07-12-0001.tiff",
  "status": "READY",
  "analyst": {
    "id": 42,
    "username": "dra_garcia",
    "full_name": "Dra. María García"
  },
  "supervisor": {
    "id": 7,
    "username": "sup_lopez",
    "full_name": "Dr. Carlos López"
  },
  "metadata": {
    "gender": "M",
    "age": 28,
    "notes": "Posible variante estructural"
  },
  "created_at": "2026-07-12T10:34:22Z",
  "updated_at": "2026-07-12T11:05:00Z",
  "chromosome_count": 46,
  "confidence_avg": 0.92
}
```

### SampleListItem (GET list, shape liviano)

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "chn_code": "CHN-2026-07-12-0001",
  "patient_ref": "ANON-001",
  "status": "READY",
  "analyst_name": "Dra. María García",
  "has_karyotype": true,
  "created_at": "2026-07-12T10:34:22Z",
  "updated_at": "2026-07-12T11:05:00Z"
}
```

### SampleCreateRequest (POST)

```json
{
  "chn_code": "CHN-2026-07-12-0001",
  "patient_ref": "ANON-001",
  "image_path": "s3://biomed/CHN-2026-07-12-0001.tiff",
  "metadata": {
    "gender": "M",
    "age": 28,
    "notes": "..."
  }
}
```

### SampleUpdateRequest (PATCH — RN-04 enforcement)

```json
{
  "patient_ref": "ANON-001-actualizado"
}
```

> **RN-04/05 enforcement:** el serializer rechaza explícitamente los
> campos `iscn_nomenclature`, `edits`, `status`, `chn_code`,
> `image_path`, `created_at`, `updated_at` en PATCH. Ver
> `test_serializer_rejects_iscn_nomenclature` y
> `test_update_cannot_change_status` en §9.

### SampleListResponse (GET list)

```json
{
  "items": [ /* SampleListItem[] */ ],
  "total": 8,
  "page": 1,
  "page_size": 25
}
```

### ProcessRequest (POST /process/)

```json
{
  "force_reprocess": false
}
```

### ProcessResponse (POST /process/, 202 Accepted)

```json
{
  "sample_id": "550e8400-e29b-41d4-a716-446655440000",
  "task_id": "abc123-def456-...",
  "status": "queued"
}
```

### MLDegradedError (503, RN-07)

```json
{
  "code": "ML_DEGRADED",
  "detail": "Pipeline de IA no disponible. Use el modo manual.",
  "retry_after_seconds": 60
}
```

## §5. Estados de UI (4 estados × 4 páginas)

| Página | Loading | Error | Success | Degraded (RN-07) |
|---|---|---|---|---|
| `SampleListPage` | Skeleton de tabla (5 filas placeholder) | Banner rojo + botón "Reintentar" | Tabla con 8 muestras, toast "Muestra creada" | Banner amarillo arriba: "Pipeline degradado" |
| `SampleFormPage` | Botón Guardar disabled + spinner | Validación inline (Zod) + banner | Toast "Muestra creada", redirect a lista | N/A (no toca pipeline) |
| `SampleDetailPage` | Skeleton de metadata | Banner rojo + "Reintentar" | Polling activo (status badge actualizado) | Botón "Procesar" deshabilitado + `DegradedBanner` con link a manual |
| `DegradedModePage` | Spinner central mientras verifica FastAPI | "FastAPI no responde después de 5s" | N/A (es la página degradada) | N/A (la página existe porque el sistema está degradado) |

## §6. Tabla de roles/permisos (3 roles × 6 endpoints)

| Endpoint | analista | supervisor | admin |
|---|:---:|:---:|:---:|
| `POST /samples/` | 201 | 201 | 201 |
| `GET /samples/` | 200 (solo propias) | 200 (todas) | 200 (todas) |
| `GET /samples/{id}/` | 200 (solo propias) | 200 | 200 |
| `PATCH /samples/{id}/` | 200 (solo propias PENDING_AI/READY) | 200 | 200 |
| `DELETE /samples/{id}/` | 403 | 403 | 204 (no si VALIDATED) |
| `POST /samples/{id}/process/` | 202 (solo propias) | 202 | 202 |

> **RN-06 segregación:** el mismo usuario NO puede ser analista y
> supervisor en casos críticos (validado a nivel DB por FKs distintos
> `analyst_id` vs `supervisor_id`).

### §6.1 Mapeo rol → campos Django (ADR-0018, cierre de este gap 2026-07-13)

Esta tabla estuvo sin cerrar en código desde la redacción original de esta
spec — `backend-clinic` no tenía `AUTH_USER_MODEL` propio ni campo `role`.
ADR-0018 resuelve derivando el rol de los campos ya existentes del `User`
por defecto de Django (sin migración nueva):

| Rol (esta tabla) | `is_staff` | `is_superuser` | Permission class aplicada |
|---|:---:|:---:|---|
| `analista` | `False` | `False` | `IsClinicRole` + scoping `analyst=request.user` |
| `supervisor` | `True` | `False` | `IsClinicRole` (ve todas, no puede `DELETE`) |
| `admin` | `True` | `True` | `IsClinicRole` + `IsAdminRole` (único que puede `DELETE`) |

`GET /samples/{id}/` y `PATCH /samples/{id}/` (antes inexistentes) y
`DELETE /samples/{id}/` (antes inexistente) se implementan en
`SampleDetailView` per ADR-0018. `POST /process/` y `GET /status/` de la
tabla de arriba permanecen fuera de alcance — no se exponen como endpoints
de re-proceso sobre una muestra existente (el disparo de IA para una
muestra nueva ya existe vía `SampleRegisterView`, ADR-0016).

## §7. Casos de aceptación (CA-1 a CA-6)

| # | Caso | Pasos | Esperado |
|---|---|---|---|
| **CA-1** | Crear → listar → procesar → ver en `correccion de cariotipo.html` | 1. Login analista<br>2. Crear muestra `CHN-TEST-001`<br>3. Verificar aparece en lista con status PENDING_AI<br>4. Click "Procesar"<br>5. Polling cada 2s<br>6. Status pasa a PROCESSING → READY (en <30s asumiendo FastAPI mockeado)<br>7. Click "Ver cariotipo" abre `correccion de cariotipo.html?sample=UUID` con el caso cargado | Lista actualizada, status READY, link funcional |
| **CA-2** | Filtros + paginación coexisten | 1. Filtro status=READY<br>2. Filtro CHN "CHN-2026-07"<br>3. Paginación page=2 page_size=10 | Tabla muestra intersección de filtros, paginación correcta |
| **CA-3** | Modo degradado | 1. Apagar FastAPI clínico (`docker stop` o `kill`)<br>2. Login analista<br>3. Crear muestra → 201 OK<br>4. Click "Procesar" → 503 ML_DEGRADED<br>5. `DegradedBanner` aparece con instrucciones | UI muestra modo degradado, CRUD sigue funcionando |
| **CA-4** | RN-04 enforcement (PATCH rechaza iscn_nomenclature) | 1. Login analista<br>2. PATCH muestra con `{iscn_nomenclature: "47,XY,+21"}` | 400 con `code: FIELD_NOT_ALLOWED` + audit log del intento |
| **CA-5** | RN-06 segregación (analista no edita muestra ajena) | 1. Login analista A<br>2. Intentar PATCH muestra del analista B | 403 con `code: NOT_OWNER` |
| **CA-6** | Cobertura RN-09 ≥90% | 1. `pytest --cov-fail-under=90` en backend-clinic/<br>2. `npm run test:coverage` en frontend-clinic/ | Ambos exit code 0 |

## §8. Integración con el pipeline FastAPI (R6, R9 del plan)

### §8.1 `pipeline_client.py` — el cliente Django → FastAPI

```python
# backend-clinic/apps/samples/pipeline_client.py (extracto)
class PipelineClient:
    def __init__(self, base_url: str, timeout: float = 2.0):
        self.base_url = base_url
        self.timeout = timeout
        self._failures = 0
        self._circuit_open_until = 0.0
        self._lock = asyncio.Lock()

    async def trigger_processing(self, sample_id: str) -> dict:
        if time.time() < self._circuit_open_until:
            raise MLDegradedError("circuit open")
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/api/v1/samples/{sample_id}/process/",
                    json={"force_reprocess": False}
                )
                resp.raise_for_status()
                async with self._lock:
                    self._failures = 0
                return resp.json()
        except (httpx.TimeoutException, httpx.HTTPError) as e:
            async with self._lock:
                self._failures += 1
                if self._failures >= 3:
                    self._circuit_open_until = time.time() + 60
            raise MLDegradedError(str(e)) from e

    async def get_status(self, sample_id: str) -> dict:
        # similar, sin circuit breaker (es read-only)
        ...
```

### §8.2 Contrato HTTP Django ↔ FastAPI

| Verbo | Path | Request | Response |
|---|---|---|---|
| `POST` | `/api/v1/samples/{id}/process/` | `{force_reprocess: bool}` | `202 {sample_id, task_id, status}` |
| `GET` | `/api/v1/samples/{id}/status/` | — | `200 {status, progress, chromosome_count, confidence_avg}` |

### §8.3 Manejo de errores en el viewset

```python
# backend-clinic/apps/samples/views.py (extracto)
class ProcessSampleView(APIView):
    def post(self, request, pk):
        sample = self.get_object()
        try:
            result = pipeline_client.trigger_processing(sample.id)
            return Response(result, status=202)
        except MLDegradedError:
            return Response(
                {"code": "ML_DEGRADED", "detail": "..."},
                status=503
            )
```

### §8.4 Frontend → Django (NUNCA React → FastAPI directo)

El frontend React solo habla con el Django clínico:

```
React (:5174)  →  Django (:8002)  →  FastAPI (:8000)
                      ↓
                  SimpleJWT
```

El proxy Vite `/api/pipeline/*` queda documentado pero **no se usa
en este release** (R6/R9 del plan: defensa en profundidad, pero el
flujo real va por Django).

## §9. Métricas de cobertura RN-09 (gates separados)

| Stack | Threshold lines | Threshold branches | Threshold funcs | Threshold stmts | Comando |
|---|:---:|:---:|:---:|:---:|---|
| `backend-clinic/` | ≥90% | ≥90% | ≥90% | ≥90% | `pytest --cov-fail-under=90` |
| `frontend-clinic/` | ≥90% | **≥88%** | ≥90% | ≥90% | `npm run test:coverage` |

> **Branches 88% en frontend** por la misma razón documentada en
> `SPEC-007` y memoria `feedback-rn09-v8-html-trap`: v8 no mide bien
> `if/else` simples en JSX. El umbral 88% es el equilibrio entre rigor
> y representatividad para HTML/JSX liviano.

### Tabla de tests objetivo

| Archivo | Tests | Cubre |
|---|:---:|---|
| `test_models.py` | 5 | chn_code unique, soft-delete, FKs, `metadata_json` |
| `test_serializers.py` | 6 | rechazo `iscn_nomenclature`, `edits`, `status`, `chn_code`, validación `patient_ref` |
| `test_permissions.py` | 8 | RN-06: analista solo ve propias, supervisor ve todas, admin-only delete |
| `test_services.py` | 10 | `list` con filtros, paginación, scoping por rol, `update` con scoping, `delete` soft-delete, `trigger_processing` |
| `test_views.py` | 25 | 6 endpoints × 4-5 escenarios (200, 400, 401, 403, 404, 409) + auth |
| `test_pipeline_client.py` | 6 | timeout 2s, 503 ML_DEGRADED, 200 OK, circuit breaker (3 fallos), reset tras 60s, get_status |
| **Subtotal backend** | **~60 tests** | ≥90% RN-09 |
| `samplesClient.spec.ts` | 8 | 6 funciones + 401/403/503 |
| `sampleTable.spec.tsx` | 6 | render, paginación, filtros, gating por rol |
| `sampleFormModal.spec.tsx` | 5 | crear, editar, validación Zod |
| `processButton+statusPoller.spec.tsx` | 5 | click encola, polling termina, timeout |
| `degradedBanner.spec.tsx` | 3 | render, retry, dismiss |
| `sampleListPage.spec.tsx` | 5 | E2E con MSW |
| `sampleDetailPage.spec.tsx` | 4 | E2E con MSW |
| `mswBootstrap.spec.tsx` | 4 | SW registrado, handlers activos |
| **Subtotal frontend** | **~50 tests** | ≥90% lines/funcs/statements, 88% branches |
| **TOTAL** | **~110 tests** | RN-09 cumplido en 2 stacks |

## §10. Trazabilidad

- **Sube a:** `BRD §3.1` (Cariotipado clínico) → `FSD-UC-001` (Ingesta + CHN) → `FSD-UC-CRUD-MUESTRA-001` (a crear) → `DD-CRUD-MUESTRA-001` (superseded) → `ADR-0015` → **esta SPEC-008**.
- **Genera:**
  - `PR-IMPL-MUESTRA-002` (bootstrap Django clínico + React clínico + tests)
  - `PM-CRUD-MUESTRA-002` (entrada en `docs/PROMPT_MAPPING.md`)
  - `backend-clinic/` (NUEVO, ~30 archivos)
  - `frontend-clinic/` (NUEVO, ~60 archivos)
  - `docker-compose.yml` raíz (NUEVO, documenta 4 servicios)
- **Impacta:**
  - `AGENTS.md §3` (nueva entrada bounded context Muestras → Django/React)
  - `AGENTS.md §5` (tabla ADRs agregar ADR-0015)
  - `AGENTS.md §6` (árbol agregar `backend-clinic/`, `frontend-clinic/`)
  - `crudmuestra.html` (banner deprecado)
  - `docs/PROMPT_MAPPING.md` (agregar PM-CRUD-MUESTRA-002)

## Notas finales

- Esta spec **NO incluye** el `correccion de cariotipo.html` ni
  `supervisor.html` (siguen vanilla). Tampoco incluye el WS del
  clínico (ADR-0009) — se usa polling cada 2s por simplicidad.
- Si el alcance crece (migrar `correccion de cariotipo.html` a React),
  abrir un ADR específico (ADR-0016) en lugar de extender esta spec.
- Verificación E2E: ver Bloque 3 del plan file
  `C:\Users\Qubits\.claude\plans\sorted-seeking-thompson.md`.
