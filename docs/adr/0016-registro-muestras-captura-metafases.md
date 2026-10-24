---
id: ADR-0016
title: Registro de Muestras — PatientVault cifrada, SampleImage, estado DRAFT
date: 2026-07-12
status: accepted
supersedes: ninguno (extiende ADR-0015, no lo deroga)
related: [ADR-0003, ADR-0015, SPEC-008, SPEC-009, AGENTS.md RN-03/RN-04/RN-05/RN-06/RN-07]
fase: desarrollo
autor: Ing. Guillermo Mamani Chambi
---

# ADR 0016: Registro de Muestras — PatientVault cifrada, SampleImage, estado DRAFT

## Contexto

El bounded context Muestras (`backend-clinic`/`frontend-clinic`, ADR-0015) implementa hoy solo el **CRUD** de una muestra ya creada: 3 campos (`chn_code`, `patient_ref`, `image_path`), sin captura de imagen real ni datos de paciente. El botón "+ Nueva Muestra" de `SampleListPage` abre un modal simple (`SampleFormModal`) que no refleja el flujo real de trabajo del laboratorio.

Existe en la raíz del repo un contrato de interfaz aprobado, `registrarmuestrafinal.html` (1062 líneas), enlazado consistentemente desde `crudmuestra.html`, `supervisor.html`, `configuracion.html` e `informe.html` bajo el nombre "Registro". Este HTML define el flujo real de **Registro de Muestras**: formulario de datos del paciente, datos de la muestra, historial clínico, tipo de análisis solicitado, captura de imágenes de metafase (por cámara web o archivo) con galería y ajustes de imagen, y disparo del análisis por IA.

Al aplicar el flujo de verificación documental (Pasos 1-3, sesión 2026-07-12), se confirmó:
1. El HTML Contract **existe** — no se activa el gate de detención.
2. **No existe ningún ADR** que cubra este flujo. `ADR-0015`/`SPEC-008` (CRUD) excluyen explícitamente en su alcance la captura de imagen, los datos de paciente y el historial clínico.
3. El modelo `Sample` de Django (`backend-clinic/apps/samples/models.py`) no tiene campos para paciente, historial clínico, ni una colección de imágenes — solo `image_path` (string único).
4. El HTML captura PII real (nombre, fecha de nacimiento, documento, teléfono, motivo de consulta, antecedentes familiares) sin ningún mecanismo de aislamiento — viola RN-03 tal como estaba especificado si se persiste tal cual en la tabla `Sample`.
5. El modal de simulación de IA del HTML contiene el texto "Segmentación de instancias (Mask R-CNN)", que contradice AGENTS §11 (*"❌ Usar Mask R-CNN o ResNet50 — los modelos definitivos son U-Net + EfficientNet-B3"*).

Este ADR resuelve las 4 decisiones bloqueantes confirmadas por el arquitecto y fija el diseño de datos necesario para implementar el feature sin violar ninguna regla no-negociable existente.

## Decisión

### D1 — Corrección textual: Mask R-CNN → U-Net

El texto del paso 2 del modal de progreso IA se corrige de *"Segmentación de instancias (Mask R-CNN)"* a *"Segmentación de instancias (U-Net)"*. Es un fragmento cosmético de una animación (nunca invoca un modelo real), pero el HTML Contract no puede replicarse literalmente cuando colisiona con una regla constitucional (AGENTS §11). Se documenta aquí como la única desviación textual respecto al HTML original, y no se extiende a ningún otro campo, layout o flujo.

### D2 — `PatientVault`: bóveda cifrada separada de `Sample`

Se crea el modelo `PatientVault` en `backend-clinic/apps/samples/models.py`, tabla `clinic_patient_vault`, **vinculado por `chn_code` (clave de negocio), no por ForeignKey** a `Sample`. Esto es deliberado: evita que un `select_related`/serializer mal configurado exponga PII junto con el listado de muestras (RN-03: "aislamiento absoluto de PII").

Campos cifrados at-rest con Fernet (`cryptography.fernet.Fernet`, clave simétrica en env var `PATIENT_VAULT_KEY`, nunca en el repo, `required=True` en `env()` — el arranque falla explícitamente si falta):
- `full_name`, `birth_date` (ISO string cifrado), `document_id`, `phone`, `indication` (motivo de consulta), `family_history`.

Campo mecánico custom `EncryptedTextField` en `apps/samples/fields.py` (`get_prep_value`/`from_db_value` cifran/descifran de forma transparente al resto del código).

