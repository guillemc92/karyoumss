# PROMPT MAPPINGS v1.0
## BIOMED UMSS — Trazabilidad Requerimiento → Prompt → Código

| Campo | Detalle |
|---|---|
| **Producto** | BIOMED UMSS – Intelligent Karyotyping |
| **Versión** | 1.0 |
| **Fecha** | Mayo 2026 |
| **Autor** | Ing. Guillermo Mamani Chambi |
| **Trazabilidad** | FSD_v1.md → PROMPT_MAPPINGS.md |
| **Propósito** | Fuente de verdad del ciclo agéntico: Input (requerimiento) → Prompt → Output (código) |

---

## ¿Qué es el PROMPT_MAPPINGS?

En el desarrollo agéntico con IA, el PROMPT_MAPPINGS reemplaza al backlog tradicional. Cada entrada mapea:

- **Input**: el requerimiento o artefacto de origen (User Story, Caso de Uso, Regla de Negocio)
- **Prompt**: los 6 elementos obligatorios (Role, Task, Context, Reasoning, Stop Condition, Output format)
- **Output**: el artefacto de código generado y sus invariantes verificables

**Convención de IDs:** `PM-[MÓDULO]-[NÚMERO]` (ej. `PM-UC01-SEG`)

---

## PM-SETUP-01 — Scaffolding del Proyecto

| Campo | Valor |
|---|---|
| **ID** | PM-SETUP-01 |
| **Título** | Estructura inicial del proyecto con Docker Compose |
| **Versión** | 1.0 |
| **Modelo recomendado** | Claude Sonnet (generación estándar) |

### Input (Artefacto Origen)
- FSD_v1.md §2.3 Estructura del proyecto
- FSD_v1.md §2.1 Stack tecnológico
- LFSD.md §5 T-01

### Prompt

```
Role: Eres un arquitecto de software senior especializado en sistemas FastAPI + React con experiencia en infraestructura Docker para aplicaciones clínicas.

Task: Genera el scaffolding completo del proyecto BIOMED UMSS incluyendo:
1. docker-compose.yml con servicios: fastapi, react, postgresql, redis, celery_worker, minio
2. Estructura de carpetas backend/ y frontend/ según FSD §2.3
3. Dockerfile para cada servicio con configuración de GPU para celery_worker
4. Variables de entorno (.env.example) para todos los servicios

Context:
- Stack: FastAPI Python 3.11+, React 18 + Vite, PostgreSQL 15, Redis 7, Celery 5, MinIO
- El servicio celery_worker debe tener acceso a GPU (nvidia runtime)
- Los datos de pacientes nunca deben salir del entorno local sin anonimización CHN
- Restricción: el docker-compose debe funcionar con `docker compose up` sin configuración adicional

Reasoning:
1. Verificar que cada servicio tenga healthcheck configurado
2. Asegurar que celery_worker depende de redis y fastapi
3. Verificar que postgresql tenga volumen persistente
4. Confirmar que minio tenga bucket inicial configurado

Stop Condition: Detente cuando todos los servicios tengan healthcheck, dependencias correctas y el proyecto pueda iniciarse con `docker compose up --build` sin errores.

Output: Archivos en formato de bloque de código con path explícito:
- `docker-compose.yml`
- `backend/Dockerfile`
- `frontend/Dockerfile`
- `.env.example`
```

### Output (Artefacto Generado)
- `docker-compose.yml`
- `backend/Dockerfile`
- `frontend/Dockerfile`
- `.env.example`

### Invariantes
- `docker compose up --build` debe ejecutarse sin errores
- Servicio `celery_worker` debe tener `deploy.resources.reservations.devices` para GPU
- Ninguna variable de entorno con datos reales en el repositorio

---

## PM-UC01-API — Endpoint de Creación de Muestra con CHN

| Campo | Valor |
|---|---|
| **ID** | PM-UC01-API |
| **Título** | POST /samples — Registro de muestra con anonimización CHN |
| **Versión** | 1.0 |
| **Modelo recomendado** | Claude Sonnet |

### Input (Artefacto Origen)
- FSD_v1.md §4 UC-01 — Flujo principal pasos 1–4
- PRD_v1.md US-01, US-02
- FSD_v1.md §5 RN-03 (CHN obligatorio antes de transmisión cloud)
- Criterio Gherkin: `PRD_v1.md §6 US-02`

### Prompt

