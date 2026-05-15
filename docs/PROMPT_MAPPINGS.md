# PROMPT MAPPINGS v2.0
## BIOMED UMSS — Trazabilidad Requerimiento → Prompt → Código

| Campo | Detalle |
|:---|:---|
| **Producto** | BIOMED UMSS – Intelligent Karyotyping Platform |
| **Versión** | 2.0 (10 contratos completos — 6 elementos + Invariantes + Failure Modes) |
| **Fecha** | Mayo 2026 |
| **Autores** | Ing. Guillermo Mamani Chambi · Ing. Josue David Villarroel Rojas |
| **Trazabilidad** | FSD_v2.md → PRD_v2.md → BRD_v3.5 → PROMPT_MAPPINGS.md |

> **Propósito:** En el AI SDLC, el PROMPT_MAPPINGS es la fuente de verdad del ciclo agéntico. Cada entrada mapea: **Input** (requerimiento) → **Prompt** (6 elementos) → **Output** (código) + **Invariantes** (propiedades verificables) + **Failure Modes** (comportamiento ante fallo).

**Convención de IDs:** `PM-[MÓDULO]-[NNN]`

---

## PM-SETUP-01 — Scaffolding del Proyecto Docker

| Campo | Valor |
|:---|:---|
| **ID** | PM-SETUP-01 |
| **Título** | Estructura inicial del proyecto con Docker Compose |
| **Modelo** | Claude Sonnet |
| **Input** | FSD_v2.md §2.3 Estructura de proyecto · FSD_v2.md §2.4 T-001 |

### Prompt

```
Role: Arquitecto de software senior especializado en FastAPI + React con experiencia
en infraestructura Docker para aplicaciones clínicas GPU.

Task: Genera el scaffolding completo del proyecto BIOMED UMSS:
1. docker-compose.yml con servicios: fastapi, react, postgresql, redis, celery_worker, minio
2. Estructura de carpetas backend/ y frontend/ según FSD §2.3
3. Dockerfile para cada servicio con configuración GPU para celery_worker
4. Variables de entorno (.env.example) — SIN valores reales

Context:
- Stack: FastAPI Python 3.11+, React 18 + Vite, PostgreSQL 15, Redis 7, Celery 5, MinIO
- celery_worker: NVIDIA runtime obligatorio (nvidia/cuda base image)
- PII nunca sale del nodo institucional — validar con AGENTS.md §10
- Restricción: funciona con `docker compose up` sin configuración adicional

Reasoning:
1. Cada servicio tiene healthcheck configurado
2. celery_worker depende de redis (healthy) y fastapi (healthy)
3. PostgreSQL tiene volumen persistente nombrado
4. MinIO tiene bucket inicial creado en entrypoint
5. No hardcodear secrets — solo referencias a variables de entorno

Stop Condition: `docker compose up --build` completa sin errores. Todos los healthchecks pasan.

Output: Bloques de código con path explícito — docker-compose.yml, Dockerfiles, .env.example
```

### Output (Artefactos Generados)
- `docker-compose.yml`
- `backend/Dockerfile`
- `frontend/Dockerfile`
- `.env.example`

### Invariantes
- `docker compose up --build` ejecuta sin errores
- `celery_worker` tiene `deploy.resources.reservations.devices` configurado para GPU
- Ningún valor real de credenciales en archivos del repositorio
- Todos los servicios tienen `healthcheck` definido

### Failure Modes
| Fallo | Comportamiento esperado |
|:---|:---|
| GPU no disponible en el host | docker-compose levanta sin GPU; celery_worker activa modo degradado automáticamente |
| Puerto 5432 ocupado | Error explícito en startup con instrucción de cambiar `PG_PORT` en `.env` |
| MinIO bucket ya existe | Idempotente — el entrypoint ignora el error `BucketAlreadyExists` |
| Imagen base no descargable | El build falla con mensaje claro; no genera imagen parcial |

---

## PM-UC01-API — Endpoint POST /samples con CHN Anonymizer

| Campo | Valor |
|:---|:---|
| **ID** | PM-UC01-API |
| **Título** | POST /samples — Ingesta de muestra con anonimización CHN |
| **Modelo** | Claude Sonnet |
| **Input** | FSD_v2.md UC-001 pasos 1–8 · PRD_v2.md US-001, US-002 · BRD_v3.5 BR-01 |

