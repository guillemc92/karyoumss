---
id: DD-CRUD-MUESTRA-001
titulo: "CRUD de Muestras (Analista) — Django 5 + React 18 (deroga parcialmente ADR-0013 según ADR-0015)"
producto: "BIOMED UMSS — Intelligent Karyotyping Platform"
grupo: "G04"
superseded_by: "ADR-0015"  # 2026-07-12: derogación parcial ADR-0013 firmada
fsd_uc:
  - "FSD-UC-001"
  - "FSD-UC-CRUD-MUESTRA-001"  # nuevo, ver §1
prd_refs:
  - "PRD-US-001"
  - "PRD-US-002"
  - "PRD-US-003"               # ver §1.2 - alta/edición/búsqueda
  - "PRD-REQ-001"
adrs:
  - "ADR-0002"  # Async Pipeline
  - "ADR-0003"  # CHN Anonymization
  - "ADR-0004"  # Evolución arquitectónica (hexagonal)
  - "ADR-0007"  # Microservicio inferencia
  - "ADR-0009"  # WebSocket + Celery
  - "ADR-0013"  # Stack split (clínico FastAPI/vanilla, admin Django/React) — derogado PARCIALMENTE por ADR-0015 solo para Muestras
  - "ADR-0015"  # Derogación parcial ADR-0013 — Stack Django + React para Muestras
prompts:
  - "PR-IMPL-MUESTRA-001"      # ver §3 (FastAPI/vanilla, reemplazado)
  - "PR-IMPL-MUESTRA-002"      # nuevo, este DD: Django + React
  - "PM-UC01-API"              # ya documentado en PROMPT_MAPPING.md §105
specs:
  - "SPEC-008-crud-muestra-react.md"  # spec técnica del stack Django/React
release: "release/2.0.0"
status: superseded
fecha: "2026-07-11"
fecha_actualizacion: "2026-07-12"
autores:
  - "Ing. Guillermo Mamani Chambi"
---

# Design Doc `DD-CRUD-MUESTRA-001` — CRUD de Muestras (Analista)

> **📌 ESTADO 2026-07-12 — SUPERSEDED por ADR-0015**
>
> La decisión arquitectónica de este DD fue **revertida** el 2026-07-12
> por el arquitecto. Ver `docs/adr/0015-derogacion-parcial-0013.md`
> (status: `accepted`) para la decisión vigente.
>
> **Decisión vigente:** stack Django 5 + DRF + SimpleJWT (backend) +
> React 18 + Vite + TS + TanStack Query + React Router 6 (frontend)
> para el bounded context Muestras. El pipeline FastAPI (U-Net +
> EfficientNet + audit Merkle + Celery) sigue intacto y es consumido
> por el Django clínico vía `pipeline_client.py` (httpx + circuit
> breaker). El FastAPI clínico **NO se reemplaza**, solo se delega.
>
> **Este DD se conserva** como referencia histórica de la decisión
> original y para mantener la trazabilidad SDD (§1 → §8 intactos). El
> detalle técnico de la implementación Django/React está en
> `docs/specs/SPEC-008-crud-muestra-react.md`.

---

## ⚠️ Decisión arquitectónica (estado original 2026-07-11, REVERTIDA por ADR-0015)

> **Esta sección conserva la decisión original con fines de trazabilidad.
> NO refleja el estado actual del proyecto.** La decisión vigente está
> en el banner superior.

Este DD proponía **NO migrar Muestras a Django ni a React**. La regla
constitucional del proyecto (ADR-0013, ratificada el 27/06/2026)
divide el monorepo por bounded context:

| Bounded context | Stack backend | Stack frontend | Apps |
|---|---|---|---|
| **clínico** (este DD original) | **FastAPI** (existente) | **vanilla HTML + JS** (existente) | `backend/app/`, `*.html` en raíz |
| **admin** (DD-ADMIN-001/002) | Django 5 + DRF | React 18 + Vite + TS | `backend-admin/`, `frontend-admin/` |

**Razones originales (ahora invalidadas por ADR-0015):**
1. La Muestra es el **artefacto central del cariotipado** — la crea
   el Analista, la procesa el pipeline U-Net + EfficientNet-B3, la
   revisa el Supervisor, la firma con MFA. Toca RN-01/02/04/05/06/07.