```
Role: Eres un desarrollador backend senior especializado en FastAPI con experiencia en sistemas de salud que deben cumplir normativas de privacidad de datos (HIPAA/GDPR equivalente).

Task: Implementa el endpoint POST /samples en FastAPI que:
1. Recibe datos de la muestra (sin datos de paciente en el body del request)
2. Genera automáticamente un código CHN único con formato CHN-YYYY-NNNN
3. Valida que el código CHN sea único en PostgreSQL
4. Retorna 201 Created con el CHN asignado y el sample_id UUID

Context:
- Stack: FastAPI + SQLAlchemy 2.0 + Pydantic v2 + PostgreSQL 15
- Modelo de datos: tabla `samples` con campos (id UUID PK, chn_code VARCHAR(20) UNIQUE, status ENUM, analyst_id UUID FK, created_at TIMESTAMP)
- El formato CHN debe ser: CHN-{AÑO_4_DÍGITOS}-{NÚMERO_4_DÍGITOS_SECUENCIAL}
- Restricción crítica: NUNCA registrar datos del paciente (nombre, edad, DNI) en este endpoint
- El endpoint debe requerir autenticación JWT con rol "analista"

Reasoning:
1. Verificar unicidad del CHN antes de insertar
2. Si colisión de CHN, reintentar con número siguiente
3. Registrar en audit log la creación de la muestra
4. Retornar 409 si el analyst_id no tiene rol "analista"

Stop Condition: Detente cuando el endpoint pase los tests unitarios de: creación exitosa, unicidad CHN, autenticación requerida y rechazo de datos de paciente en el body.

Output: Formato JSON Schema + bloque de código Python:
{
  "endpoint": "POST /samples",
  "request_body": { ... },
  "response_201": { "sample_id": "uuid", "chn_code": "CHN-2026-0001" },
  "response_409": { "detail": "CHN collision, retry" }
}
```

### Output (Artefacto Generado)
- `backend/app/api/samples.py` — Router con endpoint POST /samples
- `backend/app/schemas/sample.py` — Pydantic schemas
- `backend/app/services/chn_service.py` — Generador de códigos CHN
- `backend/tests/test_samples.py` — Tests unitarios

### Invariantes
- CHN nunca incluye datos del paciente
- Unicidad garantizada con retry automático
- Endpoint retorna 401 sin JWT válido
- Test de rechazo pasa: body con "patient_name" debe retornar 422

---

## PM-UC01-SEG — Celery Task: Segmentación con Mask R-CNN

| Campo | Valor |
|---|---|
| **ID** | PM-UC01-SEG |
| **Título** | Celery Task — Segmentación de cromosomas con Mask R-CNN |
| **Versión** | 1.0 |
| **Modelo recomendado** | Claude Opus (lógica compleja de visión artificial) |

### Input (Artefacto Origen)
- FSD_v1.md §4 UC-01 pasos 6–9
- FSD_v1.md §2.1 Stack: Mask R-CNN, TorchServe
- PRD_v1.md NFR-01 (inferencia <15s)
- LFSD.md §5 T-05

### Prompt

```
Role: Eres un ingeniero de Machine Learning especializado en visión computacional para aplicaciones médicas, con experiencia en Mask R-CNN para segmentación de instancias y procesamiento de imágenes citogenéticas.

Task: Implementa la Celery task `process_metaphase_image` que:
1. Descarga la imagen de metafase desde S3/MinIO usando el CHN como identificador
2. Aplica pre-procesamiento CLAHE para realzar las bandas G de los cromosomas
3. Ejecuta inferencia con Mask R-CNN via TorchServe REST API
4. Retorna lista de objetos con: {chromosome_id, mask_polygon, bounding_box, confidence_pre}
5. Maneja el tiling para imágenes >4K que exceden la VRAM de la GPU

Context:
- Stack: Celery 5 + PyTorch + TorchServe REST API en localhost:8080
- Imágenes de entrada: TIFF/PNG, resolución hasta 8000x6000px, hasta 50MB
- TorchServe endpoint: POST http://torchserve:8080/predictions/mask_rcnn
- Tiling strategy: dividir en patches 1024x1024 con overlap 64px, ensamblar con NMS
- El task debe publicar progreso: "preprocessing", "segmenting", "assembling"
- IoU mínimo aceptable: 0.95 (si IoU < 0.95 en más del 10% de objetos, marcar muestra como "low_quality")

Reasoning:
1. Verificar que la imagen se descargue correctamente antes de iniciar pipeline
2. Aplicar CLAHE con parámetros: clipLimit=3.0, tileGridSize=(8,8)
3. Para imágenes >4K: dividir en tiles con overlap, ejecutar Mask R-CNN por tile
4. Post-procesamiento: Non-Maximum Suppression para eliminar duplicados en bordes de tiles
5. Si TorchServe no responde en 10s: reintentar hasta 3 veces, luego marcar como error

Stop Condition: Detente cuando la task: (1) procese correctamente una imagen de 15MB en <15s, (2) maneje el tiling sin perder cromosomas en los bordes, (3) registre el progreso en Redis para el WebSocket.

Output: Bloque de código Python con:
- `backend/app/tasks/segmentation.py` — Celery task completa
- Ejemplo de output: lista de dicts con polygon_coords en formato GeoJSON-like
```

