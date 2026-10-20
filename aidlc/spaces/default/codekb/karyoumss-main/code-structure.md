# Estructura del código — karyoumss-main

## Organización del monorepo

```
backend-ml/        FastAPI — motor de inferencia (análisis profundo)
backend-clinic/    Django — contexto clínico (apps/samples)
backend-admin/     Django — contexto administrativo (apps/users, audit, config)
frontend-clinic/   React + Vite + Konva — visor clínico
frontend-admin/    React + Vite — panel de administración
docs/              BRD/MRD/PRD/FSD, ADR-0001..0036, DD-*, auditorías, entregas
scripts/, pocs/    utilidades y pruebas de concepto (no productivas)
Caddyfile.dev      proxy de desarrollo :3000
```

## backend-ml (detalle)

| Archivo | Clasificación | Contenido |
|---|---|---|
| `app/main.py` | Controller | App FastAPI, global `limite`, 4 endpoints |
| `app/concurrencia.py` | Middleware/Utility | `LimiteInferencias` (semáforo + 503) |
| `app/schemas.py` | Model/DTO | Pydantic: `BBox`, `ChromosomeOut`, `SegmentResult`, `HealthOut` |
| `app/ports.py` | Model (interfaces) | `SegmenterPort`, `ClassifierPort` (ABC) |
| `app/pipeline.py` | Service | `OpenCVSegmenter`, `get_classifier()` (singleton + lock), `run_pipeline`, `crop_of` |
| `app/segmentation.py` | Service | `Detection`, `segment` (Otsu + watershed), `load_gray` |
| `app/classifier.py` | Service (adaptador) | `PlaceholderClassifier` |
| `app/efficientnet.py` | Service (adaptador) | `EfficientNetClassifier` (torch perezoso) |
| `app/preprocess.py` | Utility | `letterbox`, `reference_height` (fuente única del preprocesado) |
| `app/asignacion.py` | Service | `hungaro`, `repartir` (ADR-0033) |
| `app/gradcam.py` | Service | `heatmap_png`, `resumen_activacion`, `GradCamNoDisponible` |
| `models/` | Static/Asset | `classifier.pth` (v3), `classes.json`, `model_meta.json` |
| `tests/` | Test | 9 archivos, 65 pruebas |
| `training/` | Utility (offline) | extracción de etiquetas, evaluación, 3 notebooks de entrenamiento |

Grafo de imports interno (sin ciclos): `main → concurrencia, pipeline, schemas, segmentation` (y de forma perezosa `gradcam`, `preprocess`); `pipeline → classifier, ports, schemas, segmentation` (perezoso `efficientnet`); `efficientnet → asignacion, ports, preprocess, segmentation`; `classifier → ports, segmentation`; `ports → segmentation`; `gradcam → preprocess`.

## Patrones de código

- **Hexagonal**: puertos ABC más adaptadores intercambiables (ADR-0007).
- **Singleton perezoso con double-checked locking** (`pipeline.get_classifier`).
- **Context manager** para el turno de inferencia (`LimiteInferencias.turno`), que libera en `finally`.
- **Configuración por entorno** con valores por defecto validados (`LimiteInferencias.desde_entorno`, `ML_ASIGNACION_ENABLED`).
- **Imports perezosos** de torch, Grad-CAM y preprocesado para que el servicio arranque sin torch (RN-07).
- **Errores HTTP explícitos**: 400 (vacío/bbox), 422 (no es imagen), 503 (ocupado, sin modelo, Grad-CAM no disponible).
- Nombres en **español** (`limite`, `turno`, `espera_s`, `maximo`), docstrings largos con trazabilidad a ADR/DD/RN, `snake_case` y `from __future__ import annotations`.
- Pruebas: `TestClient` para el contrato, `httpx.AsyncClient` + `ASGITransport` para la concurrencia real en un solo event loop, `monkeypatch` sobre los globales `main.limite`, `main.run_pipeline` y `pipeline._classifier_singleton`.

## Otros servicios (nivel de directorio)

- backend-clinic: una sola app `apps/samples` con modelos, vistas DRF, servicios, clientes HTTP (`pipeline_client`, `admin_client`, `llm_client`), ISCN, RAG, agente y MCP; 54 archivos de prueba.
- backend-admin: apps `users`, `audit`, `config`.
- frontend-clinic: `src/clinic/`, `routes.tsx`; pruebas Vitest y Playwright (`tests/`, `specs/`).
- frontend-admin: `src/admin/`, `pages/`, `hooks/`.
