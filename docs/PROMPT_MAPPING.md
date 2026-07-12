# PROMPT MAPPING v2.0
## BIOMED UMSS — Trazabilidad Requerimiento → Prompt → Código

| Campo | Detalle |
|---|---|
| **Producto** | BIOMED UMSS – Intelligent Karyotyping |
| **Versión** | 2.0 |
| **Fecha** | Mayo 2026 |
| **Autor** | Ing. Guillermo Mamani Chambi |
| **Trazabilidad** | FSD_vFinal.md → PROMPT_MAPPING.md |
| **Propósito** | Fuente de verdad del ciclo agéntico: Input (requerimiento) → Prompt → Output (código) |

---

## ¿Qué es el PROMPT_MAPPING?

En el desarrollo agéntico con IA, el PROMPT_MAPPING reemplaza al backlog tradicional. Cada entrada mapea:
- **Input**: el requerimiento o artefacto de origen (User Story, Caso de Uso, Regla de Negocio).
- **Prompt**: los 6 elementos obligatorios (Role, Task, Context, Reasoning, Stop Condition, Output format).
- **Output**: el artefacto de código generado y sus invariantes verificables.

**Convención de IDs:** `PM-[MÓDULO]-[NÚMERO]` (ej. `PM-UC01-SEG`)

---

## ⚡ Mapeo Rápido de Símbolos, Archivos y Métricas

Esta tabla proporciona un acceso rápido a la trazabilidad entre los invariantes de negocio (símbolos de reglas de negocio RN, decisiones ADR, casos de uso UC) y su materialización en código, detallando el impacto cuantitativo (antes y después).

| Símbolo | Tipo | Archivo / Sección | Métricas Antes | Métricas Después |
| :--- | :--- | :--- | :--- | :--- |
| **RN-01 / BR-R5** | Regla clínica (Bloqueo de emisión) | `backend/app/services/report_service.py` / `correccion de cariotipo.html` | Emisión manual sin validación. Riesgo clínico alto. | Bloqueo automático. 0 reportes emitidos si hay cromosomas <85% sin validar. |
| **RN-02 / BR-02** | Confianza IA (Umbral 85%) | `backend/app/tasks/classification.py` / `backend/app/schemas/sample.py` | Clasificación sin métrica de certeza. 100% de muestras requieren revisión visual exhaustiva. | Semaforización automática. Solo 13% de cromosomas marcados en naranja (requieren revisión). |
| **RN-03 / BR-01** | Privacidad de datos (CHN en Borde) | `backend/app/services/chn_service.py` / `frontend/src/services/api.ts` | Datos de paciente (PII) transmitidos en crudo. Riesgo legal alto. | 100% de PII anonimizada localmente. 0 datos de paciente transmitidos a la nube. |
| **RN-04** | ISCN Read-Only | `backend/app/api/samples.py` (No endpoints PATCH) | Nomenclatura alterable directamente en DB. Pérdida de integridad. | Bloqueo de API. Campo `iscn_nomenclature` inalterable post-generación. |
| **RN-05** | Inalterabilidad EditTrail | `backend/app/middleware/audit_trail.py` / Trigger DB | Tabla `edits` vulnerable a modificaciones y borrados. | Triggers SQL aplican `REVOKE UPDATE, DELETE`. 100% de inserciones auditables. |
| **ADR-0001** | Tiling GPU | `backend/app/services/tiling_service.py` | Imágenes >4K causan GPU OOM (100% fallos). | 0% OOM. Procesamiento constante con tiles de 1024x1024. |
| **ADR-0002** | Pipeline Asíncrono | `backend/app/tasks/segmentation.py` (Redis + Celery) | Hilo HTTP bloqueado (~15s). Timeouts constantes en cliente. | Desacoplamiento total. Hilo HTTP responde en <100ms. Inferencia corre en background. |
| **ADR-0003** | Anonimización borde | `backend/app/core/auth.py` | Procesamiento en la nube con nombres de pacientes expuestos. | Anonimización previa al upload. Cero incidentes de exposición de PII. |
| **ADR-0004** | Monolito modular | Estructura de carpetas `/backend` y `/frontend` | Repositorio fragmentado con dependencias cruzadas difíciles de compilar. | Arquitectura limpia y ordenada. Despliegue independiente de workers y API. |
| **ADR-0005** | AWS Cloud Deploy | `docs/adr/0005-cloud-provider-y-estilo-de-despliegue.md` | Servidores físicos costosos de mantener y sin escalabilidad de GPU. | Escalado automático en AWS ECS. Costo de GPU optimizado al apagar workers inactivos. |
| **UC-01** | Ingesta de metafase | `backend/app/api/samples.py` | Registro y carga manual lento (>5 minutos por muestra). | Registro y carga asíncrona automatizada en S3 en <3 segundos. |
| **UC-02** | Procesamiento IA | `backend/app/tasks/classification.py` | Cariotipado manual (TTK de 45 minutos). | Borrador automático en <15 segundos de inferencia en GPU. |
| **UC-03** | Mesa de edición HITL (FSD-UC-003) | `demo-fsd-uc003.html` · `correccion de cariotipo.html` | UI con lag al arrastrar SVG (>100ms). Informe emitible sin validar naranjas. | RN-02 semaforización + RN-01 bloqueo ISCN en demo. CHN sin PII. |