### Prompt

```
Role: Desarrollador backend senior en FastAPI con experiencia en sistemas de salud
que cumplen normativas de privacidad clínica (Ley 164 Bolivia, 21 CFR Part 11).

Task: Implementa el endpoint POST /api/v1/samples/image que:
1. Recibe imagen multipart (TIFF/PNG/JPEG, <50MB) — SIN datos del paciente en el body
2. Valida formato, tamaño e integridad (checksum MD5)
3. Genera código CHN único: CHN-YYYY-MM-DD-NNNN con verificación de unicidad en DB
4. Elimina metadatos EXIF/DICOM con PII de la imagen
5. Sube imagen anonimizada a S3 (path: {chn_code}/{timestamp}.tiff)
6. Crea registro en tabla `samples` (status=queued)
7. Encola tarea en Redis: {sample_id, s3_path, chn_code}
8. Retorna 202 Accepted con {sample_id, chn_code, task_id}

Context:
- Stack: FastAPI + SQLAlchemy 2.0 + Pydantic v2 + PostgreSQL 15 + MinIO
- CHN formato: CHN-{YYYY}-{MM}-{DD}-{NNNN_secuencial_con_retry}
- CRÍTICO: PII nunca sale del nodo institucional (AGENTS.md Regla 1)
- El endpoint requiere JWT con rol "analista"
- quality_flag: si overlap >30% agregar HIGH_OVERLAP al response

Reasoning:
1. Validar JWT y extraer analyst_id — NUNCA del body
2. Verificar formato y tamaño antes de cualquier operación
3. Generar CHN → verificar unicidad → retry automático con NNNN+1 si colisión
4. Eliminar PII con piexif/exiftool ANTES de subir a S3
5. Operaciones S3 y PostgreSQL en transacción — rollback si falla S3

Stop Condition: Endpoint pasa tests: creación exitosa, unicidad CHN, auth requerida,
rechazo de PII en body, rollback ante fallo S3.

Output: JSON Schema + código Python en bloques con paths explícitos
```

### Output (Artefactos Generados)
- `backend/app/api/samples.py`
- `backend/app/services/chn_service.py`
- `backend/app/schemas/sample.py`
- `backend/tests/test_samples.py`

### Invariantes
- CHN nunca contiene datos del paciente
- Unicidad garantizada con retry automático (máximo 3 intentos)
- Endpoint retorna 401 sin JWT válido
- 422 si body contiene campos `patient_name`, `patient_id`, `dob`
- S3 path usa solo `{chn_code}` — nunca nombre o ID del paciente

### Failure Modes
| Fallo | Comportamiento esperado |
|:---|:---|
| Archivo corrupto o no legible | 422 Unprocessable Entity con `"detail": "El archivo está dañado o incompleto"` |
| Tamaño >50MB | 413 Request Entity Too Large con límite explícito en el mensaje |
| CHN colisión tras 3 reintentos | 500 con alert a logs (crítico — indica problema de secuencia) |
| S3 no disponible | Rollback en PostgreSQL → 503 Service Unavailable; no se crea caso huérfano |
| Fallo de eliminación de EXIF | 422 — la imagen NO se procesa si PII no pudo ser eliminado |

---

## PM-UC01-SEG — Celery Task: Segmentación U-Net

| Campo | Valor |
|:---|:---|
| **ID** | PM-UC01-SEG |
| **Título** | Celery Task — Segmentación cromosómica con U-Net |
| **Modelo** | Claude Opus (lógica compleja de visión artificial) |
| **Input** | FSD_v2.md UC-002 pasos 1–7 · FSD_v2.md §8 PM-FSD-001 · BRD_v3.5 NFR-04 |

### Prompt