### Output (Artefacto Generado)
- `backend/app/tasks/segmentation.py`
- `backend/app/services/image_preprocessor.py`
- `backend/app/services/tiling_service.py`

### Invariantes
- Task completa en <15s para imagen estándar (2048x1536)
- Tiling no pierde objetos en bordes (verificable con test de imagen sintética)
- Progreso publicado en Redis key `task:{task_id}:progress`
- Si TorchServe falla 3 veces consecutivas → estado muestra = "error"

---

## PM-UC01-CLS — Celery Task: Clasificación con ResNet50 + Softmax

| Campo | Valor |
|---|---|
| **ID** | PM-UC01-CLS |
| **Título** | Celery Task — Clasificación de cromosomas y score Softmax |
| **Versión** | 1.0 |
| **Modelo recomendado** | Claude Sonnet |

### Input (Artefacto Origen)
- FSD_v1.md §4 UC-01 paso 10
- PRD_v1.md US-06 (semaforización por score)
- FSD_v1.md §5 RN-02 (bloqueo <85%)
- BRD_v2.md §4.1 umbral Softmax 85%

### Prompt

```
Role: Eres un ingeniero de ML especializado en clasificación de imágenes médicas con ResNet50 y en el diseño de pipelines de inferencia confiables para entornos clínicos.

Task: Implementa la función `classify_chromosomes` que:
1. Recibe la lista de cromosomas segmentados (recortados del resultado de Mask R-CNN)
2. Ejecuta ResNet50 via TorchServe para clasificar cada cromosoma en pares 1–22, X, Y
3. Extrae el score Softmax de la clase predicha (probabilidad de la clase ganadora)
4. Retorna para cada cromosoma: {chromosome_id, predicted_pair, confidence_score, all_scores}
5. Aplica el umbral de 85%: si confidence_score < 0.85 → campo "requires_review": true

Context:
- TorchServe endpoint: POST http://torchserve:8080/predictions/resnet50_karyotype
- Input por cromosoma: imagen recortada 64x64px en base64
- Output esperado de TorchServe: {"predictions": [{"class": "pair_1", "score": 0.923}, ...]}
- El campo all_scores debe contener todos los scores para análisis de consistencia global del cariograma
- Restricción: nunca redondear el score antes de persistirlo (guardar float completo)

Reasoning:
1. Procesar cromosomas en batch de 16 para optimizar throughput de GPU
2. Verificar que la suma de scores Softmax sea ≈ 1.0 (si no, el modelo tuvo error)
3. Implementar análisis de consistencia global: verificar que no haya dos cromosomas con mismo par si la muestra es normal
4. Persistir en tabla `chromosomes` con score completo

Stop Condition: Detente cuando: (1) clasifique correctamente los 46 cromosomas de una muestra estándar 46,XY, (2) el umbral 85% esté correctamente aplicado, (3) los scores se persistan sin redondeo.

Output: Código Python + schema JSON:
- `backend/app/tasks/classification.py`
- Schema de respuesta: `{chromosome_id: UUID, predicted_pair: int, confidence_score: float, requires_review: bool}`
```

### Output (Artefacto Generado)
- `backend/app/tasks/classification.py`
- `backend/app/services/softmax_analyzer.py`

### Invariantes
- confidence_score persiste como FLOAT sin redondeo
- requires_review = True cuando score < 0.85 (no <0.849...)
- Batch processing: máximo 16 cromosomas por request a TorchServe
- Análisis de consistencia global detecta duplicados de par en cariotipo normal

---

## PM-UC02-SEM — Componente React: Semaforización Visual