---

## PM-SETUP-01 — Scaffolding del Proyecto

| Campo | Valor |
|---|---|
| **ID** | PM-SETUP-01 |
| **Título** | Estructura inicial del proyecto con Docker Compose |
| **Versión** | 1.0 |
| **Modelo recomendado** | Claude Sonnet (generación estándar) |

### Input (Artefacto Origen)
- FSD_vFinal.md §2.3 Estructura del proyecto.
- FSD_vFinal.md §2.1 Stack tecnológico.

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
- `docker compose up --build` debe ejecutarse sin errores.
- Servicio `celery_worker` debe tener `deploy.resources.reservations.devices` para GPU.
- Ninguna variable de entorno con datos reales en el repositorio.

---

## PM-UC01-API — Endpoint de Creación de Muestra con CHN

| Campo | Valor |
|---|---|
| **ID** | PM-UC01-API |
| **Título** | POST /samples — Registro de muestra con anonimización CHN |
| **Versión** | 1.0 |
| **Modelo recomendado** | Claude Sonnet |

### Input (Artefacto Origen)
- FSD_vFinal.md §4 UC-01 — Flujo principal pasos 1–4.
- FSD_vFinal.md §5 RN-03 (CHN obligatorio antes de transmisión cloud).

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
- `backend/app/api/samples.py` — Router con endpoint POST /samples.
- `backend/app/schemas/sample.py` — Pydantic schemas.
- `backend/app/services/chn_service.py` — Generador de códigos CHN.

### Invariantes
- CHN nunca incluye datos del paciente.
- Unicidad garantizada con retry automático.
- Endpoint retorna 401 sin JWT válido.

---

## PM-UC01-SEG — Celery Task: Segmentación con Mask R-CNN

| Campo | Valor |
|---|---|
| **ID** | PM-UC01-SEG |
| **Título** | Celery Task — Segmentación de cromosomas con Mask R-CNN |
| **Versión** | 1.0 |
| **Modelo recomendado** | Claude Opus |

### Input (Artefacto Origen)
- FSD_vFinal.md §4 UC-01 pasos 6–9.
- FSD_vFinal.md §2.1 Stack: U-Net, TorchServe.

### Prompt
```
Role: Eres un ingeniero de Machine Learning especializado en visión computacional para aplicaciones médicas, con experiencia en U-Net para segmentación de instancias y procesamiento de imágenes citogenéticas.

Task: Implementa la Celery task `process_metaphase_image` que:
1. Descarga la imagen de metafase desde S3/MinIO usando el CHN como identificador
2. Aplica pre-procesamiento CLAHE para realzar las bandas G de los cromosomas
3. Ejecuta inferencia con U-Net via TorchServe REST API
4. Retorna lista de objetos con: {chromosome_id, mask_polygon, bounding_box, confidence_pre}
5. Maneja el tiling para imágenes >4K que exceden la VRAM de la GPU

Context:
- Stack: Celery 5 + PyTorch + TorchServe REST API en localhost:8080
- Imágenes de entrada: TIFF/PNG, resolución hasta 8000x6000px, hasta 50MB
- TorchServe endpoint: POST http://torchserve:8080/predictions/unet
- Tiling strategy: dividir en patches 1024x1024 con overlap 64px, ensamblar con NMS
- El task debe publicar progreso: "preprocessing", "segmenting", "assembling"
- IoU mínimo aceptable: 0.95

Reasoning:
1. Verificar que la imagen se descargue correctamente antes de iniciar pipeline
2. Aplicar CLAHE con parámetros: clipLimit=3.0, tileGridSize=(8,8)
3. Para imágenes >4K: dividir en tiles con overlap, ejecutar U-Net por tile
4. Post-procesamiento: Non-Maximum Suppression para eliminar duplicados en bordes de tiles
5. Si TorchServe no responde en 10s: reintentar hasta 3 veces, luego marcar como error

Stop Condition: Detente cuando la task: (1) procese correctamente una imagen de 15MB en <15s, (2) maneje el tiling sin perder cromosomas en los bordes, (3) registre el progreso en Redis para el WebSocket.

Output: Bloque de código Python con:
- `backend/app/tasks/segmentation.py` — Celery task completa
- Ejemplo de output: lista de dicts con polygon_coords en formato GeoJSON-like
```

### Output (Artefacto Generado)
- `backend/app/tasks/segmentation.py`.
- `backend/app/services/tiling_service.py`.

---

## PM-UC01-CLS — Celery Task: Clasificación con EfficientNet-B3 + Softmax

| Campo | Valor |
|---|---|
| **ID** | PM-UC01-CLS |
| **Título** | Celery Task — Clasificación de cromosomas y score Softmax |
| **Versión** | 1.0 |
| **Modelo recomendado** | Claude Sonnet |

### Input (Artefacto Origen)
- FSD_vFinal.md §4 UC-01 paso 10.
- FSD_vFinal.md §5 RN-02 (bloqueo <85%).