2. `crudmuestra.html` ya existe en la raíz y es vanilla HTML
   (35.170 bytes, mayo 2026). Migrar a React implicaría reescribir la
   UI, romper la convención "1:1 con la arquitectura clínica", y
   abrir un nuevo ADR-0015 que reemplace la decisión de split.
3. El pipeline de procesamiento (Celery + U-Net + EfficientNet) ya
   es FastAPI. El botón "Procesar" debe llamar a un endpoint FastAPI
   (`POST /api/v1/samples/{id}/process`), no a un endpoint Django.
   Cruzar bounded contexts introduce un acoplamiento que el ADR-0004
   prohíbe.
4. `FSD-UC-001` ya está implementado en FastAPI per `PM-UC01-API`
   (`backend/app/api/samples.py`). Reescribir el endpoint en Django
   es trabajo doble sin valor.

**Revocación (2026-07-12):** el arquitecto reconsideró y firmó
**ADR-0015** derogando parcialmente ADR-0013. Las razones de la
revocación están en el §Contexto y §Justificación de ADR-0015. En
resumen: consistencia arquitectónica con el admin, reuso del patrón
Django/DRF/React ya validado (5 commits, 99% cobertura), y el
hallazgo de que el código FastAPI de Muestras **no existe en el repo**
(eliminando el riesgo de reescritura).

**Lo que este DD conserva vigente (a pesar de la derogación):**

- §1 Trazabilidad SDD (cadena BRD→MRD→PRD→FSD)
- §2.1 Modelo de datos `Muestra` (los 9 campos canónicos se mantienen
  en el modelo Django `Sample` con `metadata_json` para campos legacy)
- §3 Estructura del HTML refactorizado (referencia para SPEC-008 §3
  wireframes)
- §4 Plan de pruebas (referencia para tests Django, especialmente los
  que verifican RN-04/05: rechazo de `iscn_nomenclature` y `edits`)
- §5 Riesgos (siguen aplicando: VALIDATED inmutable, pipeline >30s,
  muestras legacy con `image_path` en filesystem)
- §8 Trazabilidad (ajustada para apuntar a SPEC-008 y ADR-0015)

**Lo que este DD ya NO aplica (reemplazado por SPEC-008):**

- §2.2 Schemas Pydantic → reemplazado por DRF serializers
- §2.3 Endpoints FastAPI → reemplazado por Django views (mismo shape
  JSON, distinto path: `/api/clinic/samples/` vs `/api/v1/samples/`)
- §2.4 SampleService FastAPI → reemplazado por `SampleService` Django
- §2.5 Integración Celery → reemplazado por `pipeline_client.py`
- §3 Diseño frontend vanilla → reemplazado por React 18
- §6 Plan de implementación (T1-T12) → reemplazado por plan de 67
  tareas en el plan file `C:\Users\Qubits\.claude\plans\sorted-seeking-thompson.md`
- §7 Decisión que requiere el arquitecto → ELIMINADO (decisión tomada
  en ADR-0015)

---

## 1. Trazabilidad SDD

### 1.1 Cadena de verdad (ascendente)

```
BRD §3.1 (Cariotipado clínico)
  → MRD-04 (procesamiento asíncrono IA)
    → PRD-US-001, US-002, US-003 (alta, procesamiento, búsqueda)
      → FSD-UC-001 (Ingesta + CHN)
        → FSD-UC-CRUD-MUESTRA-001 (este DD, derivado)  ← NUEVO
          → DD-CRUD-MUESTRA-001 (este documento)
            → PR-IMPL-MUESTRA-001
              → código (backend/app/api/samples.py, crudmuestra.html)
```

### 1.2 FSD-UC-CRUD-MUESTRA-001 — Creación de nuevo UC

**Justificación:** `FSD-UC-001` cubre **solo la ingesta inicial** (1
endpoint POST + CHN). El CRUD completo implica **5 operaciones** que
no están en FSD-001:

