# 📋 Plan de Implementación: FSD-UC-001 — Procesamiento Asíncrono de Muestra

## 🎯 Contexto
El objetivo es implementar el flujo completo de ingesta y procesamiento de muestras citogenéticas. Este es el corazón del sistema BIOMED UMSS, transformando una imagen de metafase en un set de 46 cromosomas clasificados. La implementación debe garantizar el cumplimiento estricto de la **RN-03 (Anonimización)** y la arquitectura asíncrona definida en el **DTI**.

## 🏗️ Estrategia de Implementación

El desarrollo se dividirá en cuatro ejes paralelizables, siguiendo el principio de "Infrastructure First" para habilitar la integración continua.

### 1. 🛠️ Infraestructura (Foundational)
Tareas enfocadas en habilitar el entorno de ejecución y los servicios de soporte.
- **INF-01: Setup Docker Compose Core**: Configuración de contenedores para PostgreSQL 15, Redis 7 y MinIO (S3 compatible).
- **INF-02: TorchServe Deployment**: Despliegue de TorchServe en GPU con los modelos base (U-Net y EfficientNet-B3) cargados.
- **INF-03: Project Scaffold**: Estructura de directorios FastAPI (Hexagonal) y configuración de Celery workers.

### 2. 🧠 ML Pipeline (AI Engine)
Implementación de la lógica de Computer Vision, desde la imagen cruda hasta los scores.
- **ML-01: CLAHE Pre-processing**: Implementación de normalización de contraste (`clipLimit=3.0`, `tileGridSize=8x8`).
- **ML-02: Image Tiling Logic**: Implementación de división de imágenes $> 4\text{K}$ en tiles de $1024 \times 1024$ con overlap de $64\text{px}$ (Soporte ADR-0001).
- **ML-03: U-Net Segmentation Integration**: Cliente para TorchServe que consume tiles y retorna polígonos/bounding boxes.
- **ML-04: NMS (Non-Maximum Suppression)**: Lógica de ensamblado de tiles para eliminar redundancias en bordes.
- **ML-05: EfficientNet-B3 Classification**: Cliente para TorchServe que clasifica cromosomas y retorna el score Softmax $\in [0,1]$.
- **ML-06: Result Aggregator**: Lógica para consolidar los 46 cromosomas y asignar el flag `requires_review` si $\text{score} < 0.85$.

### 3. ⚙️ Backend (Orchestration)
Implementación de los endpoints, la lógica de negocio y la comunicación asíncrona.
- **BKE-01: Database Schema**: Implementación de tablas `samples` y `chromosomes` en PostgreSQL.
- **BKE-02: CHN Anonymizer Service**: Implementación de la lógica de generación y validación de códigos CHN (Cumplimiento RN-03).
- **BKE-03: S3 Storage Adapter**: Implementación de subida/bajada de imágenes usando rutas basadas en CHN.
- **BKE-04: Ingesta Endpoint**: `POST /samples/{id}/image` que valida formato, sube a S3 y encola tarea en Redis.
- **BKE-05: Async Pipeline Orchestrator**: Celery Worker que coordina el flujo: `S3 $\to$ CLAHE $\to$ Tiling $\to$ Segmentación $\to$ NMS $\to$ Clasificación $\to$ DB`.
- **BKE-06: WebSocket Event Publisher**: Implementación de notificaciones push `{sample_id, status: "ready"}` vía FastAPI WebSockets.
- **BKE-07: Persistencia de Resultados**: Lógica de inserción masiva de los 46 cromosomas con sus coordenadas y scores.

### 4. 🧪 Testing & Validation (Quality)
Verificación de invariantes clínicas y SLAs técnicos.
- **TST-01: Privacy Audit Test**: Verificación automatizada de que ninguna petición a TorchServe contiene PII (Validación RN-03).
- **TST-02: Pipeline Integration Test**: Ejecución de un flujo end-to-end desde el upload hasta la notificación WebSocket.
- **TST-03: SLA Performance Test**: Medición de latencia p95 para asegurar que la inferencia total sea $\le 15\text{s}$.
- **TST-04: HITL Threshold Test**: Validación de que cromosomas con $\text{score} = 0.84$ sean marcados como `requires_review`.

## 📌 Trazabilidad FSD
| Task ID | FSD-UC-001 Paso | Regla de Negocio |
| :--- | :--- | :--- |
| BKE-02 | 1 $\to$ 2 | RN-03 (Anonimización) |
| INF-02/ML-03 | 9 $\to$ 10 | NFR-01 (Inferencia < 15s) |
| ML-02 | 9 | ADR-0001 (Tiling) |
| ML-06 | 11 | HITL (Semaforización < 0.85) |
| BKE-06 | 12 | WebSocket Push |

## 🚀 Verificación Final
El flujo se considerará completo cuando:
1. Se suba una imagen TIFF de $8000 \times 6000\text{px}$.
2. El sistema genere 46 registros en la tabla `chromosomes`.
3. El Frontend reciba la notificación de "Borrador listo" en $\le 15\text{s}$.
4. Se confirme que el log de TorchServe solo contiene códigos CHN.
