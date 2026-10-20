# Inventario de componentes — karyoumss-main

## Componentes de backend-ml (analizados en profundidad)

### API FastAPI de backend-ml
- **Ubicación**: `backend-ml/app/main.py`
- **Responsabilidad**: exponer `/health/`, `/api/v1/segment/`, `/api/v1/xai/` y `/api/v1/classify/`; validar la entrada (400/422); envolver la inferencia en `limite.turno()`.
- **Depende de**: LimiteInferencias, Pipeline de inferencia, Esquemas Pydantic, OpenCVSegmenter, Grad-CAM, Preprocesado letterbox.
- **Estado**: global de módulo `limite = LimiteInferencias.desde_entorno()` (línea 30), sustituible en pruebas.

### LimiteInferencias
- **Ubicación**: `backend-ml/app/concurrencia.py`
- **Responsabilidad**: limitar las inferencias simultáneas con `threading.BoundedSemaphore(maximo)`; `turno()` adquiere con `timeout=espera_s` o lanza `HTTPException(503, Retry-After)`, y libera en `finally`.
- **API pública**: `maximo: int`, `espera_s: float`, `desde_entorno()`, `turno()`.
- **Hueco relevante para el intent**: no hay contador de inferencias en curso ni método de lectura del estado; el semáforo es privado (`_semaforo`).
- **Depende de**: `fastapi.HTTPException`, `threading`, `os`.

### Pipeline de inferencia
- **Ubicación**: `backend-ml/app/pipeline.py`
- **Responsabilidad**: `run_pipeline` (segmentar → clasificar → `SegmentResult`); `get_classifier()` como singleton perezoso con lock (EfficientNet, o Placeholder si falla).
- **Depende de**: OpenCVSegmenter, EfficientNetClassifier, PlaceholderClassifier, Esquemas Pydantic.

### OpenCVSegmenter
- **Ubicación**: `backend-ml/app/segmentation.py` (función `segment`, `Detection`, `load_gray`) y su adaptador en `pipeline.py`
- **Responsabilidad**: segmentación clásica Otsu + morfología + watershed. Techo medido: MAE 3,8 cromosomas; el error dominante es la sub-segmentación de cúmulos.

### EfficientNetClassifier
- **Ubicación**: `backend-ml/app/efficientnet.py`
- **Responsabilidad**: cargar `models/classifier.pth` (v3, macro-F1 0,6958) y clasificar en lote con letterbox; reparto global opcional (`ML_ASIGNACION_ENABLED`).
- **Depende de**: torch, torchvision, PIL, Preprocesado letterbox, Reparto global.

### PlaceholderClassifier
- **Ubicación**: `backend-ml/app/classifier.py`
- **Responsabilidad**: respaldo honesto (RN-07): clase por rango de área y confianza fija de 0,55 (todo naranja).

### Preprocesado letterbox
- **Ubicación**: `backend-ml/app/preprocess.py`
- **Responsabilidad**: fuente única del preprocesado (entrenamiento e inferencia); conserva el aspecto y la escala relativa a `ref_h`.

### Reparto global
- **Ubicación**: `backend-ml/app/asignacion.py`
- **Responsabilidad**: asignación húngara con cupos blandos de 2 copias por autosoma (ADR-0033).

### Grad-CAM
- **Ubicación**: `backend-ml/app/gradcam.py`
- **Responsabilidad**: mapa de calor real sobre `features[-1]` de EfficientNet y resumen de activación; `GradCamNoDisponible` si no se puede calcular.

### Esquemas Pydantic
- **Ubicación**: `backend-ml/app/schemas.py`
- **Responsabilidad**: contratos `BBox`, `ChromosomeOut`, `SegmentResult`, `HealthOut`.

### PipelineClient
- **Ubicación**: `backend-clinic/apps/samples/pipeline_client.py`
- **Responsabilidad**: cliente HTTP de backend-clinic hacia backend-ml con circuit breaker; traduce los fallos a `MLDegradedError` (RN-07).

## Otros componentes (solo a nivel de directorio)

### backend-clinic
- `apps/samples`: muestras, cariotipo, auditoría encadenada (ADR-0022), ISCN (ADR-0025), LLM/RAG/agente (ADR-0024/0027–0032). Depende de backend-ml, backend-admin y Ollama.

### backend-admin
- `apps/users`, `apps/audit`, `apps/config`: identidad, RBAC, JWT, 2FA, configuración.

### frontend-clinic
- SPA del analista/supervisor; cariograma Konva; consume `/api/clinic/`.

### frontend-admin
- SPA del administrador; consume `/api/admin/` y `/api/auth/`.

### backend-ml training
- `backend-ml/training/`: scripts offline de etiquetado (MetaClass), evaluación y entrenamiento; no se despliega.