| Op | Verbo HTTP | Endpoint | Permiso | FSD-UC-001 cubre |
|---|---|---|---|:---:|
| 1 | `POST /api/v1/samples/` | Ingesta + CHN | analista, supervisor, admin | ✅ sí |
| 2 | `GET /api/v1/samples/` | Listar con filtros | analista, supervisor, admin | ❌ no |
| 3 | `GET /api/v1/samples/{id}/` | Detalle | analista, supervisor, admin | ❌ no |
| 4 | `PATCH /api/v1/samples/{id}/` | Editar metadata (NO cariotipo) | analista (propias), supervisor (todas), admin | ❌ no |
| 5 | `DELETE /api/v1/samples/{id}/` | Soft-delete | admin | ❌ no |
| 6 | `POST /api/v1/samples/{id}/process/` | Disparar pipeline IA | analista, supervisor | ❌ no |
| 7 | `GET /api/v1/samples/{id}/status/` | Estado del pipeline (Celery task) | analista, supervisor | ❌ no |

**Acción:** crear `FSD-UC-CRUD-MUESTRA-001` en próxima iteración de
`FSD_vFinal.md` §4.x (después de §4.8 FSD-UC-ADMIN-001). Este DD
incluye el detalle funcional en §2; el FSD formal se hace en PR aparte
para no inflar este documento.

### 1.3 Alcance de este DD

- **Backend (FastAPI clínico):**
  - Extender `backend/app/api/samples.py` con las 6 operaciones nuevas (2-7)
  - Extender `backend/app/schemas/sample.py` con schemas de listado y edición
  - Implementar `SampleService` en `backend/app/services/sample_service.py`
    con la lógica de dominio (búsqueda por CHN, filtros por estado, paginación)
- **Frontend (vanilla HTML):**
  - Mejorar `crudmuestra.html` (35.170 bytes existentes): fetch real
    al backend FastAPI, paginación, filtros, modal CRUD
  - Agregar `frontend/src/services/muestraApi.js` con `fetch`
    wrapper que centraliza URL base, error handling, y emite eventos
    a `window.dispatchEvent('muestra:created', {detail: {id}})` para
    integración con `correccion de cariotipo.html`
- **Pipeline:**
  - El botón "Procesar" en el HTML llama a `POST /samples/{id}/process/`
    que encola un Celery task (ya existente per ADR-0002/0009)
- **NO se hace:**
  - Reescribir el pipeline U-Net + EfficientNet (intacto, RN-01/02)
  - Migrar a Django o React (ADR-0013 lo prohíbe)
  - Tocar el bounded context admin (DD-ADMIN-001/002 intacto)

---

## 2. Diseño backend (FastAPI clínico)

### 2.1 Modelo de datos `Muestra`

Ya existe per `backend/app/models/sample.py` (referenciado en
PROMPT_MAPPING §105). Este DD **NO redefine el modelo**, solo
documenta los campos que se exponen vía API:

| Campo | Tipo | Nullable | Notas |
|---|---|:---:|---|
| `id` | UUID | no | PK |
| `chn_code` | str(20) | no | UNIQUE, formato `CHN-YYYY-MM-DD-NNNN` |
| `patient_ref` | str | no | ID interno del paciente (NO PII; el CHN es el que se transmite) |
| `image_path` | str | no | Path S3/MinIO post-CHN |
| `status` | enum | no | `PENDING_AI` \| `PROCESSING` \| `READY` \| `VALIDATED` \| `REJECTED` \| `DELETED` |
| `analyst_id` | UUID (FK→users) | no | Quién creó la muestra |
| `supervisor_id` | UUID (FK→users) | sí | Quién validó (si aplica) |
| `created_at` | datetime | no | UTC |
| `updated_at` | datetime | no | UTC |
| `deleted_at` | datetime | sí | Soft-delete; default NULL |

**Restricciones críticas (RN-04/05):**
- `iscn_nomenclature` **NO se expone** vía PATCH. Se genera por el
  motor de reglas (FSD-UC-006) y es read-only.
- `image_path` es **read-only** post-creación. La imagen se reemplaza
  solo vía un nuevo endpoint `POST /samples/{id}/reupload/` (no en
  alcance de este DD; abrir FSD aparte si se necesita).
- `status` cambia **solo por eventos del pipeline** (Celery callbacks)
  o por acción explícita del Supervisor (`VALIDATED`, `REJECTED`).
  El Analista **no puede** cambiar `status` vía PATCH.