**`PatientVault` no tiene endpoint GET ni list.** Solo se escribe (`POST` como parte del registro compuesto) y se corrige (`PATCH` acotado, mismo endpoint de registro en modo edición). Nunca aparece en `SampleListItemSerializer` ni en ningún listado.

### D3 — `SampleImage`: galería de metafases (relación 1:N)

Se crea el modelo `SampleImage`:
```python
SampleImage:
  id: UUID (PK)
  sample: FK → Sample (CASCADE)
  image_path: CharField(512)
  order: int
  source: choices["camera", "upload"]
  captured_at: datetime (auto_now_add)
```

`Sample.image_path` (campo legacy singular, ya usado por ADR-0015/SPEC-008 para el CRUD) se mantiene sin cambios por compatibilidad hacia atrás. Las muestras registradas con el nuevo flujo usan la relación `sample.images` (1:N); `image_path` queda vacío o apunta a la primera imagen por conveniencia de listados que aún no migraron.

Las imágenes se reciben del navegador como base64 (mismo mecanismo que el HTML: `canvas.toDataURL()` para captura por cámara, `FileReader.readAsDataURL()` para upload). Se persisten con `image_path` derivado de `{chn_code}/{timestamp}_{order}.jpg` — **ningún nombre de archivo ni metadata incluye el nombre real del paciente** (RN-03).

### D4 — Estado `DRAFT` en el enum existente

Se agrega `DRAFT = 'DRAFT', 'Borrador'` como primer valor de `SampleStatus` (ya definido en `backend-clinic/apps/samples/models.py`, ADR-0015). Se descarta usar el enum de 7 estados de `AGENTS.md §7` (`queued/processing/ready/pending_validation/pending_signature/emitido/error`) porque pertenece al FastAPI clínico, que **no está commiteado en el repo** (mismo hallazgo que motivó ADR-0015). El enum Django ya en producción (`PENDING_AI/PROCESSING/READY/VALIDATED/REJECTED`) es la fuente de verdad operativa; se extiende, no se reemplaza.

Transición: `DRAFT → PENDING_AI` ocurre al registrar definitivamente (no al guardar borrador). El resto del ciclo de vida (`PENDING_AI → PROCESSING → READY → VALIDATED`) ya está implementado y no se toca.

### D5 — Campos nuevos en `Sample` (no PII)

Se agregan a la tabla `clinic_samples` (no a `PatientVault`, porque no son datos del paciente sino de la muestra/logística del laboratorio):

| Campo | Tipo | Nota |
|---|---|---|
| `sample_code` | `CharField(unique=True)` | Autogenerado `BM-YYYYMMDD-NNN`, análogo pero distinto de `chn_code` |
| `sample_type` | `choices`: sangre/medula/amniotico/vellosidades | |
| `culture_method` | `CharField(blank=True)` | |
| `collection_date` | `DateField(null=True)` | |
| `reception_date` | `DateField(null=True)` | |
| `requesting_doctor` | `CharField(blank=True)` | |
| `department` | `CharField(blank=True)` | |
| `analysis_requests` | `JSONField(default=list)` | Lista de los checkboxes de análisis marcados |

### D6 — `chn_code` sigue siendo input manual

A diferencia de `sample_code` (autogenerado), `chn_code` sigue siendo un campo editable por el usuario, tal como en el HTML. Se añade validación de formato server-side contra el patrón RN-03 (`CHN-YYYY-MM-DD-NNNN`); si no matchea, `400 INVALID_CHN_FORMAT`. Esta validación no existía en ningún lado antes de este ADR — es un endurecimiento, no un cambio de campo.

### D7 — Endpoint compuesto `POST /api/clinic/samples/register/`

Transacción atómica (`django.db.transaction.atomic`) que crea `Sample` + `PatientVault` + N `SampleImage` en un solo request.

```json
{
  "patient": {"full_name": "...", "birth_date": "...", "document_id": "...", "phone": "..."},
  "sample": {"chn_code": "...", "sample_type": "...", "culture_method": "...", "collection_date": "...", "reception_date": "...", "requesting_doctor": "...", "department": "..."},
  "clinical_history": {"indication": "...", "family_history": "..."},
  "analysis_requests": ["karyotype_high_res", "mosaicism", ...],
  "images": [{"data_base64": "...", "source": "camera|upload"}, ...],
  "is_draft": true|false
}
```