```
Role: Ingeniero ML especializado en visión computacional médica con experiencia en
U-Net para segmentación semántica de imágenes citogenéticas de alta resolución.

Task: Implementa la Celery task `segment_metaphase` que:
1. Descarga imagen de S3 usando CHN como identificador (NUNCA PII)
2. Aplica CLAHE: clipLimit=3.0, tileGridSize=(8,8)
3. Si imagen >4000px: tiling 1024×1024 con overlap 64px
4. Ejecuta U-Net via TorchServe: POST /predictions/unet_karyotype
5. Post-procesa con NMS (IoU threshold 0.3) para eliminar duplicados en bordes
6. Retorna lista: {chromosome_id, polygon_coords, bounding_box, quality_flags}
7. Si overlap_index >30%: agrega quality_flag HIGH_OVERLAP
8. Publica progreso en Redis: preprocessing → segmenting → assembling

Context:
- Modelo: U-Net con backbone ResNet34 (NO Mask R-CNN — obsoleto)
- TorchServe endpoint: POST http://torchserve:8080/predictions/unet_karyotype
- Imágenes: TIFF/PNG hasta 50MB, resolución hasta 8000×6000px
- IoU segmentación target: >0.90 (si <0.90 en >10% → quality_flag LOW_IOU)
- Timeout TorchServe: 10s antes de reintento; máximo 3 reintentos

Reasoning:
1. Verificar descarga de S3 exitosa antes de iniciar pipeline
2. CLAHE aplicado a cada tile individualmente (no a la imagen completa)
3. U-Net por tile → NMS cross-tile para eliminar fragmentos duplicados
4. Validar conteo: si <40 o >55 cromosomas → quality_flag ABNORMAL_COUNT
5. Si TorchServe no responde en 10s × 3: activar modo degradado (UC-007)

Stop Condition: Task completa cuando: (1) todos los tiles procesados, (2) NMS aplicado,
(3) polígonos persistidos, (4) progreso publicado en Redis.

Output: Código Python con paths explícitos — segmentation.py, tiling_service.py
```

### Output (Artefactos Generados)
- `backend/app/tasks/segmentation.py`
- `backend/app/services/image_preprocessor.py`
- `backend/app/services/tiling_service.py`

### Invariantes
- Task completa en <12s para imagen estándar (2048×1536px)
- Tiling no pierde cromosomas en bordes (verificable con test de imagen sintética de borde)
- Progreso publicado en Redis key `sample:{sample_id}:progress`
- S3 path referenciado siempre por CHN — nunca por PII
- quality_flags es lista vacía `[]` si no hay anomalías de calidad

### Failure Modes
| Fallo | Comportamiento esperado |
|:---|:---|
| TorchServe timeout × 3 | Task marca `samples.status = 'manual_mode'` → activa UC-007 (modo degradado) |
| VRAM GPU insuficiente | Automáticamente reduce tile size a 512×512 y reintenta |
| Imagen ilegible tras descarga | Task falla con `CORRUPTED_DOWNLOAD`; S3 re-upload se programa |
| Conteo anormal (<40 o >55) | Continúa el pipeline pero agrega `quality_flag: ABNORMAL_COUNT` — no bloquea |
| NMS elimina todos los objetos | Fallo crítico: marca muestra como `error`, alerta a administrador |

---

## PM-UC01-CLS — Celery Task: Clasificación EfficientNet-B3

| Campo | Valor |
|:---|:---|
| **ID** | PM-UC01-CLS |
| **Título** | Celery Task — Clasificación cromosómica con EfficientNet-B3 + Softmax |
| **Modelo** | Claude Sonnet |
| **Input** | FSD_v2.md UC-002 pasos 7–10 · FSD_v2.md §8 PM-FSD-002 · BRD_v3.5 BR-02, BR-03 |

### Prompt