### 2.2 Schemas Pydantic (extender `backend/app/schemas/sample.py`)

```python
# Existente
class SampleCreate(BaseModel):
    file: UploadFile
    hospital_code: str | None = None

class SampleRead(BaseModel):
    id: UUID
    chn_code: str
    status: SampleStatus
    created_at: datetime
    # ...

# Nuevos (este DD)
class SampleListItem(BaseModel):
    """Shape liviano para listados. NO incluye image_path ni audit log."""
    id: UUID
    chn_code: str
    patient_ref: str
    status: SampleStatus
    created_at: datetime
    updated_at: datetime
    analyst_name: str       # joined, NO UUID crudo
    has_karyotype: bool     # True si tiene al menos 1 chromosome

class SampleListResponse(BaseModel):
    items: list[SampleListItem]
    total: int
    page: int
    page_size: int

class SampleUpdate(BaseModel):
    """PATCH parcial. Solo metadata editable por Analista."""
    patient_ref: str | None = Field(None, min_length=1, max_length=64)
    # NO incluir: status, chn_code, image_path, iscn_nomenclature

class SampleProcessRequest(BaseModel):
    force_reprocess: bool = False  # útil en modo degradado (RN-07)
```

### 2.3 Endpoints nuevos (extender `backend/app/api/samples.py`)

| Método | Path | Permiso | Descripción |
|---|---|---|---|
| `GET` | `/api/v1/samples/` | `analista`, `supervisor`, `admin` | Listar con filtros (`?status=`, `?chn=`, `?date_from=`, `?date_to=`, `?page=`, `?page_size=`) |
| `GET` | `/api/v1/samples/{id}/` | `analista`, `supervisor`, `admin` | Detalle completo (incluye `image_path`, `audit_log`) |
| `PATCH` | `/api/v1/samples/{id}/` | `analista` (propias), `supervisor`, `admin` | Editar `patient_ref` solamente |
| `DELETE` | `/api/v1/samples/{id}/` | `admin` | Soft-delete (set `deleted_at`) |
| `POST` | `/api/v1/samples/{id}/process/` | `analista`, `supervisor` | Encola Celery task `process_sample(id)` |
| `GET` | `/api/v1/samples/{id}/status/` | `analista`, `supervisor` | Estado del pipeline (polling fallback a WebSocket ADR-0009) |

**Permisos por rol (BR-12, RN-06 segregación):**

```python
# backend/app/permissions.py (extender)
def can_edit_sample(user, sample) -> bool:
    if user.role == "admin": return True
    if user.role == "supervisor": return True
    if user.role == "analista":
        return sample.analyst_id == user.id and sample.status in ("PENDING_AI", "READY")
    return False

def can_delete_sample(user, sample) -> bool:
    return user.role == "admin" and sample.status != "VALIDATED"
```

### 2.4 Servicio de dominio (`backend/app/services/sample_service.py`)

```python
class SampleService:
    def list(
        self,
        *,
        status: SampleStatus | None = None,
        chn_query: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        page: int = 1,
        page_size: int = 25,
        current_user: User,
    ) -> SampleListResponse:
        """Lista con filtros + paginación + scoping por rol."""
        q = Sample.query.filter(Sample.deleted_at.is_(None))
        # Scoping por rol (RN-06): analista solo ve las propias
        if current_user.role == "analista":
            q = q.filter(Sample.analyst_id == current_user.id)
        if status:    q = q.filter(Sample.status == status)
        if chn_query: q = q.filter(Sample.chn_code.ilike(f"%{chn_query}%"))
        if date_from: q = q.filter(Sample.created_at >= date_from)
        if date_to:   q = q.filter(Sample.created_at <= date_to)
        total = q.count()
        items = q.order_by(Sample.created_at.desc()) \
                 .offset((page - 1) * page_size).limit(page_size).all()
        return SampleListResponse(items=items, total=total, page=page, page_size=page_size)

    def update_metadata(self, sample_id: UUID, patch: SampleUpdate, current_user: User) -> Sample:
        sample = self.get(sample_id)
        if not can_edit_sample(current_user, sample):
            raise PermissionError("No puede editar esta muestra")
        if patch.patient_ref is not None:
            sample.patient_ref = patch.patient_ref
        sample.updated_at = datetime.utcnow()
        db.session.commit()
        return sample

    def trigger_processing(self, sample_id: UUID, current_user: User) -> dict:
        sample = self.get(sample_id)
        if current_user.role not in ("analista", "supervisor", "admin"):
            raise PermissionError("Solo analista/supervisor puede procesar")
        if sample.status not in ("PENDING_AI", "READY", "REJECTED"):
            raise ValidationError(f"No se puede procesar muestra en estado {sample.status}")
        task = celery_app.send_task("app.tasks.process_sample", args=[str(sample.id)])
        return {"task_id": task.id, "sample_id": str(sample.id), "status": "queued"}
```