| Campo | Valor |
|---|---|
| **ID** | PM-UC02-SEM |
| **Título** | Componente React — Semaforización de confianza en mesa de edición |
| **Versión** | 1.0 |
| **Modelo recomendado** | Claude Sonnet |

### Input (Artefacto Origen)
- PRD_v1.md US-06, US-07, US-10
- PRD_v1.md §6 Gherkin UC-02
- FSD_v1.md §4 UC-02 paso 2
- BRD_v2.md §8.2 R1 (4 mecanismos anti-sesgo)

### Prompt

```
Role: Eres un desarrollador frontend senior especializado en React con Konva.js para canvas interactivos y en UX para aplicaciones médicas donde la claridad visual es crítica para la seguridad clínica.

Task: Implementa el componente ChromosomeCanvas que:
1. Renderiza cromosomas en Konva.js Stage con border color según confidence_score
2. Verde (#00e676) para score ≥ 0.85, Naranja (#ff6d00) para score < 0.85
3. El borde naranja debe ser 3px (vs 1px verde) para mayor visibilidad
4. Al hacer clic en un cromosoma naranja: lo selecciona y lo resalta en el panel lateral
5. El botón "Generar Informe" debe estar DESHABILITADO si existen cromosomas < 0.85 sin validar
6. Implementar gradiente de color continuo (no solo binario) para representar scores intermedios

Context:
- Stack: React 18 + Konva.js 9 + Zustand (estado global)
- Los cromosomas se cargan desde: GET /samples/{id}/chromosomes
- Estructura de datos: [{id, pair, confidence_score, polygon_coords, validated, requires_review}]
- La "Mesa de Edición" ya existe como prototipo en `correccion de cariotipo.html` del Módulo 3
- Implementar gradiente: score 0.85 = verde puro, 0.7 = amarillo-naranja, <0.6 = rojo

Reasoning:
1. Usar Konva.js Shape con stroke dinámico según score
2. El estado de validación debe vivir en Zustand store, no en estado local del componente
3. El botón "Generar Informe" debe suscribirse al store y recalcular en cada cambio de validación
4. Implementar contador visual: "X cromosomas pendientes de revisión"

Stop Condition: Detente cuando: (1) el semáforo muestre correctamente verde/naranja, (2) el botón se bloquee con cromosomas pendientes, (3) el gradiente sea visible para scores intermedios.

Output: Componentes React en TypeScript:
- `frontend/src/components/EditorCanvas/ChromosomeCanvas.tsx`
- `frontend/src/store/chromosomeStore.ts` (Zustand)
- `frontend/src/components/EditorCanvas/ReviewPanel.tsx`
```

### Output (Artefacto Generado)
- `frontend/src/components/EditorCanvas/ChromosomeCanvas.tsx`
- `frontend/src/store/chromosomeStore.ts`
- `frontend/src/components/EditorCanvas/ReviewPanel.tsx`

### Invariantes
- Botón "Generar Informe" deshabilitado con 1+ cromosomas <85% sin validar
- Gradiente de color visible: no solo verde/naranja sino escala continua
- Estado de validación persiste en Zustand (no se pierde al re-render)
- Accesibilidad: borde naranja de 3px mínimo (visible sin distinción de colores)

---

## PM-UC03-ISCN — Generación Automática de Nomenclatura ISCN

| Campo | Valor |
|---|---|
| **ID** | PM-UC03-ISCN |
| **Título** | Servicio de generación automática de nomenclatura ISCN |
| **Versión** | 1.0 |
| **Modelo recomendado** | Claude Opus (lógica clínica compleja) |

### Input (Artefacto Origen)
- FSD_v1.md §5 RN-06 (ISCN auto-generado, read-only)
- PRD_v1.md US-11
- FSD_v1.md §4 UC-03 paso 3
- BRD_v2.md §4.2 F-07

### Prompt