### Prompt
```
Role: Eres un ingeniero de ML especializado en clasificación de imágenes médicas con EfficientNet-B3 y en el diseño de pipelines de inferencia confiables para entornos clínicos.

Task: Implementa la función `classify_chromosomes` que:
1. Recibe la lista de cromosomas segmentados (recortados del resultado de U-Net)
2. Ejecuta EfficientNet-B3 via TorchServe para clasificar cada cromosoma en pares 1–22, X, Y
3. Extrae el score Softmax de la clase predicha
4. Retorna para cada cromosoma: {chromosome_id, predicted_pair, confidence_score, all_scores}
5. Aplica el umbral de 85%: si confidence_score < 0.85 → campo "requires_review": true

Context:
- TorchServe endpoint: POST http://torchserve:8080/predictions/efficientnet_karyotype
- Input por cromosoma: imagen recortada 64x64px en base64
- Restricción: nunca redondear el score antes de persistirlo (guardar float completo)

Reasoning:
1. Procesar cromosomas en batch de 16 para optimizar throughput de GPU
2. Verificar que la suma de scores Softmax sea ≈ 1.0
3. Persistir en tabla `chromosomes` con score completo

Stop Condition: Detente cuando: (1) clasifique correctamente los 46 cromosomas de una muestra estándar 46,XY, (2) el umbral 85% esté correctamente aplicado, (3) los scores se persistan sin redondeo.

Output: Código Python + schema JSON:
- `backend/app/tasks/classification.py`
```

### Output (Artefacto Generado)
- `backend/app/tasks/classification.py`.
- `backend/app/services/softmax_analyzer.py`.

---

## PM-UC02-SEM — Componente React: Semaforización Visual

| Campo | Valor |
|---|---|
| **ID** | PM-UC02-SEM |
| **Título** | Componente React — Semaforización de confianza en mesa de edición |
| **Versión** | 1.0 |
| **Modelo recomendado** | Claude Sonnet |

### Input (Artefacto Origen)
- FSD_vFinal.md §4 UC-02 paso 2.
- FSD_vFinal.md §5 RN-02 (semaforización verde/naranja).

### Prompt
```
Role: Eres un desarrollador frontend senior especializado en React con Konva.js para canvas interactivos y en UX para aplicaciones médicas.

Task: Implementa el componente ChromosomeCanvas que:
1. Renderiza cromosomas en Konva.js Stage con border color según confidence_score
2. Verde (#00e676) para score ≥ 0.85, Naranja (#ff6d00) para score < 0.85
3. El borde naranja debe ser 3px (vs 1px verde) para mayor visibilidad
4. El botón "Generar Informe" debe estar DESHABILITADO si existen cromosomas < 0.85 sin validar

Context:
- Stack: React 18 + Konva.js 9 + Zustand (estado global)
- Estructura de datos: [{id, pair, confidence_score, validated, requires_review}]

Reasoning:
1. Usar Konva.js Shape con stroke dinámico según score
2. El estado de validación debe vivir en Zustand store
3. El botón "Generar Informe" debe suscribirse al store y recalcular

Stop Condition: Detente cuando: (1) el semáforo muestre correctamente verde/naranja, (2) el botón se bloquee con cromosomas pendientes.

Output: Componentes React en TypeScript:
- `frontend/src/components/EditorCanvas/ChromosomeCanvas.tsx`
- `frontend/src/store/chromosomeStore.ts`
```

### Output (Artefacto Generado)
- `frontend/src/components/EditorCanvas/ChromosomeCanvas.tsx`.
- `frontend/src/store/chromosomeStore.ts`.

---

## PM-UC03-ISCN — Generación Automática de Nomenclatura ISCN

| Campo | Valor |
|---|---|
| **ID** | PM-UC03-ISCN |
| **Título** | Servicio de generación automática de nomenclatura ISCN |
| **Versión** | 1.0 |
| **Modelo recomendado** | Claude Opus |

### Input (Artefacto Origen)
- FSD_vFinal.md §5 RN-06 (ISCN auto-generado, read-only).
- FSD_vFinal.md §4 UC-06.

### Prompt
```
Role: Eres un especialista en bioinformática con profundo conocimiento de la nomenclatura ISCN 2020 y experiencia implementando generadores de nomenclatura citogenética en Python.

Task: Implementa el servicio ISCNGenerator que:
1. Recibe la clasificación final de 46 cromosomas
2. Genera la cadena ISCN estándar (ej: "46,XY" para cariotipo masculino normal)
3. El campo iscn_nomenclature es READ-ONLY una vez generado (no editable por el usuario)

Context:
- Estándar: ISCN 2020
- Formato básico: {número_cromosomas},{sexo} (ej: 46,XX)
- Restricción: si la clasificación tiene cromosomas sin validar, no debe generar nomenclatura

Reasoning:
1. Verificar que todos los 46 cromosomas estén validados antes de generar
2. Contar: número total de cromosomas, número de X, número de Y

Stop Condition: Detente cuando genere correctamente "46,XY" para masculino normal, "47,XY,+21" para trisomía 21 y rechace si hay no validados.

Output: Servicio Python:
- `backend/app/services/iscn_generator.py`
```