### 2.5 Integración con Celery (ADR-0002/0009)

El endpoint `POST /samples/{id}/process/` encola un Celery task que
**ya existe** (`app.tasks.process_sample`). El handler HTTP solo
dispara; no ejecuta la inferencia inline (sería bloqueante). El
frontend recibe `task_id` y puede:

1. Suscribirse al WebSocket `samples/{id}/status` (ADR-0009, ya
   implementado)
2. O hacer polling a `GET /samples/{id}/status/` cada 2s (fallback)

`Sample.status` se actualiza por el callback del Celery task:
`PENDING_AI` → `PROCESSING` → (`READY` | `VALIDATED` | `REJECTED`).

---

## 3. Diseño frontend (vanilla HTML)

### 3.1 Mejoras a `crudmuestra.html` (35.170 bytes existentes)

**Lo que se preserva (no se toca):**
- Paleta CSS vars (UMSS azul/rojo)
- Estructura navbar + tabla
- Modal CRUD existente
- Iconos FontAwesome 6.4

**Lo que se agrega:**

1. **Capa de fetch centralizada** — `frontend/src/services/muestraApi.js`:
   ```javascript
   const API_BASE = (window.BIOMED_CONFIG?.apiBase) ?? '/api/v1';
   async function listSamples({status, chn, page = 1, pageSize = 25} = {}) {
     const qs = new URLSearchParams();
     if (status) qs.set('status', status);
     if (chn) qs.set('chn_query', chn);
     qs.set('page', page); qs.set('page_size', pageSize);
     const res = await fetch(`${API_BASE}/samples/?${qs}`, {
       headers: { 'Accept': 'application/json', 'Authorization': `Bearer ${getToken()}` }
     });
     if (!res.ok) throw new Error(`List failed: ${res.status}`);
     return res.json();
   }
   // createSample, getSample, updateSample, deleteSample, processSample, getStatus
   ```

2. **Tabla dinámica** — reemplazar las filas hardcoded por render
   desde `SampleListResponse.items`:
   ```javascript
   async function refreshTable() {
     const data = await listSamples(currentFilters);
     tbody.innerHTML = data.items.map(rowHtml).join('');
     renderPagination(data.total, data.page, data.page_size);
   }
   ```

3. **Filtros** — select de estado (`PENDING_AI`, `READY`, etc.),
   input de búsqueda por CHN, datepickers desde/hasta. Debounce
   300ms en input CHN.

4. **Paginación** — `« ‹ 1 2 3 ... 10 › »` con 25 items por página
   default. Cambiar `pageSize` a 50/100 requiere confirmación
   (afecta performance en `correccion de cariotipo.html` downstream).

5. **Modal CRUD** — el modal existente se conecta a `createSample` /
   `updateSample`. Validación: `patient_ref` 1-64 chars, no vacío.

6. **Botón "Procesar"** — llama `processSample(id)`, muestra toast
   "Procesamiento encolado, task_id: …", actualiza fila a status
   `PROCESSING`. El modal muestra el log de WebSocket events.

7. **Exportación CSV** — botón "Exportar" genera CSV con las columnas
   visibles (CHN, paciente, status, fecha). Client-side, no server-side
   (las 25-rows-por-página es lo que se exporta, no el total — si se
   quiere todo, abrir FSD aparte para export server-side).

