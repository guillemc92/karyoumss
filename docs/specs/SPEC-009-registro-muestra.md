---
id: SPEC-009
titulo: "Registro de Muestras — formulario paciente + captura de metafases"
bounded_context: muestras-clinico
documento_driving: ADR-0016
stack:
  backend: "Django 5 + DRF 3.15 + SimpleJWT 5 + SQLite (dev) + cryptography (Fernet)"
  frontend: "React 18 + Vite 5 + TypeScript 5 + TanStack Query 5 + React Router 6"
  ui_contract: "registrarmuestrafinal.html (raíz del repo, 1062 líneas)"
version: 0.1
fecha: "2026-07-12"
autor: "Ing. Guillermo Mamani Chambi"
estado: proposed
agents_conformance: "§11 (PR a release/2.0.0), RN-03/04/05/06/07"
refs:
  - "ADR-0016 (PatientVault + SampleImage + DRAFT)"
  - "ADR-0015 (derogación parcial ADR-0013, CRUD Muestras)"
  - "ADR-0003 (CHN Anonymization at the Edge)"
  - "SPEC-008 (CRUD de Muestras, precedente)"
  - "RN-03, RN-04, RN-05, RN-06, RN-07, RN-09"
---

# SPEC-009 — Registro de Muestras (formulario paciente + captura de metafases)

> Implementa el flujo real de "Registro" descrito en `registrarmuestrafinal.html`,
> conectándolo al bounded context Muestras (Django + React) según ADR-0016.
> Sustituye el modal simple `SampleFormModal` como punto de entrada de "+ Nueva Muestra".

## §0. Contexto y motivación

El CRUD de Muestras (ADR-0015/SPEC-008) opera sobre una muestra ya existente con 3 campos. El **Registro** es el flujo de creación real usado por el laboratorio: captura datos del paciente, datos administrativos de la muestra, historial clínico, tipo de análisis solicitado, y ≥3 imágenes de metafase (recomendado ≥20), antes de disparar el análisis por IA. El HTML `registrarmuestrafinal.html` es el contrato de UI aprobado; esta spec traduce ese contrato a contratos técnicos Django/React.

## §1. Alcance y no-alcance

### Incluye
- Endpoint compuesto `POST /api/clinic/samples/register/` (crea Sample + PatientVault + N SampleImage en una transacción).
- 5 secciones de formulario React replicando el HTML: Información del Paciente, Información de la Muestra, Historial Clínico, Solicitud de Análisis, Captura de Metafases.
- Captura de imagen por cámara web (`getUserMedia`) y por archivo (`<input type=file multiple>`).
- Galería de imágenes capturadas con eliminación individual y "Limpiar todas".
- Ajustes de imagen (brillo/contraste/umbral/resolución) — aplicados client-side al capturar por cámara, igual que el HTML (`ctx.filter` en canvas).
- Guardar borrador (`is_draft=true`), Cancelar, Registrar y analizar con IA (`is_draft=false`).
- Modal de progreso IA conectado a polling real (no simulación fija).

### NO incluye
- Reescritura del pipeline FastAPI (U-Net, EfficientNet, Grad-CAM) — intacto, se consume vía `pipeline_client.py` existente.
- Edición de `iscn_nomenclature` ni tabla `edits` (RN-04/05, fuera de alcance del bounded context Django).
- Autenticación/roles nuevos — reusa `SessionProvider`/JWT de `frontend-clinic` ya implementado.
- `correccion de cariotipo.html` — se navega ahí al finalizar el registro exitoso, sin modificarlo.
- Compresión/optimización de imágenes base64 (limitación conocida documentada en ADR-0016).

## §2. Mapeo campo-por-campo: HTML → contrato JSON

### Sección 1 — Información del Paciente (`registrarmuestrafinal.html` líneas 534-570)

| Campo HTML (`id`) | Tipo HTML | Campo JSON (`patient.*`) | Destino | Obligatorio |
|---|---|---|---|---|
| `chn` | text | `sample.chn_code` | `Sample.chn_code` | Sí |
| `patientName` | text | `patient.full_name` | `PatientVault.full_name` (cifrado) | Sí |
| `birthDate` | date | `patient.birth_date` | `PatientVault.birth_date` (cifrado) | Sí |
| `gender` | select M/F/O | `sample.gender` | `Sample.metadata.gender` (no PII, reusa patrón ADR-0015) | Sí |
| `document` | text | `patient.document_id` | `PatientVault.document_id` (cifrado) | No |
| `phone` | tel | `patient.phone` | `PatientVault.phone` (cifrado) | No |