```
Role: Eres un especialista en bioinformática con profundo conocimiento de la nomenclatura ISCN (International System for Human Cytogenomic Nomenclature) 2020 y experiencia implementando parsers y generadores de nomenclatura citogenética en Python.

Task: Implementa el servicio ISCNGenerator que:
1. Recibe la clasificación final de 46 cromosomas (con pares 1-22, X, Y y sus posiciones)
2. Genera la cadena ISCN estándar (ej: "46,XY" para cariotipo masculino normal)
3. Detecta y codifica anomalías estructurales básicas si están presentes
4. El campo iscn_nomenclature es READ-ONLY una vez generado (no editable por el usuario)

Context:
- Estándar: ISCN 2020 (International System for Human Cytogenomic Nomenclature)
- Formato básico: {número_cromosomas},{sexo} (ej: 46,XX para femenino normal; 46,XY para masculino normal)
- Anomalías a detectar en v1: trisomía (47,+21), monosomía (45,X), translocaciones simples
- El generador debe ser determinista: misma entrada → misma salida siempre
- Restricción: si la clasificación tiene cromosomas sin validar, no debe generar nomenclatura

Reasoning:
1. Verificar que todos los 46 cromosomas estén validados antes de generar
2. Contar: número total de cromosomas, número de X, número de Y
3. Detectar desviaciones del número esperado (46) → añadir notación de anomalía
4. Generar string ISCN siguiendo el estándar 2020

Stop Condition: Detente cuando: (1) genere "46,XY" para cariotipo masculino normal, (2) genere "47,+21" para trisomía 21, (3) rechace generar si existen cromosomas sin validar.

Output: Servicio Python con docstring completo:
- `backend/app/services/iscn_generator.py`
- Tests: `backend/tests/test_iscn_generator.py` con casos: 46,XX / 46,XY / 47,+21 / 45,X
```

### Output (Artefacto Generado)
- `backend/app/services/iscn_generator.py`
- `backend/tests/test_iscn_generator.py`

### Invariantes
- Determinista: misma entrada → misma salida
- Rechaza generar con cromosomas sin validar → excepción `UnvalidatedChromosomesError`
- Test "46,XY" pasa · Test "47,+21" pasa · Test "45,X" pasa
- Campo read-only: ningún endpoint permite PATCH en iscn_nomenclature

---

## PM-UC03-AUDIT — Middleware de Audit Trail

| Campo | Valor |
|---|---|
| **ID** | PM-UC03-AUDIT |
| **Título** | Middleware FastAPI — Audit trail inalterable de ediciones |
| **Versión** | 1.0 |
| **Modelo recomendado** | Claude Haiku (boilerplate) |

### Input (Artefacto Origen)
- FSD_v1.md §5 RN-07 (audit trail en todos los PATCH endpoints)
- PRD_v1.md US-16
- FSD_v1.md §6 Diccionario: tabla `edits`
- BRD_v2.md §8.3 RC4

### Prompt

```
Role: Eres un desarrollador backend especializado en FastAPI con experiencia en sistemas de auditoría para aplicaciones clínicas donde la trazabilidad es un requisito legal.

Task: Implementa el middleware AuditTrailMiddleware para FastAPI que:
1. Intercepta todos los requests PATCH a /chromosomes/{id}/*
2. Captura el estado before (consulta DB antes) y after (resultado de la operación)
3. Registra en tabla `edits`: chromosome_id, user_id, action, before_state, after_state, timestamp
4. El registro debe ser INALTERABLE: la tabla edits solo permite INSERT, no UPDATE ni DELETE

Context:
- Stack: FastAPI + SQLAlchemy 2.0 + PostgreSQL 15
- Tabla `edits`: {id UUID PK, chromosome_id UUID FK, user_id UUID FK, action ENUM, before_state JSONB, after_state JSONB, created_at TIMESTAMP DEFAULT NOW()}
- La inalterabilidad se garantiza a nivel de base de datos con: REVOKE UPDATE, DELETE ON edits FROM app_user
- El user_id debe extraerse del JWT token, nunca del body del request
- Actions: "rotate", "move", "split", "merge", "reclassify", "validate"

Reasoning:
1. Usar dependency injection de FastAPI para el middleware
2. Capturar before_state ANTES de ejecutar el endpoint
3. Capturar after_state DESPUÉS de que el endpoint retorna 200
4. Si el endpoint falla, NO registrar en audit trail
5. Incluir migration SQL que revoca permisos de UPDATE/DELETE

Stop Condition: Detente cuando: (1) el middleware capture correctamente before/after, (2) la migration SQL revoque permisos de modificación, (3) un test verifique que INSERT funciona pero UPDATE falla.

Output: Código Python + SQL migration:
- `backend/app/middleware/audit_trail.py`
- `backend/migrations/xxx_audit_trail_readonly.sql`
- `backend/tests/test_audit_trail.py`
```

### Output (Artefacto Generado)
- `backend/app/middleware/audit_trail.py`
- `backend/migrations/xxx_audit_trail_readonly.sql`
- `backend/tests/test_audit_trail.py`