```
Role: Ingeniero ML especializado en clasificación de imágenes médicas con EfficientNet
y diseño de pipelines de inferencia confiables para entornos clínicos regulados.

Task: Implementa `classify_chromosomes` que:
1. Recibe lista de cromosomas segmentados (crops 224×224px)
2. Ejecuta EfficientNet-B3 via TorchServe en batch de 16
3. Obtiene confidence_score = max(softmax_vector) — SIN redondear
4. Retorna: {chromosome_id, predicted_pair, confidence_score, all_scores, requires_review}
5. requires_review = True si confidence_score < 0.85

Context:
- Modelo: EfficientNet-B3 (NO ResNet50 — obsoleto) con 24 clases de salida
- TorchServe endpoint: POST http://torchserve:8080/predictions/efficientnet_b3_karyotype
- Input por crop: imagen 224×224px en base64
- CRÍTICO: confidence_score se persiste como FLOAT — NUNCA usar round() antes del INSERT
- all_scores: vector completo de 24 probabilidades (para análisis de consistencia global)

Reasoning:
1. Batch de máximo 16 crops por request (optimiza throughput GPU)
2. Verificar suma de Softmax ≈ 1.0 ± 0.001 (si no → error del modelo)
3. Análisis de consistencia: si dos cromosomas tienen mismo par en muestra normal → LOW_CONSISTENCY flag
4. requires_review calculado en backend — nunca en frontend
5. Persistir en tabla `chromosomes` con score completo sin modificar

Stop Condition: Todos los cromosomas del batch clasificados. Scores persistidos sin redondeo.
requires_review correctamente asignado según umbral 0.85.

Output: Código Python + schema JSON con paths explícitos
```

### Output (Artefactos Generados)
- `backend/app/tasks/classification.py`
- `backend/app/services/softmax_analyzer.py`

### Invariantes
- `confidence_score` persistido como FLOAT sin redondear (verificable: `assert score == db_score`)
- `requires_review = True` exactamente cuando `confidence_score < 0.85` (no ≤)
- Batch processing: máximo 16 cromosomas por request a TorchServe
- `all_scores` contiene exactamente 24 valores sumando ≈ 1.0

### Failure Modes
| Fallo | Comportamiento esperado |
|:---|:---|
| TorchServe no disponible | Task activa modo degradado UC-007; muestra pasa a `manual_mode` |
| Softmax no suma ≈ 1.0 | Cromosoma marcado con `quality_flag: SOFTMAX_ERROR`; requires_review = True forzado |
| Crop corrupto o tamaño incorrecto | Cromosoma individual marcado como `UNCLASSIFIABLE`; resto del batch continúa |
| Consistencia baja (mismo par duplicado) | Agrega `quality_flag: LOW_CONSISTENCY` a la muestra — no bloquea |

---

## PM-UC02-SEM — Componente React: Semaforización Visual

| Campo | Valor |
|:---|:---|
| **ID** | PM-UC02-SEM |
| **Título** | ChromosomeCanvas — Semaforización de confianza en mesa de edición |
| **Modelo** | Claude Sonnet |
| **Input** | PRD_v2.md US-004, US-006, US-016 · FSD_v2.md UC-002, UC-003 · BRD_v3.5 BR-02 |

### Prompt

```
Role: Desarrollador frontend senior en React + Konva.js para canvas interactivos,
especializado en UX para aplicaciones médicas donde la claridad visual previene errores clínicos.

Task: Implementa ChromosomeCanvas con:
1. Renderizado de cromosomas en Konva.js Stage con borde dinámico por confidence_score
2. Verde (#00e676, 1px) para score ≥ 0.85; Naranja (#ff6d00, 3px) para score < 0.85
3. Gradiente continuo: 0.85=verde, 0.70=amarillo-naranja, <0.60=rojo (WCAG AA)
4. Al clic en naranja: selecciona + resalta en ReviewPanel lateral
5. Botón "Pasar a Supervisor" DESHABILITADO si remaining_reviews > 0
6. Contador visual: "X cromosomas pendientes de revisión"

Context:
- Stack: React 18 + Konva.js 9 + Zustand
- Datos desde: GET /api/v1/samples/{id}/chromosomes
- CRÍTICO: el estado de validación vive en Zustand (no en estado local del componente)
- Prototipo HTML de referencia: correccion de cariotipo.html del Módulo 3
- Accesibilidad: borde naranja 3px mínimo (visible sin distinción de colores, WCAG AA)

Reasoning:
1. Zustand store maneja: chromosomes[], pendingCount, canPassToSupervisor
2. ChromosomeCanvas suscrito al store — re-renderiza solo en cambios de score/validated
3. El botón suscrito a pendingCount — disabled cuando pendingCount > 0
4. Gradiente implementado con interpolación lineal entre colores clave
5. Performance: virtualizar cromosomas off-screen con Konva.js clip

Stop Condition: (1) Semáforo muestra verde/naranja correctamente, (2) botón bloqueado
con cromosomas pendientes, (3) gradiente visible, (4) accesibilidad WCAG AA.

Output: TypeScript + Konva.js con paths: ChromosomeCanvas.tsx, chromosomeStore.ts, ReviewPanel.tsx
```