### Sección 2 — Información de la Muestra (líneas 572-620)

| Campo HTML | Tipo | Campo JSON (`sample.*`) | Destino | Obligatorio |
|---|---|---|---|---|
| `sampleCode` | text readonly, autogenerado | — (no se envía, el backend lo genera) | `Sample.sample_code` | auto |
| `sampleType` | select | `sample.sample_type` | `Sample.sample_type` | Sí |
| `cultureMethod` | select | `sample.culture_method` | `Sample.culture_method` | No |
| `collectionDate` | date | `sample.collection_date` | `Sample.collection_date` | Sí |
| `receptionDate` | date | `sample.reception_date` | `Sample.reception_date` | No |
| `requestingDoctor` | text | `sample.requesting_doctor` | `Sample.requesting_doctor` | No |
| `department` | text | `sample.department` | `Sample.department` | No |

### Sección 3 — Historial Clínico (líneas 622-633)

| Campo HTML | Tipo | Campo JSON (`clinical_history.*`) | Destino |
|---|---|---|---|
| `indication` | textarea | `clinical_history.indication` | `PatientVault.indication` (cifrado) |
| `familyHistory` | textarea | `clinical_history.family_history` | `PatientVault.family_history` (cifrado) |

### Sección 4 — Solicitud de Análisis (líneas 635-668)

6 checkboxes → array `analysis_requests: string[]`:

| Checkbox HTML (`id`) | Valor en `analysis_requests` |
|---|---|
| `analysis1` (checked por defecto) | `"karyotype_high_res"` |
| `analysis2` | `"mosaicism"` |
| `analysis3` | `"fish"` |
| `analysis4` | `"array_cgh"` |
| `analysis5` | `"fragility_study"` |
| `analysis6` | `"other"` |

### Sección 5 — Captura de Metafases (líneas 670-751)

| Elemento HTML | Comportamiento | Campo JSON |
|---|---|---|
| Botón "Conectar cámara" + `getUserMedia` | Cliente-side, no llega al backend | — |
| Botón "Capturar metafase" (`canvas.toDataURL('image/jpeg')`) | Genera 1 entrada de galería | `images[].data_base64`, `images[].source = "camera"` |
| Botón "Subir imagen" (`<input type=file multiple>`, acepta jpeg/png/tiff) | 1 entrada por archivo | `images[].data_base64`, `images[].source = "upload"` |
| Sliders brillo/contraste/umbral | Aplicados vía `ctx.filter` antes de capturar (solo cámara) | No se envían al backend (ya "horneados" en la imagen) |
| Select resolución | Configura `videoElement`/`canvas` dimensions | No se envía |
| Badge de calidad (`X/20 mínimas`) | Solo UI, no bloquea envío | — |
| Galería — eliminar individual / limpiar todas | Estado local React antes de enviar | — |

## §3. Wireframe ASCII — `SampleRegisterPage`

