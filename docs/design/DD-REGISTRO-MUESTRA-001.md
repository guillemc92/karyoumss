---
id: DD-REGISTRO-MUESTRA-001
titulo: "Registro de Muestras — formulario paciente + captura de metafases"
producto: "BIOMED UMSS — Intelligent Karyotyping Platform"
grupo: "G04"
fsd_uc:
  - "FSD-UC-001"                # ingesta simple, precedente parcial
  - "FSD-UC-REGISTRO-MUESTRA-001"  # nuevo, a crear formalmente en FSD_vFinal.md
prd_refs:
  - "PRD-US-001"
adrs:
  - "ADR-0003"  # CHN Anonymization at the Edge
  - "ADR-0015"  # Derogación parcial ADR-0013 — stack Django/React para Muestras
  - "ADR-0016"  # PatientVault cifrada + SampleImage + DRAFT (este feature)
prompts:
  - "PM-REGISTRO-MUESTRA-001"   # a crear en PROMPT_MAPPING.md, Paso 16/T16
specs:
  - "SPEC-009-registro-muestra.md"
ui_contract: "registrarmuestrafinal.html"  # HTML aprobado, raíz del repo
release: "release/2.0.0"
status: proposed
fecha: "2026-07-12"
autores:
  - "Ing. Guillermo Mamani Chambi"
---

# Design Doc `DD-REGISTRO-MUESTRA-001` — Registro de Muestras

## 0. Relación con `DD-CRUD-MUESTRA-001`

Este DD es **complementario**, no sustituye a `DD-CRUD-MUESTRA-001.md` (superseded por ADR-0015). El CRUD opera sobre una muestra **ya existente** (editar `patient_ref`, listar, soft-delete). El Registro es el flujo de **creación** desde cero, con datos de paciente reales, historial clínico y captura de imágenes — un dominio de datos más amplio que requirió su propio ADR (0016) porque introduce PII real por primera vez en el bounded context Django (el CRUD usa `patient_ref` ya pseudoanonimizado).

Ambos comparten el mismo bounded context (`backend-clinic/apps/samples/`, `frontend-clinic/src/clinic/`) y el mismo modelo `Sample` (extendido por ADR-0016, no reemplazado).

## 1. Trazabilidad SDD

```
BRD §3.1 (Cariotipado clínico)
  → registrarmuestrafinal.html (HTML Contract, UI aprobada)
    → ADR-0016 (PatientVault + SampleImage + DRAFT)
      → SPEC-009-registro-muestra.md (Gherkin + contratos)
        → este DD (arquitectura de componentes)
          → código (backend-clinic/, frontend-clinic/)
            → tests (≥90% RN-09)
```

## 2. Arquitectura de datos (resumen; detalle completo en ADR-0016)

```
┌─────────────────┐         ┌──────────────────────┐         ┌───────────────┐
│  PatientVault    │         │  Sample (extendido)   │         │  SampleImage   │
│  ────────────────│         │  ──────────────────── │         │  ────────────  │
│  chn_code (link) │◄────────┤  chn_code (unique)    ├────────►│  sample (FK)   │
│  full_name (enc) │  (débil,│  sample_code (unique) │  (FK,   │  image_path    │
│  birth_date (enc)│  NO FK) │  status (+ DRAFT)      │  CASCADE)│  order         │
│  document_id(enc)│         │  sample_type            │         │  source        │
│  phone (enc)     │         │  culture_method         │         │  captured_at   │
│  indication (enc)│         │  collection_date        │         └───────────────┘
│  family_hist(enc)│         │  reception_date         │
└─────────────────┘         │  requesting_doctor      │
                              │  department             │
                              │  analysis_requests[]    │
                              │  analyst (FK, existente)│
                              │  metadata (JSON, gender)│
                              └──────────────────────┘
```

Cifrado: `PatientVault` usa `EncryptedTextField` (Fernet) en los 6 campos marcados `(enc)`. Nunca expuesto en serializers de lectura/listado.

## 3. Componentes backend (`backend-clinic/apps/samples/`)