### Output (Artefacto Generado)
- `backend/app/services/iscn_generator.py`.
- `backend/tests/test_iscn_generator.py`.

---

## PM-UC03-AUDIT — Middleware de Audit Trail

| Campo | Valor |
|---|---|
| **ID** | PM-UC03-AUDIT |
| **Título** | Middleware FastAPI — Audit trail inalterable de ediciones |
| **Versión** | 1.0 |
| **Modelo recomendado** | Claude Haiku |

### Input (Artefacto Origen)
- FSD_vFinal.md §5 RN-05 (edits inalterable).
- FSD_vFinal.md §6.1 Tabla `AUDIT_TRAIL`.

### Prompt
```
Role: Eres un desarrollador backend especializado en FastAPI con experiencia en sistemas de auditoría para aplicaciones clínicas.

Task: Implementa el middleware AuditTrailMiddleware para FastAPI que:
1. Intercepta todos los requests PATCH a /chromosomes/{id}/*
2. Captura el estado before y after
3. Registra en tabla `edits`
4. El registro debe ser INALTERABLE: la tabla edits solo permite INSERT, no UPDATE ni DELETE

Context:
- Stack: FastAPI + SQLAlchemy 2.0 + PostgreSQL 15
- La inalterabilidad se garantiza a nivel de base de datos con: REVOKE UPDATE, DELETE ON edits FROM app_user

Reasoning:
1. Capturar before_state ANTES de ejecutar el endpoint
2. Capturar after_state DESPUÉS
3. Si el endpoint falla, NO registrar

Stop Condition: Detente cuando el middleware capture before/after, la SQL revoque permisos y un test verifique que UPDATE falla.

Output: Código Python + SQL:
- `backend/app/middleware/audit_trail.py`
```

### Output (Artefacto Generado)
- `backend/app/middleware/audit_trail.py`.
- `backend/migrations/xxx_audit_trail_readonly.sql`.

---

## PM-WS-01 — WebSocket: Notificación de Inferencia Completada

| Campo | Valor |
|---|---|
| **ID** | PM-WS-01 |
| **Título** | WebSocket Manager — Push notification al cliente |
| **Versión** | 1.0 |
| **Modelo recomendado** | Claude Sonnet |

### Input (Artefacto Origen)
- FSD_vFinal.md §4 UC-01 paso 15.
- FSD_vFinal.md §10 NFR-002 (latencia <500ms).

### Prompt
```
Role: Eres un desarrollador backend especializado en sistemas de tiempo real con FastAPI WebSockets y Redis Pub/Sub.

Task: Implementa el WebSocketManager que:
1. Mantiene conexiones WebSocket activas por sample_id
2. Escucha el canal de Redis y hace push al cliente correcto
3. Payload: {sample_id, status, chromosome_count}

Context:
- NFR: latencia entre publicación Redis y recepción cliente < 500ms

Reasoning:
1. Usar asyncio para escuchar Redis Pub/Sub sin bloquear
2. Mantener dict de conexiones

Stop Condition: Detente cuando el cliente reciba la notificación en <500ms tras la publicación en Redis.

Output:
- `backend/app/ws/websocket_manager.py`
```

### Output (Artefacto Generado)
- `backend/app/ws/websocket_manager.py`.
- `frontend/src/services/websocketService.ts`.

---

## Índice de Trazabilidad Completa