```
┌──────────────────────────────────────────────────────────────────────────┐
│ [BIOMED UMSS]  REGISTRO DE MUESTRAS      demo_analista [Analista] [Salir]│
├──────────────────────────────────────────────────────────────────────────┤
│  📋 Registro de Nueva Muestra                                            │
│  Complete la información del paciente y capture las imágenes de metafase │
│                                                                            │
│  ℹ️ Campos con * son obligatorios. Se requieren al menos 20 metafases.  │
│                                                                            │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │ 🧬 Datos de la Muestra                                              │  │
│  ├────────────────────────────────────────────────────────────────────┤  │
│  │ 👤 INFORMACIÓN DEL PACIENTE                                         │  │
│  │  [CHN *]        [Nombre completo *]      [F. nacimiento *]          │  │
│  │  [Género *]     [Documento]              [Teléfono]                 │  │
│  │                                                                      │  │
│  │ 🧪 INFORMACIÓN DE LA MUESTRA                                        │  │
│  │  [Código auto]  [Tipo muestra *]         [Método cultivo]           │  │
│  │  [F. recolección *]  [F. recepción]                                 │  │
│  │  [Médico solicitante] [Departamento]                                │  │
│  │                                                                      │  │
│  │ 📝 HISTORIAL CLÍNICO                                                │  │
│  │  [Motivo de consulta...........................]                   │  │
│  │  [Antecedentes familiares......................]                   │  │
│  │                                                                      │  │
│  │ 🔬 SOLICITUD DE ANÁLISIS                                            │  │
│  │  ☑ Cariotipo alta resolución   ☐ Array-CGH                         │  │
│  │  ☐ Mosaicismo                  ☐ Fragilidad cromosómica            │  │
│  │  ☐ FISH                        ☐ Otro                              │  │
│  │                                                                      │  │
│  │ 📷 CAPTURA DE METAFASES                                             │  │
│  │  ┌─────────────────────┐  ┌──────────────────────┐                 │  │
│  │  │ Vista previa cámara │  │ Ajustes de imagen     │                 │  │
│  │  │ [Conectar cámara]   │  │ Brillo    [====|===]  │                 │  │
│  │  │ [Capturar] [Subir]  │  │ Contraste [====|===]  │                 │  │
│  │  └─────────────────────┘  │ Umbral    [====|===]  │                 │  │
│  │                            │ Calidad: ⚠️ Faltan 17 │                 │  │
│  │                            └──────────────────────┘                 │  │
│  │  Metafases capturadas (3/20)                    [🗑 Limpiar todas]  │  │
│  │  [img1] [img2] [img3]                                               │  │
│  │                                                                      │  │
│  │           [💾 Guardar borrador] [✕ Cancelar] [🤖 Registrar y IA]   │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
```

## §4. Gherkin

### UC-R-001: Guardar borrador

```gherkin
Feature: Guardar borrador de registro
  Como Analista/Técnico
  Quiero guardar un registro incompleto
  Para continuar más tarde sin perder el trabajo

  Scenario: Guardar borrador con solo CHN
    Given estoy en la página de Registro de Muestras
    And ingresé CHN "CHN-2026-07-12-0001" y ningún otro dato
    When hago click en "Guardar borrador"
    Then POST /api/clinic/samples/register/ con is_draft=true
    And retorna 201 con {id, status: "DRAFT"}
    And veo el toast "Borrador guardado correctamente"

  Scenario: Guardar borrador sin CHN
    When hago click en "Guardar borrador" sin haber ingresado CHN
    Then retorna 400 con {code: "CHN_REQUIRED"}
    And el formulario muestra el error inline
```

### UC-R-002: Registrar definitivamente y analizar con IA

```gherkin
Feature: Registro definitivo con disparo de IA
  Scenario: Registro exitoso con 3 metafases (umbral real del HTML)
    Given completé CHN, nombre del paciente, y capturé 3 imágenes
    When hago click en "Registrar y analizar con IA"
    Then POST /api/clinic/samples/register/ con is_draft=false
    And retorna 201 con {id, status: "PENDING_AI", task_id}
    And se abre el modal de progreso con 3 pasos (Detección, Segmentación U-Net, Clasificación ISCN)
    And al completar, navega a "correccion de cariotipo.html?sample={id}"

  Scenario: Registro rechazado por menos de 3 imágenes
    Given completé CHN y nombre pero solo capturé 2 imágenes
    When hago click en "Registrar y analizar con IA"
    Then el formulario NO envía la petición (validación client-side, replica el HTML)
    And muestra "Se requieren al menos 3 metafases para el análisis. Actualmente tiene 2."

  Scenario: Registro rechazado por CHN o nombre faltante
    Given no completé CHN o nombre del paciente
    When hago click en "Registrar y analizar con IA"
    Then el formulario NO envía la petición
    And muestra "Complete los campos obligatorios: CHN y Nombre del paciente"

  Scenario: Registro con formato de CHN inválido
    Given ingresé CHN "12345" (no matchea CHN-YYYY-MM-DD-NNNN)
    When hago click en "Registrar y analizar con IA"
    Then retorna 400 con {code: "INVALID_CHN_FORMAT"}

  Scenario: Registro con CHN duplicado
    Given ya existe una muestra con chn_code "CHN-2026-07-12-0001"
    When intento registrar con el mismo CHN
    Then retorna 409 con {code: "CHN_DUPLICATE"}
    And ningún dato se persiste (transacción atómica revertida)

  Scenario: Pipeline IA no disponible al registrar (RN-07)
    Given el FastAPI clínico está caído
    When registro definitivamente con datos válidos
    Then el Sample SÍ se persiste con status PENDING_AI
    And el modal de progreso muestra DegradedBanner en vez de la animación
    And NO se pierde el registro (solo el disparo automático del pipeline falla)
```

