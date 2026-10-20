# Dependencias — karyoumss-main

## Dependencias internas entre servicios

| Origen | Destino | Mecanismo | Configuración |
|---|---|---|---|
| backend-clinic | backend-ml | HTTP multipart (`PipelineClient`) con circuit breaker | `CLINIC_FASTAPI_URL` (por defecto `http://localhost:8000`), `CLINIC_FASTAPI_TIMEOUT`=2.0, `CLINIC_FASTAPI_CIRCUIT_THRESHOLD`=3, `CLINIC_FASTAPI_CIRCUIT_COOLDOWN`=60 |
| backend-clinic | backend-admin | HTTP interno (`admin_client`, `auth_bridge`) | `ADMIN_INTERNAL_URL` (por defecto `http://localhost:8001`) |
| backend-clinic | Ollama | API compatible con OpenAI (local, sin egreso, RN-03) | variables `CLINIC_LLM_*` |
| frontend-clinic | backend-clinic | REST `/api/clinic/` (vía Caddy :3000) | — |
| frontend-admin | backend-admin | REST `/api/admin/`, `/api/auth/` | — |

**Acoplamiento con backend-ml**: el único consumidor es `PipelineClient`. Depende de las rutas `/api/v1/segment|xai|classify/`, del esquema `SegmentResult` y del código 503 (lo trata como degradación). Un endpoint GET nuevo y aditivo en backend-ml no rompe este contrato. backend-clinic no consulta `/health/` de backend-ml: su `pipeline/health/` solo mira el circuit breaker.

## Dependencias internas de backend-ml (módulos)

Ver el grafo en `code-structure.md`. Puntos que importan para el intent: `main.py` importa `LimiteInferencias` de `concurrencia.py` y crea el global `limite`; `concurrencia.py` solo depende de la biblioteca estándar y de `fastapi.HTTPException`. Las pruebas `tests/test_concurrencia.py` y `tests/test_api_inferencia.py` sustituyen `main.limite`, `main.run_pipeline` y `pipeline._classifier_singleton`.

## Dependencias externas

Las versiones están en `technology-stack.md`. Observaciones:
- backend-ml fija solo cotas inferiores (`>=`), así que las instalaciones no son reproducibles; torch es opcional en tiempo de ejecución (import perezoso con fallback).
- backend-clinic y backend-admin fijan la mayoría de versiones exactas, salvo openai/langgraph/langchain-openai (`>=`).
- `cryptography` aparece con versiones distintas en backend-clinic (43.0.0) y backend-admin (49.0.0); son entornos separados.
- No hay lockfile de Python en ningún servicio; los frontends tienen `package-lock.json`.

## Dependencias de datos y artefactos
- `backend-ml/models/classifier.pth` (≈ 42 MB, versionado en git), `classes.json`, `model_meta.json`.
- `datasets/` (MetaClass, ignorado por git) solo para entrenamiento y evaluación.