### Output (Artefactos Generados)
- `frontend/src/components/EditorCanvas/ChromosomeCanvas.tsx`
- `frontend/src/store/chromosomeStore.ts`
- `frontend/src/components/EditorCanvas/ReviewPanel.tsx`

### Invariantes
- Botón "Pasar a Supervisor" deshabilitado mientras `pendingCount > 0`
- Gradiente de color visible para scores intermedios (no binario)
- Estado de validación persiste en Zustand al navegar entre rutas
- Borde naranja mínimo 3px (verificable con Playwright screenshot)

### Failure Modes
| Fallo | Comportamiento esperado |
|:---|:---|
| GET /chromosomes retorna error | Skeleton loader visible; botón deshabilitado; toast error con retry automático |
| Konva.js no puede renderizar canvas | Fallback a lista HTML pura con íconos de semáforo (sin canvas) |
| Zustand store corrupto (hydration error) | Store se reinicializa desde el servidor; usuario no pierde trabajo validado ya confirmado |
| confidence_score undefined | Cromosoma renderizado como naranja por defecto (fail-safe clínico) |

---

## PM-UC03-ISCN — Generador Determinístico de Nomenclatura ISCN

| Campo | Valor |
|:---|:---|
| **ID** | PM-UC03-ISCN |
| **Título** | ISCNGenerator — Motor determinístico de nomenclatura ISCN 2024 |
| **Modelo** | Claude Opus (lógica clínica compleja) |
| **Input** | FSD_v2.md UC-006 · PRD_v2.md US-012, US-021 · BRD_v3.5 BR-04 |

### Prompt

```
Role: Especialista en bioinformática con dominio profundo de ISCN 2024 (International
System for Human Cytogenomic Nomenclature) e implementación de parsers determinísticos.

Task: Implementa ISCNGenerator que:
1. Recibe clasificación final de 46 cromosomas validados (pares 1-22, X, Y)
2. Genera string ISCN: "46,XY" normal / "47,XY,+21" trisomía 21 / "45,X" monosomía X
3. Detecta: trisomía, monosomía, translocaciones simples (v1.0)
4. El campo iscn_nomenclature es READ-ONLY tras generación (ningún endpoint PATCH)

Context:
- Estándar: ISCN 2024 (no 2020 — actualizado en BRD v3.5)
- Formato: {N_cromosomas},{sexo}[,{anomalías_ascendente}]
- Determinista: misma entrada → misma salida siempre (sin aleatoriedad)
- Restricción: si ∃ cromosoma sin validar → lanzar UnvalidatedChromosomesError (no generar)
- NUNCA generar ISCN con componente IA — motor de reglas puro

Reasoning:
1. Verificar que todos los cromosomas tengan validated=True
2. Contar total, X (par 23), Y (par 24)
3. Determinar número base: 46 normal, ≠46 → anomalía numérica
4. Ordenar anomalías en forma ascendente por número de cromosoma afectado
5. Verificar validez básica de la cadena generada con regex ISCN

Stop Condition: Tests pasan: "46,XY", "47,XY,+21", "45,X", "47,XX,+18" y rechaza
con UnvalidatedChromosomesError si cromosomas sin validar.

Output: Python + docstring + tests con paths explícitos
```

### Output (Artefactos Generados)
- `backend/app/services/iscn_generator.py`
- `backend/tests/test_iscn_generator.py`

### Invariantes
- Determinista: `ISCNGenerator.generate(chromosomes) == ISCNGenerator.generate(chromosomes)` siempre
- Lanza `UnvalidatedChromosomesError` si ∃ cromosoma con `validated=False`
- Tests pasan: 46,XX · 46,XY · 47,XY,+21 · 45,X · 47,XX,+18
- Ningún endpoint PATCH sobre `iscn_nomenclature` (verificable en OpenAPI spec)