### UC-R-003: Captura de imágenes

```gherkin
Feature: Captura de metafases por cámara y archivo
  Scenario: Conectar cámara y capturar
    Given hago click en "Conectar cámara"
    And el navegador otorga permiso de getUserMedia
    Then el botón "Capturar metafase" se habilita
    When hago click en "Capturar metafase"
    Then se agrega una imagen a la galería
    And el contador "X/20" se incrementa

  Scenario: Subir archivos
    When selecciono 3 archivos JPEG/PNG/TIFF desde "Subir imagen"
    Then las 3 imágenes se agregan a la galería
    And cada una tiene source="upload"

  Scenario: Eliminar imagen individual
    Given tengo 3 imágenes en la galería
    When hago click en el botón eliminar de la imagen 2
    Then quedan 2 imágenes en la galería

  Scenario: Limpiar todas
    Given tengo 5 imágenes en la galería
    When hago click en "Limpiar todas" y confirmo
    Then la galería queda vacía
    And el badge de calidad vuelve a "Sin evaluar"
```

### UC-R-004: Cancelar registro

```gherkin
Feature: Cancelar registro
  Scenario: Cancelar con confirmación
    Given tengo datos parciales en el formulario
    When hago click en "Cancelar" y confirmo el diálogo
    Then el formulario se limpia
    And la cámara se desconecta si estaba activa
    And navego de vuelta a /clinic/samples
```

## §5. Contratos JSON completos

### Request: `POST /api/clinic/samples/register/`

```json
{
  "patient": {
    "full_name": "ANON-999",
    "birth_date": "1998-03-15",
    "document_id": "12345678",
    "phone": "+591 71234567"
  },
  "sample": {
    "chn_code": "CHN-2026-07-12-0001",
    "sample_type": "sangre",
    "culture_method": "72h",
    "collection_date": "2026-07-12",
    "reception_date": "2026-07-12",
    "requesting_doctor": "Dr. Alejandro Rojas",
    "department": "Genética Clínica",
    "gender": "M"
  },
  "clinical_history": {
    "indication": "Estudio prenatal por edad materna avanzada.",
    "family_history": "Sin antecedentes familiares de importancia."
  },
  "analysis_requests": ["karyotype_high_res"],
  "images": [
    {"data_base64": "data:image/jpeg;base64,...", "source": "camera"},
    {"data_base64": "data:image/jpeg;base64,...", "source": "upload"},
    {"data_base64": "data:image/jpeg;base64,...", "source": "upload"}
  ],
  "is_draft": false
}
```

### Response 201 (éxito, no-draft)

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "chn_code": "CHN-2026-07-12-0001",
  "sample_code": "BM-20260712-042",
  "status": "PENDING_AI",
  "task_id": "abc123-def456",
  "image_count": 3,
  "created_at": "2026-07-12T14:30:00Z"
}
```

### Response 201 (éxito, draft)

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "chn_code": "CHN-2026-07-12-0001",
  "sample_code": "BM-20260712-042",
  "status": "DRAFT",
  "task_id": null,
  "image_count": 0,
  "created_at": "2026-07-12T14:30:00Z"
}
```

### Errores

| Status | Code | Cuándo |
|---|---|---|
| 400 | `CHN_REQUIRED` | Falta `chn_code` (aplica incluso en draft) |
| 400 | `INVALID_CHN_FORMAT` | `chn_code` no matchea `CHN-YYYY-MM-DD-NNNN` |
| 400 | `PATIENT_NAME_REQUIRED` | Falta `patient.full_name` (solo si `is_draft=false`) |
| 400 | `INSUFFICIENT_IMAGES` | `images.length < 3` (solo si `is_draft=false`) |
| 401 | `UNAUTHENTICATED` | JWT ausente/inválido |
| 403 | `PERMISSION_DENIED` | Rol no es analista/supervisor/admin |
| 409 | `CHN_DUPLICATE` | Ya existe muestra activa con ese `chn_code` |

## §6. Tabla de roles/permisos

Replica el control de acceso del HTML (`citogenetista`, `admin`, `supervisor` en `localStorage.biomed_user`, adaptado a roles Django `analista`/`supervisor`/`admin`):