Regla de validación (replica exacta del gate del HTML, `submitBtn` handler):
- `is_draft=true`: validación laxa, solo `chn_code` requerido. `status = DRAFT`.
- `is_draft=false`: exige `chn_code` + `patient.full_name` + `images.length >= 3` (el HTML usa el umbral real de 3, no el sugerido de 20 — ver nota de UX abajo). `status = PENDING_AI`, y al final de la transacción se dispara `pipeline_client.trigger_processing()` (RN-07, circuit breaker ya implementado por ADR-0015).

**Nota de UX preservada intencionalmente:** el HTML muestra "mínimo 20 metafases" en el badge de calidad y el alert informativo, pero el gate de envío real solo exige 3. Esto se replica exactamente — no es una inconsistencia a resolver, es el comportamiento documentado del contrato de UI.

### D8 — Modal de progreso conectado a datos reales

El HTML original anima el modal de IA con `setInterval` de 4 pasos fijos (nunca llama a un backend). Se reemplaza el mecanismo interno por el flujo de polling ya existente (`useStatusPolling`, `pipeline_client.py` con circuit breaker) manteniendo la apariencia visual idéntica (ícono, barra de progreso, 3 pasos de texto — con el paso 2 corregido según D1). Esto no es "mejorar el diseño": es la única forma de que el modal refleje un pipeline real, dado que el HTML nunca tuvo backend.

## Justificación

- **RN-03 exige aislamiento de PII**; hasta este ADR, ningún flujo del repo capturaba PII real de paciente — el CRUD (`ADR-0015`) usa `patient_ref` ya pseudoanonimizado. El Registro sí captura datos reales, por lo que la bóveda cifrada es la primera vez que se necesita, y se diseña siguiendo la decisión de ADR-0003 ("mapping vive en bóveda local cifrada, no en la tabla pública").
- **`SampleImage` como relación 1:N** es la única forma de modelar una galería sin violar el principio de una responsabilidad por tabla; el campo legacy `image_path` singular de ADR-0015 no alcanza para el caso de uso real de múltiples metafases.
- **`DRAFT` en el enum Django existente** (no un campo booleano separado, no el enum nunca implementado de AGENTS.md) es la opción de menor fricción: reutiliza el `status` que ya gobierna toda la UI de listado/filtros/badges, y evita mantener dos fuentes de verdad de "en qué etapa está la muestra".

## Consecuencias

### Positivas
- Cierra el gap real detectado en el flujo de verificación (Paso 2): ahora existe trazabilidad ADR→SPEC→código para el Registro.
- El aislamiento de PII vía `PatientVault` es la primera implementación concreta de lo que ADR-0003 exige desde mayo 2026 — antes era una promesa sin código.
- La galería `SampleImage` habilita el caso de uso real de citogenética (20-46 metafases por muestra), no solo el CRUD de una imagen representativa.

### Negativas
- Aumenta la superficie del bounded context Muestras: 2 modelos nuevos, 1 campo cifrado custom, 1 endpoint compuesto con lógica transaccional más compleja que el CRUD simple de ADR-0015.
- Gestión de la clave `PATIENT_VAULT_KEY` es responsabilidad operacional nueva (rotación, backup) — sin eso, los datos de pacientes ya registrados quedan irrecuperables (ver ADR-0003 "Cons": dependencia del vault para recuperación).
- Imágenes base64 en el body del POST no están optimizadas (sin compresión, sin streaming); aceptable para esta fase, documentado como límite conocido.

### Neutras
- El campo `Sample.image_path` legacy no se elimina; convive con `SampleImage` hasta que se decida deprecar el CRUD simple (fuera de alcance de este ADR).
- El enum `SampleStatus` de AGENTS.md §7 (7 valores) sigue sin implementarse; esta discrepancia documental persiste y no se resuelve aquí (fuera de alcance — pertenece a la gobernanza de AGENTS.md/DTI, no a este feature).

## Tensión con reglas del proyecto y cómo se resuelve