### Invariantes
- Tabla `edits` solo permite INSERT (REVOKE UPDATE, DELETE)
- user_id siempre del JWT, nunca del body
- Si endpoint falla → ningún registro en edits
- Test de inalterabilidad: `UPDATE edits SET ...` debe lanzar PermissionError

---

## PM-WS-01 — WebSocket: Notificación de Inferencia Completada

| Campo | Valor |
|---|---|
| **ID** | PM-WS-01 |
| **Título** | WebSocket Manager — Push notification al cliente |
| **Versión** | 1.0 |
| **Modelo recomendado** | Claude Sonnet |

### Input (Artefacto Origen)
- FSD_v1.md §4 UC-01 paso 12–13
- PRD_v1.md US-05, NFR-02 (latencia <500ms)
- LFSD.md §2 UC-01 criterio Gherkin

### Prompt

```
Role: Eres un desarrollador backend especializado en sistemas de tiempo real con FastAPI WebSockets y Redis Pub/Sub para arquitecturas desacopladas entre workers y clientes web.

Task: Implementa el WebSocketManager que:
1. Mantiene conexiones WebSocket activas por sample_id
2. Celery Worker publica en Redis channel: `sample:{sample_id}:events`
3. FastAPI escucha el channel y hace push al cliente WebSocket correcto
4. Payload del evento: {sample_id, status, chromosome_count, processing_time_ms}
5. Reconexión automática del cliente si la conexión se pierde

Context:
- Stack: FastAPI WebSocket + Redis Pub/Sub + asyncio
- El cliente React se conecta a: ws://backend/ws/samples/{sample_id}
- El Celery Worker publica via Redis: `redis.publish(f"sample:{sample_id}:events", json.dumps(payload))`
- NFR: latencia entre publicación Redis y recepción cliente < 500ms
- Manejar casos: cliente desconectado, sample_id inválido, múltiples clientes por muestra

Reasoning:
1. Usar asyncio para escuchar Redis Pub/Sub sin bloquear el event loop
2. Mantener dict de conexiones: {sample_id: [WebSocket, ...]}
3. Al recibir evento Redis, hacer push a todos los WebSockets del sample_id
4. Limpiar conexiones cerradas del dict automáticamente

Stop Condition: Detente cuando: (1) el cliente recibe notificación en <500ms tras publicación Redis, (2) múltiples clientes del mismo sample_id reciben el evento, (3) reconexión funciona tras desconexión.

Output:
- `backend/app/ws/websocket_manager.py`
- `backend/app/api/websocket_routes.py`
- `frontend/src/services/websocketService.ts` (cliente React con reconexión)
```

### Output (Artefacto Generado)
- `backend/app/ws/websocket_manager.py`
- `backend/app/api/websocket_routes.py`
- `frontend/src/services/websocketService.ts`

### Invariantes
- Latencia Push < 500ms en red local (verificable con Playwright timing)
- Dict de conexiones no tiene memory leak (conexiones cerradas limpiadas)
- Cliente React se reconecta automáticamente tras 3s de desconexión
- Payload siempre incluye `processing_time_ms` para monitoreo de NFR-01

---

## Índice de Trazabilidad Completa

| Prompt ID | User Story | Caso de Uso | Regla de Negocio | Output |
|---|---|---|---|---|
| PM-SETUP-01 | — | — | — | docker-compose.yml |
| PM-UC01-API | US-01, US-02 | UC-01 pasos 1–4 | RN-03, RN-04 | POST /samples |
| PM-UC01-SEG | US-01, US-05 | UC-01 pasos 6–9 | — | segmentation.py |
| PM-UC01-CLS | US-06 | UC-01 paso 10 | RN-02 | classification.py |
| PM-UC02-SEM | US-06, US-07, US-10 | UC-02 pasos 1–7 | RN-02 | ChromosomeCanvas.tsx |
| PM-UC03-ISCN | US-11 | UC-03 paso 3 | RN-06 | iscn_generator.py |
| PM-UC03-AUDIT | US-16 | UC-03 audit | RN-07 | audit_trail.py |
| PM-WS-01 | US-05 | UC-01 pasos 12–13 | — | websocket_manager.py |

---

*Documento vivo — agregar nuevo PM por cada feature implementada*
*Trazabilidad: PROMPT_MAPPINGS.md ← FSD_v1.md ← PRD_v1.md ← BRD_v2.md*