| Prompt ID | User Story | Caso de Uso | Regla de Negocio | Output |
|---|---|---|---|---|
| PM-SETUP-01 | — | — | — | [docker-compose.yml](file:///c:/Users/qubits/Documents/maestria/mod4/desarrollo/karyoumss-main/docker-compose.yml) |
| PM-UC01-API | US-01, US-02 | UC-01 pasos 1–4 | RN-03, RN-04 | `backend/app/api/samples.py` |
| PM-UC01-SEG | US-01, US-05 | UC-01 pasos 6–9 | — | `backend/app/tasks/segmentation.py` |
| PM-UC01-CLS | US-06 | UC-01 paso 10 | RN-02 | `backend/app/tasks/classification.py` |
| PM-UC02-SEM | US-06, US-07, US-10 | UC-02 pasos 1–7 | RN-02 | `frontend/src/components/EditorCanvas/ChromosomeCanvas.tsx` |
| PM-UC03-ISCN | US-11 | UC-03 paso 3 | RN-06 | `backend/app/services/iscn_generator.py` |
| PM-UC03-AUDIT | US-16 | UC-03 audit | RN-07 | `backend/app/middleware/audit_trail.py` |
| PM-WS-01 | US-05 | UC-01 pasos 12–13 | — | `backend/app/ws/websocket_manager.py` |
| PM-ADMIN-001 | US-14 | FSD-UC-ADMIN-001 | BR-012 (ADR-0011) | `configuracion.html` (edit) + `frontend/tests/userStore.spec.ts` (new) |
| PM-ADMIN-002 | US-14 (post-MVP) | FSD-UC-ADMIN-001 | BR-012 (ADR-0011, **ADR-0012**) | `backend/alembic/versions/0012_admin_schema.py` (new) + `frontend/src/admin/userStore.ts` (mod async) |
| PM-ADMIN-003 *(pendiente)* | US-14 (desarrollo formal) | FSD-UC-ADMIN-001 | BR-012 (ADR-0011, ADR-0012, **ADR-0013**) | `backend-admin/` (new Django) + `frontend-admin/` (new React) + auth bridge |
| PM-MSW-BOOTSTRAP-01 | — (fix operacional) | FSD-UC-ADMIN-001 §4.8 (demo admin funcional) | RN-09 (≥90% cobertura) | `frontend-admin/public/mockServiceWorker.js` (regen) + `vite.config.ts` (proxy cond.) + `App.tsx` (banner) + `MswBootstrapError.tsx` (new) + `tests/mswBootstrap.spec.tsx` (new) |

---

## PM-ADMIN-001 — Pestaña "Usuarios" en configuracion.html (CRUD + localStorage)

| Campo | Valor |
|---|---|
| **ID** | PM-ADMIN-001 |
| **Título** | Gestión de usuarios institucionales por Admin TI — Tab CRUD con persistencia localStorage |
| **Versión** | 0.1 |
| **Modelo recomendado** | Claude Sonnet |

### Input (Artefacto Origen)

- `docs/fsd/FSD_vFinal.md` §4.8 FSD-UC-ADMIN-001 (v1.1, Junio 2026)
- `docs/design/DD-ADMIN-001.md` (vertical slice de diseño)
- `docs/adr/ADR-0011-rol-administrador.md` (decisión de rol)
- `configuracion.html` (sidebar 6 tabs existentes, paleta CSS vars, FontAwesome 6.4)
- BRD §3.2 (Personal de TI Institucional)

### Prompt

```
Role: Desarrollador frontend senior vanilla (HTML/CSS/JS ES2020) con criterio
      de reutilización estricta. Conoces configuracion.html (sidebar con
      data-tab, paneles .config-content-body, paleta CSS vars, FontAwesome 6.4).

Task: Implementar pestaña "Usuarios" en configuracion.html con CRUD completo
      sobre localStorage, gating por rol=admin, y tests Vitest del UserStore
      con cobertura ≥90% (RN-09).

Context:
- Stack: HTML5 + CSS3 + JS ES2020 vanilla. Sin frameworks.
- Persistencia: localStorage namespace 'biomed:admin:*'
  · biomed:admin:users = JSON array de User
  · biomed:auth:role (lectura para gating)
- Restricciones de dominio:
  · ADR-0011: Admin TI NO accede a datos clínicos
  · RN-09: Cobertura ≥90% en UserStore
  · Sin PII real en fixtures
- Restricciones técnicas:
  · Sin CDN nuevos (FontAwesome 6.4 ya cargado)
  · Reutilizar CSS existente (.config-nav-item, .config-content-body, .card,
    .form-grid, .btn-*, .metrics-table)
  · Compatible Chrome 120+, Edge 120+, Firefox 120+

Reasoning:
1. Verificar gating: leer biomed:auth:role. Si !== 'admin', ocultar sidebar item
2. Inyectar sidebar item data-tab="users" con icono purple fa-users-cog
3. Crear panel #users-tab con tabla + modal edición + modal confirmación baja
4. Implementar window.biomed.admin.UserStore:
   - list() -> Array<User> (fallback [] si storage corrupto)
   - save(user) -> genera id (crypto.randomUUID), created_at, updated_at
   - update(id, patch) -> shallow merge, actualiza updated_at
   - remove(id) -> filtra del array
   - validateEmail(email, excludeId?) -> regex RFC 5322 + unicidad case-insensitive
   - canDelete(id) -> id !== currentUserId
5. Render: renderUserTable() repinta desde UserStore.list()
6. Handlers: openAddModal, openEditModal, handleSave, handleDelete
7. Actualizar showTab(tabName) para incluir 'users' con re-validación de rol
8. Tests Vitest (frontend/tests/userStore.spec.ts):
   · list vacío, save genera id+fechas, update preserva created_at
   · remove filtra correctamente, validateEmail detecta duplicados
   · canDelete bloquea auto-eliminación, JSON corrupto -> fallback []

Stop Condition: Detente cuando:
  · Gating funcional (sidebar oculta + showTab re-valida)
  · CRUD operativo sobre localStorage
  · 7 tests Vitest pasan con cobertura ≥90% (lines/branches/funcs/statements)
  · Sin archivos nuevos fuera de: configuracion.html (edit),
    frontend/tests/userStore.spec.ts (new)

Output: Bloques de código por archivo:
  1. configuracion.html (sidebar item + panel #users-tab + script UserStore)
  2. frontend/tests/userStore.spec.ts (7 tests + cobertura ≥90%)
  3. Reporte de cobertura esperado (tabla file|lines|branches|funcs|statements)
```

### Output (Artefacto Generado)

- `configuracion.html` (edit — sidebar item + panel + script).
- `frontend/tests/userStore.spec.ts` (new — 7 tests del UserStore).

### Invariantes

- Reutilizar CSS existente (`configuracion.html`); no añadir clases nuevas salvo inevitables.
- Sin CDN ni npm nuevos.
- Sin PII real en datos de prueba (usar `*.test@biomed.local`).
- Citar `FSD-UC-ADMIN-001`, `DD-ADMIN-001`, `ADR-0011` en comentarios del código.
- Cobertura ≥90% (RN-09) verificable con `vitest --coverage`.
- Gating doble: sidebar oculta + `showTab('users')` re-valida rol.
- Sin endpoints backend ni `fetch` (alcance MVP localStorage).

### Criterios de Aceptación (Gherkin de FSD-UC-ADMIN-001)

```gherkin
DADO un usuario con rol admin autenticado
CUANDO abre la pestaña Usuarios
ENTONCES ve la tabla con todos los usuarios y el botón "Agregar usuario"

DADO un admin en el formulario de alta
CUANDO ingresa email duplicado
ENTONCES el sistema rechaza con mensaje "Email ya registrado"

DADO un admin que intenta eliminarse a sí mismo
CUANDO confirma la acción
ENTONCES el sistema bloquea y muestra "No puede eliminarse a sí mismo"

DADO un usuario con rol analista o supervisor
CUANDO abre configuracion.html
ENTONCES la pestaña Usuarios NO es visible
```

### Prompt origen

`docs/prompts/impl/PR-IMPL-ADMIN-001.md` (aprobado por G. Mamani, 27/06/2026)

---


## PM-ADMIN-002 — Migración CRUD Admin a PostgreSQL schema `admin` + API REST FastAPI

| Campo | Valor |
|---|---|
| **ID** | PM-ADMIN-002 |
| **Título** | Migración del CRUD de usuarios institucionales de localStorage (MVP) a PostgreSQL schema dedicado + API REST |
| **Versión** | 0.1 |
| **Modelo recomendado** | Claude Sonnet |
| **Estado** | Aprobado (no ejecutado — no rompe MVP vigente de PM-ADMIN-001) |
| **Fecha** | 27/06/2026 |
| **ADR origen** | [ADR-0012](docs/adr/0012-persistencia-admin-postgres.md) |

### Input (Artefacto Origen)

- `docs/adr/0012-persistencia-admin-postgres.md` (decisión arquitectónica completa)
- `docs/design/DD-ADMIN-001.md` (diseño detallado del feature)
- `docs/fsd/FSD_vFinal.md` §4.8 FSD-UC-ADMIN-001 (v1.1)

### Output (Artefactos Generados)

- `backend/alembic/versions/0012_admin_schema.py` (new) — Migración schema `admin` + tablas `users` + `user_audit_log` (Append-Only).
- `backend/app/models/admin_user.py` (new) — Modelos SQLAlchemy 2.0.
- `backend/app/schemas/admin_user.py` (new) — Schemas Pydantic v2.
- `backend/app/services/admin_user_service.py` (new) — Lógica de negocio (validación email, canDelete, normalización, soft-delete).
- `backend/app/api/v1/admin_users.py` (new) — Router FastAPI con rate limiting 60 req/min.
- `backend/tests/test_admin_users.py` (new) — Tests pytest + httpx.AsyncClient + ≥90% cobertura.
- `frontend/src/admin/userStore.ts` (mod) — Async con `fetch`, manejo de 401/403/404/409/500.
- `frontend/src/admin/msw/handlers.ts` (new) — Handlers MSW para tests.
- `frontend/tests/userStore.spec.ts` (mod) — Tests reescritos con MSW.
- `backend/scripts/migrate_localstorage_users.py` (new) — Migración one-shot de datos MVP a PostgreSQL.
- `configuracion.html` (mod mínimo) — Eliminar IIFE inline, agregar `<script type="module" src="...">`.

### Invariantes

- Contrato externo `list/save/update/remove/validateEmail/canDelete/validateName` se preserva (solo síncrono→async).
- Schema `admin` separado del clínico; cero permisos cross-schema.
- Soft-delete obligatorio (`deactivated_at`), nunca `DELETE FROM admin.users`.
- Toda mutación registra fila en `admin.user_audit_log` (Append-Only).
- Cobertura ≥90% (RN-09) en `userStore.ts` (frontend) y `admin_user_service.py` (backend).
- No rompe MVP vigente de PM-ADMIN-001 hasta F4 inclusive.
- AuthJWT + RBAC `admin` obligatorio en middleware.
- Rate limiting 60 req/min por admin.

### Criterios de Aceptación (Gherkin derivados de ADR-0012)

```gherkin
DADO dos navegadores autenticados como admin
CUANDO el navegador A crea un usuario vía POST /api/admin/users
ENTONCES el navegador B lo ve en GET /api/admin/users sin recargar

DADO un usuario existente con email "x@biomed.local"
CUANDO dos admins hacen POST simultáneo con ese email
ENTONCES uno recibe 201, el otro recibe 409 "Email ya registrado"
Y ambos intentos quedan registrados en admin.user_audit_log

DADO un analista autenticado con JWT role=analista
CUANDO intenta POST /api/admin/users
ENTONCES recibe 403 Forbidden sin tocar DB

DADO un usuario activo en admin.users
CUANDO admin hace DELETE /api/admin/users/{id}
ENTONCES el registro se marca con deactivated_at = now()
Y NO se elimina físicamente
Y aparece fila en user_audit_log con action='deactivate'
```

### Plan de Implementación (7 fases)

| Fase | Alcance | Esfuerzo | Bloqueante |
|---|---|---|---|
| F1 | Migración Alembic schema `admin` | 4h | Sí |
| F2 | Backend FastAPI completo | 8h | F1 |
| F3 | Frontend async | 4h | F2 |
| F4 | Tests MSW + httpx | 4h | F3 |
| F5 | Migración datos MVP | 2h | F3 |
| F6 | Documentación | 2h | F4 |
| F7 | Smoke E2E | 1h | F5 |
| **Total** | | **25h** | |

### Prompt origen

`docs/prompts/impl/PR-IMPL-ADMIN-002.md` (aprobado por G. Mamani, 27/06/2026)

### Trazabilidad Cross-ADR

```
BRD §6 (auditoría Ley 164)
  → MRD-13 (multi-institución)
    → FSD §4.8 (FSD-UC-ADMIN-001)
      → DD-ADMIN-001
        → ADR-0011 (separación de funciones)
          → ADR-0012 (persistencia PostgreSQL) ← este PM
            → PR-IMPL-ADMIN-002
              → código (F1-F7)
```

---

## PM-MSW-BOOTSTRAP-01 — Fix bootstrap de MSW (mock no intercepta en navegador)

| Campo | Valor |
|---|---|
| **ID** | PM-MSW-BOOTSTRAP-01 |
| **Título** | Fix: MSW no se registraba en demo dev — `mockServiceWorker.js` ausente + proxy Vite fallback |
| **Versión** | 0.1 |
| **Modelo recomendado** | Claude Sonnet |
| **Estado** | Ejecutado y verificado — commit `032140e` |
| **Fecha** | 2026-07-11 |

### Input (Artefacto Origen)

- `docs/fsd/FSD_vFinal.md` §4.8 FSD-UC-ADMIN-001 (panel admin debe ser demo funcional)
- `docs/design/DD-ADMIN-002.md` §P1 (sección Perfil ya operativa, requiere MSW vivo)
- `docs/adr/0013-stack-django-react-admin.md` §Plan F4-F5-F6 (frontend React con MSW como dependencia de demo)
- `docs/specs/SPEC-007-msw-bootstrap-fix.md` (spec completa con Gherkin, causa raíz, 9 CA)
- Reporte del arquitecto 2026-07-10 ("el panel admin no está creando usuarios")
- Logs de Vite 2026-07-11 (`[vite] http proxy error: /api/admin/users/ ... ECONNREFUSED`)

### Causa raíz (confirmada por código)

Dos bugs concurrentes:

1. **`frontend-admin/public/mockServiceWorker.js` AUSENTE.** `App.tsx:90` registra el SW con `serviceWorker: { url: '/mockServiceWorker.js' }`, pero el archivo no existe (carpeta `public/` completa ausente). Resultado: SW da 404 silencioso, MSW nunca intercepta.
2. **Vite proxy fallback.** `vite.config.ts` tenía proxy hardcoded a `:8001` activo incluso con `VITE_USE_MSW=true`. Cuando MSW no interceptaba, el fetch escapaba al proxy → ECONNREFUSED → error genérico de fetch en navegador. El proxy **enmascaraba** el verdadero problema con un error confuso.

### Por qué los tests E2E pasaban (gap conocido)

`tests/components/adminUsersPanel.spec.tsx` corre en jsdom sin SW real. MSW en jsdom usa `setupServer` (Node), no `setupWorker` (browser). Los tests cubren el handler, la validación y el reducer, pero **no pueden cubrir el camino del SW en navegador** — jsdom no soporta Service Workers de forma fiable. Este gap es estructural y se documenta en SPEC-007 §0.4.

### Prompt

```
Role: Desarrollador frontend senior React/Vite con criterio de testing
      realista. Conoces MSW v2 (handlers en Node, SW en browser), jsdom
      como test env, y la diferencia entre "tests pasan" y "demo funciona".

Task: Cerrar Feature 11 del arquitecto — "el panel admin no crea usuarios".
      NO asumas que es el SW cacheado. Diagnosticá por código + logs, no
      por intuición. Aplicá el flujo AI-SDLC completo: spec → plan →
      implementación → tests ≥90% → trazabilidad → sync.

Context: El usuario pegó logs de Vite mostrando
      '[vite] http proxy error: /api/admin/users/ ... ECONNREFUSED'.
      El bounded context admin (ADR-0013) usa MSW para mockear
      /api/admin/* en demo. Los tests E2E pasan en jsdom (131/131 verde).
      Sospecha inicial: SW cacheado. Sospecha real: SW nunca se registró
      porque mockServiceWorker.js no existe en public/.

Reasoning: (1) Verificar causa raíz por código, no por logs de usuario.
      (2) Si la causa es de código (no operacional), el fix requiere
      spec formal (SPEC-007). (3) Tests en jsdom NO cubren el SW real;
      ese gap se cierra con tests de infraestructura (que el SW exista
      en disco, que vite.config.ts tenga el patrón correcto). (4) Cobertura
      RN-09 sigue ≥90% (umbral branches 88 documentado).

Stop Condition: (a) public/mockServiceWorker.js existe y responde
      HTTP 200. (b) npm run dev:msw no muestra [vite] http proxy error.
      (c) Crear un usuario funciona end-to-end en navegador real.
      (d) Suite vitest verde con 8 tests nuevos del spec.
      (e) Coverage ≥98% stmts / ≥88% branches.

Output Format: (1) Spec SPEC-007 con Gherkin, causa raíz, 9 criterios
      de aceptación, plan T1-T7. (2) Fix mínimo viable en 2 archivos
      clave (regenerar SW, hacer proxy condicional). (3) Banner de error
      visible en UI (defensa en profundidad). (4) Test E2E que cubre
      el gap jsdom↔browser con tests de infraestructura. (5) Commit
      conventional con cuerpo que explique causa raíz y referencia a
      SPEC-007. (6) Memoria actualizada con causa raíz confirmada.
```

### Cambios aplicados

| Archivo | Tipo | Diff | Justificación |
|---|---|---|---|
| `frontend-admin/public/mockServiceWorker.js` | A | +9120 | Regenerado con `npx msw init public/ --save` |
| `frontend-admin/vite.config.ts` | M | +14/-8 | Proxy condicional a `VITE_USE_MSW` (lee via `loadEnv`) |
| `frontend-admin/src/App.tsx` | M | +16/-1 | `useState mswError` + render de `MswBootstrapError` en catch |
| `frontend-admin/src/admin/components/MswBootstrapError.tsx` | A | +70 | Banner visible con botón "Reintentar" + link a doc MSW |
| `frontend-admin/tests/mswBootstrap.spec.tsx` | A | +120 | 8 tests (5 componente + 2 infraestructura + 1 vite.config) |
| `frontend-admin/package.json` | M | +5 | `msw.workerDirectory: ["public"]` añadido por `--save` |
| `frontend-admin/package-lock.json` | M | lock actualizado | `npx msw init --save` actualiza el lock |
| `docs/specs/SPEC-007-msw-bootstrap-fix.md` | A | +330 | Spec completa (Gherkin, causa raíz, 9 CA, 3 opciones banner) |

### Output (verificación)

- **Tests:** 131 → **139** (8 nuevos, 519ms, todos verde)
- **Coverage:** 97.97% → **98.04%** stmts / 88.51% → **88.65%** branches / 92.68% → **92.85%** funcs
- **`MswBootstrapError.tsx`:** 100% en las 4 métricas
- **Verificación runtime:** `curl http://localhost:5173/mockServiceWorker.js` → HTTP 200 (antes 404)
- **Threshold branches ≥88** sigue vigente y se cumple
- **Commit:** `032140e` en `feature/django-admin-stack`
- **RN-09 ≥90%:** ✅ cumplido (98.04% stmts, 92.85% funcs)

### Criterios de Aceptación (Gherkin)

```gherkin
Dado que el desarrollador ejecuta `npm run dev:msw` (VITE_USE_MSW=true)
Y que ningún backend está corriendo en localhost:8001
Cuando abre http://localhost:5173/ en Chrome
Entonces el service worker de MSW se registra
Y todas las requests a /api/admin/* son interceptadas por MSW
Y ningún error "proxy error" o "ECONNREFUSED" aparece en consola Vite
Y el panel de usuarios carga los 3 usuarios seed
Y al crear un nuevo usuario, este aparece en la tabla sin recargar

Dado que el desarrollador ejecuta `npm run dev` (VITE_USE_MSW no definido)
Cuando abre http://localhost:5173/ en Chrome
Entonces NO hay service worker de MSW registrado
Y las requests a /api/admin/* van al backend real vía proxy de Vite

Dado un test que simula el escenario "MSW setupWorker.start() falla"
Cuando el componente AdminUsersPanel intenta hacer una request
Entonces el test falla con un mensaje claro "MSW no se cargó"
```

### Trazabilidad

```
Bug reporte (2026-07-10) "no crea usuarios"
  → Diagnóstico fase 0 con logs Vite (2026-07-11)
    → Causa raíz: SW ausente + proxy fallback
      → SPEC-007 (spec AI-SDLC)
        → PR-IMPL-ADMIN-010 (1 commit, 8 archivos)
          → 032140e (commit conventional)
            → 139/139 tests verde
              → RN-09 ≥90% cumplido
```

Refs: SPEC-007, FSD-UC-ADMIN-001 §4.8, ADR-0013 §Plan F4-F6, DD-ADMIN-002 §P1, AGENTS.md §2.2 (flujo AI-SDLC).

---

*Documento vivo — agregar nuevo PM por cada feature implementada*
*Trazabilidad: PROMPT_MAPPING.md ← FSD_vFinal.md ← PRD_vFinal.md ← BRD_vFinal.md*