| Endpoint | analista | supervisor | admin |
|---|:---:|:---:|:---:|
| `POST /samples/register/` (draft) | 201 | 201 | 201 |
| `POST /samples/register/` (definitivo) | 201 | 201 | 201 |

No hay distinción de permisos por rol dentro del registro (a diferencia del CRUD, donde `DELETE` es admin-only) — cualquier rol clínico puede registrar una muestra, igual que el HTML permite a `citogenetista`/`admin`/`supervisor`.

## §7. Casos de aceptación (CA-1 a CA-8)

| # | Caso | Pasos | Esperado |
|---|---|---|---|
| **CA-1** | Registro completo exitoso | Login → completar 5 secciones → capturar 3 imágenes → "Registrar y analizar con IA" | 201, modal de progreso con 3 pasos reales, navega a `correccion de cariotipo.html` |
| **CA-2** | Guardar borrador mínimo | Login → solo CHN → "Guardar borrador" | 201 status=DRAFT, toast de confirmación |
| **CA-3** | Bloqueo por <3 imágenes | Completar todo excepto capturar solo 2 imágenes → intentar registrar | Alert client-side, NO se envía request |
| **CA-4** | PII cifrada en DB | Registrar con datos de paciente → inspeccionar tabla `clinic_patient_vault` directamente en SQLite | Los campos PII NO son texto plano (son bytes Fernet) |
| **CA-5** | CHN duplicado | Registrar 2 veces con mismo CHN | Segunda vez 409, primera muestra intacta |
| **CA-6** | Modo degradado no bloquea registro | FastAPI caído, registrar definitivamente | 201 igual, `DegradedBanner` en el modal, muestra persistida |
| **CA-7** | Cancelar limpia estado | Completar parcialmente → Cancelar → confirmar | Formulario vacío, cámara desconectada, navega a lista |
| **CA-8** | Cobertura RN-09 | `pytest --cov-fail-under=90` backend, `npm run test:coverage` frontend | Ambos ≥90/88/90/90 |

## §8. Integración con pipeline y RN-07

Idéntico patrón que SPEC-008 §8: `SampleRegistrationService.register()` llama a `pipeline_client.trigger_processing(sample.id)` solo si `is_draft=false` y la transacción de persistencia tuvo éxito. Si el pipeline_client lanza `MLDegradedError` (circuit breaker abierto o timeout), el registro **no se revierte** — la muestra queda persistida en `PENDING_AI` y el frontend recibe `task_id: null` con un flag `degraded: true` en la respuesta, que activa el `DegradedBanner` en el modal en vez de la animación de progreso.

## §9. Métricas de cobertura RN-09

| Stack | Threshold | Comando |
|---|:---:|---|
| `backend-clinic/` (incluye `fields.py`, `services.py`, `views.py` nuevos) | ≥90% lines/branches/funcs/statements | `pytest --cov-fail-under=90` |
| `frontend-clinic/` (incluye 6 componentes + hooks nuevos) | ≥90% lines/funcs/statements, ≥88% branches | `npm run test:coverage` |

Archivos con mayor riesgo de cobertura baja (documentar si no se alcanza 90% exacto, mismo criterio que `feedback-rn09-v8-html-trap`):
- `useCamera.ts`: rama de error de `getUserMedia` rechazado por el usuario (permiso denegado) — testeable con mock que rechaza la promesa.
- `fields.py` (`EncryptedTextField`): rama de valor `None`/vacío antes de cifrar.

## §10. Trazabilidad

- **Sube a:** BRD §3.1 → `registrarmuestrafinal.html` (HTML Contract) → **ADR-0016** → esta SPEC-009.
- **Genera:** código en `backend-clinic/apps/samples/` (fields, models, serializers, services, views, permissions, migrations, tests) y `frontend-clinic/src/clinic/` (types, api, hooks, components, pages, tests).
- **Impacta:** `docs/PROMPT_MAPPING.md` (PM-REGISTRO-MUESTRA-001), `docs/DTI.md` (§21 registro ADR-0016, modelo de datos), `docs/design/DD-CRUD-MUESTRA-001.md` o DD nuevo.

## Notas finales

- El umbral "≥3 imágenes para enviar / ≥20 sugeridas en UI" se replica tal cual del HTML — no es un defecto a corregir (ver ADR-0016 D7 nota de UX).
- Si en el futuro se requiere compresión de imágenes o upload por streaming (en vez de base64 en el body), abrir un ADR nuevo — está fuera de alcance de esta spec.