| Componente | Responsabilidad |
|---|---|
| `fields.py::EncryptedTextField` | Cifra/descifra transparente vía Fernet en `get_prep_value`/`from_db_value` |
| `models.py::PatientVault` | Almacena PII cifrada, vinculada por `chn_code` |
| `models.py::SampleImage` | Galería 1:N de metafases por muestra |
| `models.py::Sample` (extendido) | +8 campos no-PII (tabla D5 de ADR-0016), +`DRAFT` en `SampleStatus` |
| `serializers.py::PatientVaultSerializer` | Write-only, valida campos PII, nunca en respuestas GET |
| `serializers.py::SampleImageSerializer` | Valida `data_base64`/`source`, no persiste directo (delegado a service) |
| `serializers.py::SampleRegisterSerializer` | Serializer compuesto: agrupa `patient`+`sample`+`clinical_history`+`analysis_requests`+`images`+`is_draft`, aplica regla de validación condicional draft/no-draft |
| `services.py::SampleRegistrationService` | Orquesta la transacción atómica: genera `sample_code`, valida formato CHN, persiste los 3 modelos, dispara `pipeline_client` si corresponde |
| `views.py::SampleRegisterView` | `POST /register/`, usa el serializer + service, traduce excepciones a códigos HTTP |
| `permissions.py::CanRegisterSample` | Analista/supervisor/admin (igual control de acceso que el HTML) |

## 4. Componentes frontend (`frontend-clinic/src/clinic/`)

| Componente | Responsabilidad |
|---|---|
| `types/registration.ts` | Tipos `PatientData`, `SampleRegistrationData`, `ClinicalHistory`, `AnalysisRequest`, `CapturedImage` |
| `api/registrationClient.ts` | `registerSample(data, isDraft)` → `POST /register/` |
| `hooks/useSampleRegistration.ts` | TanStack Query mutation |
| `hooks/useCamera.ts` | Encapsula `getUserMedia`/`canvas.toDataURL`/conectar-desconectar |
| `components/PatientInfoSection.tsx` | Sección 1 del HTML (6 campos) |
| `components/SampleInfoSection.tsx` | Sección 2 (7 campos, código autogenerado readonly) |
| `components/ClinicalHistorySection.tsx` | Sección 3 (2 textareas) |
| `components/AnalysisRequestSection.tsx` | Sección 4 (6 checkboxes) |
| `components/MetaphaseCaptureSection.tsx` | Sección 5 (cámara + ajustes + galería) |
| `components/RegisterProcessingModal.tsx` | Modal IA con polling real (no `setInterval` fijo) |
| `pages/SampleRegisterPage.tsx` | Orquesta las 5 secciones + 3 acciones |

## 5. Riesgos (ver también ADR-0016 §Consecuencias)

| Riesgo | Mitigación |
|---|---|
| Muestras seed de SPEC-008 (8 muestras) sin `PatientVault` asociada | Aceptable — `PatientVault` es opcional a nivel de negocio; el CRUD simple sigue funcionando sin ella |
| Clave `PATIENT_VAULT_KEY` perdida = PII irrecuperable | Documentado explícitamente como trade-off aceptado en ADR-0003/ADR-0016; fuera de alcance definir procedimiento de backup en este DD |

## 6. Plan de implementación

Ver plan file `C:\Users\Qubits\.claude\plans\sorted-seeking-thompson.md` — tabla de tareas T1-T17. Este DD corresponde a T3; T4-T14 son el código; T15 verificación E2E; T16-T17 trazabilidad y commit.

## 7. Trazabilidad

- **Sube a:** BRD §3.1 → `registrarmuestrafinal.html` → ADR-0016 → SPEC-009 → este DD.
- **Baja a:** código en `backend-clinic/apps/samples/{fields,models,serializers,services,views,permissions}.py` + `frontend-clinic/src/clinic/{types,api,hooks,components,pages}/*`.
- **Impacta:** `docs/PROMPT_MAPPING.md`, `docs/DTI.md`, `AGENTS.md §5`.

## Notas

- Este DD **no reemplaza** `DD-CRUD-MUESTRA-001.md`; ambos coexisten como documentos de diseño de features distintas dentro del mismo bounded context.
- Decisiones de esquema de datos están en ADR-0016, no se repiten aquí en detalle — este documento es la vista de componentes/arquitectura, el ADR es la vista de decisión.