### Failure Modes
| Fallo | Comportamiento esperado |
|:---|:---|
| Cromosomas sin validar | `UnvalidatedChromosomesError` — no se genera ISCN parcial |
| String override del Supervisor inválido | Validación regex ISCN básica → rechaza con `"ISCN inválido: ..."` |
| Anomalía no reconocida en v1.0 | Genera ISCN base correcto + nota `"anomalía compleja detectada — revisión manual"` |
| Reintento en misma muestra | Idempotente — retorna el mismo iscn_nomenclature ya almacenado |

---

## PM-UC03-AUDIT — Middleware de Audit Trail SHA256

| Campo | Valor |
|:---|:---|
| **ID** | PM-UC03-AUDIT |
| **Título** | AuditTrailMiddleware — Registro inalterable con hash chain SHA256 |
| **Modelo** | Claude Haiku (boilerplate estructurado) |
| **Input** | FSD_v2.md UC-005 §8 · BRD_v3.5 BR-05, BR-R4 · NFR-007 (21 CFR Part 11) |

### Prompt

```
Role: Desarrollador backend especializado en FastAPI y sistemas de auditoría para
aplicaciones clínicas reguladas bajo 21 CFR Part 11.

Task: Implementa AuditTrailMiddleware que:
1. Intercepta todos los PATCH en /api/v1/chromosomes/{id}/* y /api/v1/reports/{id}/*
2. Captura before_state (SELECT antes) y after_state (resultado tras 200 OK)
3. Calcula current_hash = SHA256(previous_hash + action + before + after + timestamp)
4. INSERT en tabla `edits` con hash chain — REVOKE UPDATE, DELETE al app_user
5. user_id extraído del JWT — NUNCA del body del request

Context:
- Stack: FastAPI + SQLAlchemy 2.0 + PostgreSQL 15
- Tabla edits: id, chromosome_id, user_id, action ENUM, before_state JSONB,
  after_state JSONB, previous_hash VARCHAR(64), current_hash VARCHAR(64), created_at DEFAULT NOW()
- CRITICAL: created_at siempre DEFAULT NOW() — nunca recibir del cliente
- Actions válidas: XAI_VIEWED, CORREGIR_CLASE, DIVIDIR, UNIR, ROTAR_90, VALIDATE,
  ISCN_OVERRIDE, SIGN_REPORT

Reasoning:
1. Dependency injection en FastAPI (no middleware global — más control)
2. Consultar el último `current_hash` de la misma muestra como `previous_hash`
3. Si endpoint retorna != 200: NO registrar (mantiene consistencia causal)
4. Hash chain verificable externamente: cualquier alteración rompe la cadena
5. Migration SQL: REVOKE UPDATE, DELETE ON edits FROM app_user

Stop Condition: (1) Middleware captura before/after correctamente, (2) hash chain
íntegra, (3) test de inalterabilidad pasa (UPDATE lanza PermissionError).

Output: Python + SQL migration + tests con paths explícitos
```

### Output (Artefactos Generados)
- `backend/app/middleware/audit_trail.py`
- `backend/migrations/0002_audit_trail_readonly.sql`
- `backend/tests/test_audit_trail.py`

### Invariantes
- Tabla `edits` solo permite INSERT (REVOKE UPDATE, DELETE en migration SQL)
- `user_id` siempre del JWT — test de inyección pasa (body `user_id` ignorado)
- Si endpoint falla → ningún registro en `edits`
- Hash chain verificable: `SHA256(previous_hash + payload) == current_hash`

### Failure Modes
| Fallo | Comportamiento esperado |
|:---|:---|
| DB no disponible al registrar audit | Endpoint falla con 503; operación del cromosoma también se revierte (atomicidad) |
| previous_hash no existe (primer registro) | Usa string vacío `""` como previous_hash — documentado en migration |
| Intento de UPDATE en edits | `PermissionError` en PostgreSQL — logueado como `SECURITY_VIOLATION` |
| Timestamp manipulado en el request | Ignorado — `created_at` siempre generado por `DEFAULT NOW()` en DB |

---

## PM-UC02-XAI — Grad-CAM Explicabilidad IA