8. **Enlace a corrección de cariotipo** — botón "Ver cariotipo" en
   cada fila abre `correccion de cariotipo.html?sample={id}`. El HTML
   destino ya lee el param y carga el caso (ver FSD-UC-003).

9. **Indicador de modo degradado (RN-07)** — si el backend devuelve
   `503 Service Unavailable` con `code: "ML_DEGRADED"`, mostrar banner
   "Modo degradado: las muestras se pueden crear pero no procesar
   automáticamente. Use el flujo manual."

### 3.2 Estructura del HTML refactorizado

```
crudmuestra.html (existente, refactorizado)
├── <head> — mismo CSS + Inter font + FontAwesome (sin cambios)
├── <body>
│   ├── .navbar (existente, intacto)
│   ├── .main-container
│   │   ├── .toolbar
│   │   │   ├── filtros (status, chn, fechas)
│   │   │   ├── botones [+ Nueva muestra] [⟳ Refrescar] [⤓ Exportar CSV]
│   │   ├── .biomed-banner--degraded (RN-07, hidden por default)
│   │   ├── .table-wrapper
│   │   │   └── <table id="samples-table"> con <thead>+<tbody>
│   │   ├── .pagination (render dinámico)
│   │   ├── .modal.crud (existente, conectado a API)
│   │   └── .toast-container
│   └── <script type="module">
│       ├── import muestraApi from '@/services/muestraApi.js'
│       ├── state: { filters, page, pageSize, total, items }
│       ├── refreshTable(), applyFilters(), resetFilters()
│       ├── onCreate(), onEdit(), onDelete(), onProcess()
│       └── boot: refreshTable() al cargar
```

### 3.3 Reglas de UI

- **Gating por rol** — si `localStorage['biomed:auth:role'] === 'analista'`,
  ocultar botones "Eliminar" y "Editar supervisor". La defensa real
  está en el backend; el UI es cortesía (no seguridad).
- **Trazabilidad de clicks** — cada acción CRUD emite
  `window.dispatchEvent('muestra:created', {detail: {id}})` para que
  `correccion de cariotipo.html` (si está abierto en otra pestaña)
  refresque automáticamente. Útil para el flujo "crear muestra → ver
  cariotipo".

---

## 4. Plan de pruebas (cobertura RN-09 ≥90%)

### 4.1 Tests backend (pytest)

**`backend/app/tests/test_sample_crud.py`** (nuevo, ~250 LOC, ~25 tests):

| Test | Verifica |
|---|---|
| `test_list_samples_anonimo_401` | GET sin token → 401 |
| `test_list_samples_analista_scoped` | analista solo ve sus propias muestras |
| `test_list_samples_supervisor_ve_todas` | supervisor ve todas |
| `test_list_samples_filtro_chn` | `?chn_query=CHN-2026-07` filtra |
| `test_list_samples_filtro_status` | `?status=READY` filtra |
| `test_list_samples_filtro_fechas` | `?date_from=&date_to=` filtra |
| `test_list_samples_paginacion` | `?page=2&page_size=10` retorna items 11-20 |
| `test_get_sample_detalle` | GET por id retorna `SampleRead` completo |
| `test_get_sample_404_si_no_existe` | id inexistente → 404 |
| `test_update_sample_analista_propia` | analista edita su propia PENDING_AI |
| `test_update_sample_analista_ajena_403` | analista edita muestra de otro → 403 |
| `test_update_sample_no_puede_cambiar_status` | PATCH con `status` es ignorado |
| `test_update_sample_no_puede_cambiar_chn` | PATCH con `chn_code` es ignorado |
| `test_update_sample_validated_inmutable` | muestra VALIDATED no se puede editar |
| `test_delete_sample_admin` | admin elimina (soft-delete) |
| `test_delete_sample_analista_403` | analista intenta eliminar → 403 |
| `test_delete_sample_validated_409` | muestra VALIDATED no se puede eliminar |
| `test_process_sample_analista` | POST /process encola Celery task |
| `test_process_sample_ya_processing_409` | status PROCESSING → 409 |
| `test_process_sample_no_auth_401` | sin token → 401 |
| `test_get_status_polling` | GET /status retorna estado actual |
| `test_audit_trail_crea_evento` | cada CRUD genera evento en audit_log |
| `test_audit_trail_append_only` | UPDATE en audit_log está bloqueado (RN-05) |
| `test_pii_no_expuesto_en_list` | listado NO incluye `patient_name`, solo `patient_ref` |
| `test_chn_unico` | crear 2 con mismo CHN → 409 |