| Regla | Tensión | Resolución |
|---|---|---|
| **RN-03** (PII nunca sale del entorno local / CHN Anonymizer) | El HTML captura PII real | `PatientVault` cifrada, sin FK directa a `Sample`, sin endpoint de lectura pública. Nombres de archivo de imágenes derivados de `chn_code`, nunca del nombre real. |
| **RN-04** (`iscn_nomenclature` read-only) | Ninguna — el Registro no toca ese campo | El endpoint `register/` no expone ni escribe `iscn_nomenclature`; sigue siendo exclusivo del FastAPI clínico (fuera de alcance). |
| **RN-05** (tabla `edits` append-only) | Ninguna — el Registro no toca esa tabla | `backend-clinic/apps/samples/` no tiene tabla `edits` (confirmado en ADR-0015 y se mantiene). |
| **RN-06** (segregación analista/supervisor) | El endpoint de registro asigna `analyst` | `SampleRegisterView` usa `request.user` como `analyst` (igual patrón que `SampleListCreateView` de ADR-0015); `CanRegisterSample` exige rol analista/supervisor/admin, igual al control de acceso `citogenetista/admin/supervisor` del HTML. |
| **RN-07** (modo degradado si IA falla) | El registro no-draft dispara el pipeline | Se reutiliza `pipeline_client.py` (circuit breaker ya implementado, ADR-0015 #6); si el FastAPI está caído, el registro persiste igual (status queda en `PENDING_AI`) y el frontend muestra `DegradedBanner` en vez de bloquear el guardado. |
| **AGENTS §11** (prohibición Mask R-CNN) | Texto del HTML original | D1: corrección textual a U-Net, única desviación del HTML Contract, documentada explícitamente. |
| **AGENTS §11** (no pushear a main) | — | Rama `feature/clinic-django-stack`, PR a `release/2.0.0`, sin cambios respecto a ADR-0015. |

## Plan de migración

No aplica migración de datos existentes: el Registro es un flujo **nuevo** (crea muestras desde cero), no reemplaza el CRUD de ADR-0015 que sigue operando sobre muestras ya existentes (editar `patient_ref`, eliminar, listar). Las 8 muestras seed de ADR-0015/SPEC-008 no tienen `PatientVault` asociada (se crearon antes de este ADR) — esto es aceptable porque `PatientVault` es opcional a nivel de negocio (una muestra puede no tener paciente identificado, ej. datos legacy).

## Alternativas evaluadas y rechazadas

**A1. Guardar PII directamente en `Sample.metadata` (JSONField ya existente).**
Rechazada: `metadata` no está cifrado, y cualquier endpoint que devuelva `Sample` (incluidos los de ADR-0015 ya en producción) filtraría PII en texto plano. Viola RN-03 directamente.

**A2. `PatientVault` con ForeignKey a `Sample` en vez de vínculo por `chn_code`.**
Rechazada: un ForeignKey habilita `select_related`/`prefetch_related` accidental que expondría PII en cualquier query futura sobre `Sample` sin que el desarrollador lo note. El vínculo débil por `chn_code` obliga a una consulta explícita y separada.

**A3. Un solo campo `Sample.image_path` con lista de paths separados por coma.**
Rechazada: no permite metadata por imagen (`order`, `source`, `captured_at`), rompe normalización, dificulta borrado individual desde la galería (funcionalidad requerida por el HTML).

**A4. Reescribir el modal de IA sin conexión a datos reales (mantener `setInterval` fijo).**
Rechazada: sería simular una funcionalidad sin construirla, contradice el principio de "no crear código sin evidencia" del flujo Antirracionalización.

## Trazabilidad

- **Sube a:** BRD §3.1 (Cariotipado clínico) → FSD-UC-001 (Ingesta simple, precedente parcial) → `registrarmuestrafinal.html` (HTML Contract) → **este ADR-0016**.
- **Genera:** `docs/specs/SPEC-009-registro-muestra.md`, actualización de `docs/design/DD-CRUD-MUESTRA-001.md` (o DD nuevo, decisión en Paso 5/T3), código en `backend-clinic/apps/samples/` y `frontend-clinic/src/clinic/`.
- **Impacta:**
  - `docs/PROMPT_MAPPING.md` (nueva entrada PM-REGISTRO-MUESTRA-001)
  - `docs/DTI.md` (registro de este ADR en §21, modelo de datos actualizado)
  - `AGENTS.md §5` (tabla de ADRs, agregar 0016)

## Notas

- Este ADR **no deroga** ADR-0015; el CRUD simple sigue operando para muestras ya creadas (editar `patient_ref` genérico, listar, soft-delete).
- Este ADR **no toca** el pipeline FastAPI de inferencia ni `correccion de cariotipo.html` (el flujo de Registro navega ahí al terminar, sin modificarlo).
- Si en el futuro se decide deprecar el CRUD simple en favor exclusivo del Registro completo, eso requiere un ADR nuevo — no se decide aquí.
- Rama de trabajo: `feature/clinic-django-stack` (continuación). NO pushear a `main`. PR a `release/2.0.0`.