| Campo | Valor |
|:---|:---|
| **ID** | PM-UC02-XAI |
| **Título** | GradCAM Service — Explicabilidad XAI para cromosomas naranjas |
| **Modelo** | Claude Opus |
| **Input** | FSD_v2.md UC-003 · PRD_v2.md US-005 · BRD_v3.5 BR-06 |

### Prompt

```
Role: Ingeniero ML especializado en Explainable AI (XAI) para aplicaciones médicas,
con dominio de Grad-CAM y su aplicación a redes convolucionales EfficientNet.

Task: Implementa GradCAMService que:
1. Recibe crop 224×224 y los logits de EfficientNet-B3 para un cromosoma
2. Calcula Grad-CAM sobre la última capa convolucional (features.dense_block5)
3. Genera heatmap superpuesto (opacidad 0.5) sobre el crop original
4. Identifica región de máxima intensidad y la mapea a banda cromosómica (lookup table)
5. Retorna: {heatmap_base64, salient_region, explanation_text}

Context:
- Modelo: EfficientNet-B3 — capa objetivo: últimas conv features
- Tiempo máximo: <1 segundo por cromosoma
- explanation_text: "La IA se basó en la banda {region} para clasificar como par {pair}"
- Log obligatorio: XAI_VIEWED en Audit Trail (BR-04 del BRD)
- El analista NO puede resolver cromosoma naranja sin haber abierto XAI

Reasoning:
1. Forward pass guardando activaciones de la capa objetivo
2. Backprop de la clase predicha → gradientes respecto a feature maps
3. Promedio de gradientes por canal → pesos de importancia α_k
4. Mapa de calor = ReLU(Σ α_k × A_k)
5. Resize a 224×224, superponer con colormap "jet", opacidad 0.5
6. Lookup table bandas G: región máxima → banda citogenética (ej: q22.3)

Stop Condition: Heatmap generado y región identificada en <1 segundo. Log XAI_VIEWED
registrado en Audit Trail.

Output: Python service con paths explícitos + lookup table de bandas G
```

### Output (Artefactos Generados)
- `backend/app/services/gradcam_service.py`
- `backend/app/data/chromosome_bands_lookup.json`
- `backend/tests/test_gradcam.py`

### Invariantes
- Heatmap generado en <1 segundo (verificable con pytest-benchmark)
- Log `XAI_VIEWED` registrado en Audit Trail antes de retornar la respuesta
- El cromosoma naranja NO puede marcarse como resuelto sin `xai_consulted=True`
- Opacidad del overlay: exactamente 0.5 (configurable pero con valor default obligatorio)

### Failure Modes
| Fallo | Comportamiento esperado |
|:---|:---|
| Región no identificable en lookup table | Retorna `explanation_text: "Región de influencia no determinable"` — no error |
| Grad-CAM tarda >1 segundo | Timeout → heatmap precomputado durante inferencia inicial es servido como cache |
| Logits no disponibles (inferencia antigua) | Re-ejecuta forward pass solo para Grad-CAM; no bloquea al analista |
| Crop corrupto o tamaño incorrecto | 422 — analista ve mensaje con instrucción de re-segmentar el cromosoma |

---

## PM-WS-01 — WebSocket Manager: Notificaciones en Tiempo Real

| Campo | Valor |
|:---|:---|
| **ID** | PM-WS-01 |
| **Título** | WebSocketManager — Push notifications via Redis PubSub |
| **Modelo** | Claude Sonnet |
| **Input** | FSD_v2.md UC-008 · PRD_v2.md US-014 · NFR-002 (latencia <500ms) |

### Prompt

