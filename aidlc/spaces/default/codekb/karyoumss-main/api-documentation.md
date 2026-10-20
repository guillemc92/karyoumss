# Documentación de APIs — karyoumss-main

## backend-ml (FastAPI, :8000) — detalle

Sin autenticación ni rate limiting. FastAPI publica `/docs` y `/openapi.json` automáticamente. Los endpoints de inferencia son `def` (threadpool) y se ejecutan dentro de `limite.turno()`; `/health/` no pasa por el límite.

| Método y ruta | Entrada | Respuesta | Códigos | Pasa por el límite |
|---|---|---|---|---|
| `GET /health/` | — | `HealthOut {status, service, model_version, trained_model}` | 200 | No |
| `POST /api/v1/segment/` | multipart `file` | `SegmentResult {model_version, segmenter, classifier, image_width, image_height, chromosome_count, confidence_avg, chromosomes[ChromosomeOut{order, predicted_class, confidence_score, bbox{x,y,w,h}, area}]}` | 200, 400 (vacío), 422 (no es imagen), 503 (+`Retry-After`) | Sí |
| `POST /api/v1/xai/` | multipart `file` + form `x,y,w,h` (int) | `dict {heatmap_base64, activacion, modelo, metodo:'grad-cam', ref_h}` | 200, 400 (imagen o bbox inválidos), 503 (ocupado / sin modelo entrenado / Grad-CAM no disponible) | Sí |
| `POST /api/v1/classify/` | multipart `file` + form `x,y,w,h` (int) | `dict {predicted_class, confidence_score, modelo, entrenado, ref_h}` | 200, 400, 503 | Sí |

**Contrato de la contrapresión (503)**: `detail='backend-ml ocupado: hay demasiadas inferencias en curso'`, cabecera `Retry-After = max(1, ceil(ML_ESPERA_MAX_S))`.

**Configuración** (`.env.example`): `ML_MAX_INFERENCIAS` (int ≥ 1, por defecto 1), `ML_ESPERA_MAX_S` (float ≥ 0, por defecto 25), `ML_ASIGNACION_ENABLED` (booleano, por defecto apagado). Los valores inválidos hacen fallar el arranque con `ValueError`.

### Punto de extensión del intent

El intent añadirá `GET /api/v1/inferencias/` con `{maximo, en_curso, libres, espera_max_s}`, sin pasar por el semáforo. Hoy no existe ninguna ruta ni esquema con ese contrato. Los datos `maximo` y `espera_s` ya están en `LimiteInferencias`; `en_curso` no se registra (ver `component-inventory.md`).

## backend-clinic (DRF, :8002, prefijo `/api/clinic/`) — resumen

25 rutas: registro y CRUD de muestras, `process/`, `status/`, cariotipo y metafase, operaciones por cromosoma (`xai/`, `resolve/`, `anomaly/`, `reclassify/`, `split/`, `recrop/`, `join/`, `cross/`), `validate/`, `audit/`, `audit-review/` (+`decide/`), `sign/`, `narrative/`, `iscn/`, `pipeline/health/`, `tools/query/`, `agente/`. Permisos RBAC por opción (`HasOpcion`). `pipeline/health/` informa `{available, mode}` a partir del estado del circuit breaker, sin llamada de red.

### Consumo de backend-ml (`apps/samples/pipeline_client.py`)

`PipelineClient` con circuit breaker (umbral 3, enfriamiento 60 s, timeout base 2 s): `segment_image` → `/api/v1/segment/` (timeout ≥ 30 s), `xai_heatmap` → `/api/v1/xai/` (≥ 60 s), `classify_crop` → `/api/v1/classify/` (≥ 60 s). Cualquier error HTTP o timeout se convierte en `MLDegradedError` (RN-07). `trigger_processing`/`get_status` apuntan a `/api/v1/samples/{id}/process|status/`, que backend-ml no expone.

## backend-admin (DRF, :8001) — resumen

Rutas bajo `/api/admin/` (auditoría, configuración, perfil, 2FA, modelos, notificaciones, apariencia), `/api/auth/` (emisión de JWT, `exchange`) y `/api/internal/` (llamadas servicio a servicio desde backend-clinic). JWT de SimpleJWT, autoridad única (ADR-0017/0020).