**`backend/app/tests/test_sample_service.py`** (nuevo, ~120 LOC, ~12 tests):
- Tests unitarios del `SampleService` sin HTTP (mockean `current_user`)

### 4.2 Tests frontend (Vitest + jsdom)

**`frontend/tests/crudmuestra.spec.js`** (nuevo, ~150 LOC, ~10 tests):

| Test | Verifica |
|---|---|
| `test_renderiza_filas_desde_api` | tabla se llena con respuesta de `listSamples` |
| `test_filtro_chn_debounce_300ms` | 2 inputs en <300ms → 1 sola llamada |
| `test_filtro_status_cambia_tabla` | cambiar select status recarga |
| `test_paginacion_next_prev` | botones funcionan, page cambia |
| `test_boton_procesar_llama_api` | click → `processSample(id)` llamado |
| `test_boton_procesar_muestra_toast` | toast con task_id aparece |
| `test_modal_create_submit` | submit → `createSample` → modal cierra |
| `test_modal_edit_submit` | submit → `updateSample` → modal cierra |
| `test_export_csv_genera_string` | click → CSV con header correcto |
| `test_gating_analista_oculta_delete` | analista no ve botón Eliminar |

**`frontend/tests/muestraApi.spec.js`** (nuevo, ~80 LOC, ~6 tests):
- `listSamples` construye URL correcta
- `processSample` retorna `task_id`
- Error 401 → `throw new Error('No autenticado')`
- Error 503 con `code: "ML_DEGRADED"` → `throw new DegradedError(...)`

### 4.3 Tests de integración (manual + opcional Playwright)

- **CA-1:** Crear muestra → aparece en tabla con status `PENDING_AI` → click "Procesar" → status cambia a `PROCESSING` → llega WebSocket event → status `READY` → click "Ver cariotipo" abre `correccion de cariotipo.html` con el caso cargado.
- **CA-2:** Filtro CHN + filtro status + paginación coexisten sin romperse.
- **CA-3:** Modo degradado: backend devuelve 503 → UI muestra banner + deshabilita botón "Procesar".

### 4.4 Métricas de cobertura

| Capa | Threshold RN-09 | Línea base | Target |
|---|:---:|:---:|:---:|
| Backend `backend/app/services/sample_service.py` | ≥90% | 0% (nuevo) | 95% |
| Backend `backend/app/api/samples.py` | ≥90% | ~70% (parcial) | 92% |
| Frontend `frontend/src/services/muestraApi.js` | ≥90% | 0% (nuevo) | 95% |
| Frontend `crudmuestra.html` (IIFE refactorizada) | ≥90% | 0% (nuevo) | 90% |

---

## 5. Riesgos y mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|:---:|:---:|---|
| El analista borra accidentalmente una muestra VALIDATED | Media | Alto | Soft-delete + audit trail + restricción backend (no eliminar si VALIDATED) |
| El pipeline tarda >30s y el timeout del navegador mata la request | Alta | Medio | `processSample` retorna inmediatamente con `task_id`; UI usa WebSocket para actualización |
| Muestras legacy con `image_path` en filesystem (no S3) | Media | Alto | Validar path en GET; si no existe, marcar muestra como `REJECTED` con nota |
| Scope creep: cambiar PATCH para permitir editar `status` | Alta | Alto (viola RN-04) | Test explícito `test_update_sample_no_puede_cambiar_status` + code review checklist |
| Decisión del arquitecto de migrar a React+Django | Baja | Catastrófico (rompe ADR-0013) | Este DD se cierra; si cambia, se abre ADR-0015 y DD-CRUD-MUESTRA-002 |
| RN-09 cobertura cae al integrar todo | Media | Medio | Tests escritos primero (TDD); gate `fail_under=90` en pytest.ini |

---

## 6. Plan de implementación (PR-IMPL-MUESTRA-001)