```
Role: Desarrollador backend especializado en sistemas de tiempo real con FastAPI
WebSockets y Redis Pub/Sub para arquitecturas desacopladas.

Task: Implementa WebSocketManager que:
1. Mantiene conexiones WebSocket activas por sample_id y analyst_id
2. Celery Worker publica en Redis channel: `sample:{sample_id}:events`
3. FastAPI suscrito escucha el channel y hace push al cliente correcto en <500ms
4. Payload: {status, sample_id, chromosome_count, processing_time_ms}
5. Si analista desconectado: almacena evento 24h en DB para notificación al reconectar

Context:
- Stack: FastAPI WebSocket + Redis Pub/Sub + asyncio
- Cliente: ws://backend/ws/samples/{sample_id} con JWT en header
- NFR-002: latencia <500ms desde publicación Redis hasta recepción cliente
- Reconexión automática del cliente React (exponential backoff: 1s, 2s, 4s, max 30s)
- Múltiples clientes por sample_id posibles (supervisor + analista)

Reasoning:
1. Dict de conexiones: {sample_id: [WebSocket, ...]}
2. asyncio task suscripta a Redis PubSub sin bloquear event loop
3. Al recibir evento: push a TODOS los WebSockets del sample_id
4. Limpiar conexiones cerradas del dict automáticamente (weakrefs)
5. Si analista desconectado: INSERT en tabla `pending_notifications`

Stop Condition: Notificación recibida en <500ms (test con pytest-asyncio).
Múltiples clientes reciben el mismo evento. Reconexión funciona tras desconexión.

Output: Python con paths: websocket_manager.py, event_publisher.py + TypeScript cliente
```

### Output (Artefactos Generados)
- `backend/app/ws/websocket_manager.py`
- `backend/app/ws/event_publisher.py`
- `frontend/src/services/websocketService.ts`

### Invariantes
- Latencia Push <500ms en red local (verificable con Playwright timing)
- Dict de conexiones sin memory leak (conexiones cerradas limpiadas automáticamente)
- Cliente React reconecta con exponential backoff (1s → 2s → 4s → máx 30s)
- Payload siempre incluye `processing_time_ms` para monitoreo de NFR-001

### Failure Modes
| Fallo | Comportamiento esperado |
|:---|:---|
| Redis PubSub no disponible | WebSocketManager detecta falla → polling fallback cada 5s hacia `/api/v1/samples/{id}` |
| Analista desconectado durante procesamiento | Evento almacenado en `pending_notifications` → entregado al reconectar |
| WebSocket flood (>100 mensajes/segundo) | Rate limiting activo → mensajes agrupados en batches de 10 por segundo |
| JWT expirado en conexión WebSocket | Cierre con código 4001 (Unauthorized) → cliente redirige a login |

---

## Índice de Trazabilidad Completa

| PM ID | User Story PRD | Caso de Uso FSD | Regla de Negocio BRD | Output principal |
|:---|:---|:---|:---|:---|
| PM-SETUP-01 | — | — | — | docker-compose.yml |
| PM-UC01-API | US-001, US-002 | UC-001 | BR-01 | POST /samples/image |
| PM-UC01-SEG | US-003 | UC-002 | NFR-004 | segmentation.py (U-Net) |
| PM-UC01-CLS | US-004 | UC-002 | BR-02, BR-03 | classification.py (EfficientNet-B3) |
| PM-UC02-SEM | US-004, US-006, US-016 | UC-002, UC-003 | BR-02, BR-03 | ChromosomeCanvas.tsx |
| PM-UC03-ISCN | US-012, US-021 | UC-006 | BR-04 | iscn_generator.py |
| PM-UC03-AUDIT | US-010, US-017 | UC-005 | BR-05, BR-R4 | audit_trail.py |
| PM-UC02-XAI | US-005 | UC-003 | BR-06 | gradcam_service.py |
| PM-WS-01 | US-014 | UC-008 | NFR-002 | websocket_manager.py |
| PM-FSD-001* | — | UC-002 | NFR-004 | Contrato FSD §8 |

*PM-FSD-001/002/003 documentados en FSD_v2.md §8 — total: **10 contratos** ✅

---

## Métricas de Cobertura de Prompts

| Métrica | Valor | Cálculo |
|:---|:---|:---|
| **Prompt Coverage** | 85% | 17 US con PM vs 21 US totales en PRD |
| **Spec Fidelity** | 94% | 16 de 17 endpoints API del FSD con PM asociado |
| **Failure Mode Coverage** | 100% | 8 PMs × promedio 4 failure modes = 32 failure modes documentados |
| **Model Accuracy** | 100% | Todos los PMs usan U-Net + EfficientNet-B3 (ninguno menciona modelos obsoletos) |