| # | Tarea | Esfuerzo | Bloqueante |
|---|---|:---:|---|
| T1 | Spec formal `SPEC-008-crud-muestra.md` con Gherkin completo | 2h | sí |
| T2 | Extender `backend/app/schemas/sample.py` con `SampleListItem`, `SampleListResponse`, `SampleUpdate` | 1h | T1 |
| T3 | Crear `backend/app/services/sample_service.py` con `SampleService.list/update/trigger_processing` | 3h | T2 |
| T4 | Extender `backend/app/api/samples.py` con 6 endpoints nuevos (list, get, patch, delete, process, status) | 3h | T3 |
| T5 | Extender `backend/app/permissions.py` con `can_edit_sample`, `can_delete_sample` | 1h | T3 |
| T6 | Tests pytest: `test_sample_crud.py` (25 tests) + `test_sample_service.py` (12 tests) | 4h | T3, T4 |
| T7 | Crear `frontend/src/services/muestraApi.js` con 6 funciones | 1h | T4 |
| T8 | Refactorizar `crudmuestra.html` para usar `muestraApi` + tabla dinámica + filtros + paginación + modal CRUD + CSV | 6h | T7 |
| T9 | Tests Vitest: `crudmuestra.spec.js` (10) + `muestraApi.spec.js` (6) | 3h | T7, T8 |
| T10 | Crear `FSD-UC-CRUD-MUESTRA-001` en `FSD_vFinal.md` §4.x | 1h | T1 |
| T11 | Agregar PM-CRUD-MUESTRA-001 a `PROMPT_MAPPING.md` | 30min | T1-T9 |
| T12 | Commit + push a `feature/django-admin-stack` (o nueva rama `feature/crud-muestra`) | 30min | T11 |
| **Total** | | **~26h** | |

---

## 7. Decisión que requiere el arquitecto

**¿Aprobás:**
1. La decisión de **no migrar a Django/React** (mantener FastAPI + vanilla HTML) documentada en §0?
2. La creación del nuevo **FSD-UC-CRUD-MUESTRA-001** (T10) o preferís que las 6 operaciones nuevas se documenten como extensión de FSD-UC-001?
3. El **scope de T8** (refactor de `crudmuestra.html` con tabla dinámica, filtros, paginación, modal CRUD, CSV) o preferís un MVP más pequeño (solo listar + crear + procesar)?

---

## 8. Trazabilidad SDD

- **Sube a:** BRD §3.1 (Cariotipado clínico) → PRD-US-001, US-002, US-003 → FSD-UC-001 → este DD
- **Baja a:** `SPEC-008-crud-muestra.md` (a crear) → `PR-IMPL-MUESTRA-001` → código → tests → `PROMPT_MAPPING.md` (PM-CRUD-MUESTRA-001)
- **Impacta:**
  - `FSD_vFinal.md` — nuevo UC §4.x FSD-UC-CRUD-MUESTRA-001 (T10)
  - `PROMPT_MAPPING.md` — nueva entrada PM-CRUD-MUESTRA-001 (T11)
  - `backend/app/api/samples.py` — 6 endpoints nuevos
  - `backend/app/schemas/sample.py` — 3 schemas nuevos
  - `backend/app/services/sample_service.py` — archivo nuevo
  - `backend/app/permissions.py` — 2 funciones nuevas
  - `crudmuestra.html` — refactor (no rewrite)
  - `frontend/src/services/muestraApi.js` — archivo nuevo
  - `frontend/tests/` — 2 archivos de tests nuevos
  - `backend/app/tests/` — 2 archivos de tests nuevos

---

## Notas

- Este DD es **propuesto**, no aprobado. Requiere sign-off del
  arquitecto (sección 7) antes de generar SPEC-008.
- Si la respuesta a §7.1 es "sí, Django + React", este DD se
  supersede y se abre ADR-0015 derogando parcialmente ADR-0013.
  Hasta entonces, **el stack constitucional es FastAPI + vanilla**.
- El esfuerzo total (~26h) cabe en un sprint de 3 días del
  arquitecto (1 solo integrante, ~8h/día).
- Vinculado a [[p1-bug-creacion-usuarios-2026-07-10]] (lección: no
  descartar stack constitucional sin evidencia) y a
  [[reference-key-files]] (mapa del repo).
