# Escaneo de código del developer — estado-inferencias

## Developer Code Scan Results

Escaneo realizado el 2026-10-19 sobre `HEAD 4fc0de6` (rama `feature-con-aidlc`), con árbol de trabajo sucio (cambios sin commitear fuera de `backend-ml/`). Profundidad Minimal: análisis profundo de `backend-ml/` (servicio que toca el intent) y del cliente que lo consume en `backend-clinic`; el resto del monorepo, a nivel de directorio.

### Scan Coverage
- **Analyzed deeply**:
  - `backend-ml/app/` (los 12 módulos, en especial `main.py`, `concurrencia.py`, `schemas.py`, `pipeline.py`)
  - `backend-ml/tests/` (9 archivos; suite ejecutada: 65 passed en 29,85 s con Python 3.12 global)
  - `backend-ml/requirements.txt`
  - `backend-ml/.env.example`
  - `backend-ml/README.md`
  - `backend-clinic/apps/samples/pipeline_client.py` (consumidor HTTP de backend-ml)
- **Skimmed only**:
  - `backend-ml/training/` (README y cabeceras; notebooks `.ipynb` no abiertos)
  - `backend-ml/models/` (solo `model_meta.json`; `.pth` binarios)
  - `backend-clinic/` (rutas de `apps/samples/urls.py`, `settings.py` líneas de backend-ml, `PipelineHealthView`, `requirements.txt`, `pytest.ini`)
  - `backend-admin/` (rutas, `requirements.txt`)
  - `frontend-clinic/`, `frontend-admin/` (`package.json`, estructura de `src/`)
  - `docs/` (listado; leído `docs/design/DD-AUD-001.md` §F1)
  - `Caddyfile.dev`, `scripts/`, `pocs/`, `package.json` raíz
- **Left out**:
  - `node_modules/` (raíz y frontends), `.venv/` (backend-clinic, backend-admin)
  - `__pycache__/`, `.pytest_cache/`, `.coverage`, `coverage/`, `htmlcov/`, `coverage.xml`, `test-results/`, `playwright-report*/`, `frontend-admin/dist/`
  - `datasets/` (datos), `model/` y `backend-ml/models_v1_backup/` (ignorados), `backend-ml/models_v2_backup/` (pesos binarios)
  - `*.sqlite3`, `backend-clinic/media/`
  - Material no-código de la raíz: PDFs, `.mp4`, `.docx`, prototipos `.html`, `script.sql` (esquema MetaClass legado)
  - Instalación de AI-DLC y otras herramientas de agentes: `.claude/`, `.cursor/`, `.agents/`, `.skills/`, `aidlc/`

### Packages Found
- backend-ml — servicio HTTP (FastAPI) — Python — motor de inferencia: segmentación OpenCV + clasificación EfficientNet-B3 + Grad-CAM
- backend-clinic — servicio HTTP (Django + DRF) — Python — contexto clínico: muestras, cariotipo, ISCN, auditoría, LLM/RAG/agente
- backend-admin — servicio HTTP (Django + DRF) — Python — contexto administrativo: usuarios, RBAC, 2FA, configuración, autoridad JWT
- frontend-clinic — SPA (React 18 + Vite 5 + Konva) — TypeScript — visor/corrección de cariotipo
- frontend-admin — SPA (React 18 + Vite 5) — TypeScript — panel de administración
- backend-ml/training — scripts y notebooks — Python — extracción de etiquetas, entrenamiento y evaluación (offline)

### Build System
- **Type**: pip + `requirements.txt` (Python); npm (frontends); sin Docker Compose ni Dockerfiles en el repo
- **Config Files**: `backend-ml/requirements.txt`, `backend-clinic/requirements.txt`, `backend-admin/requirements.txt`, `backend-clinic/pytest.ini`, `backend-admin/pytest.ini`, `frontend-*/package.json`, `frontend-*/vite.config.ts`, `frontend-*/vitest.config.ts`, `Caddyfile.dev`
- **Build Dependencies**: backend-clinic → backend-ml (HTTP `CLINIC_FASTAPI_URL`, :8000); backend-clinic → backend-admin (HTTP `ADMIN_INTERNAL_URL`, :8001); frontend-clinic → backend-clinic (:8002); frontend-admin → backend-admin (:8001)

### APIs Discovered
- REST (FastAPI) — `backend-ml/app/main.py` — 4 endpoints: `GET /health/`, `POST /api/v1/segment/`, `POST /api/v1/xai/`, `POST /api/v1/classify/` (+ `/docs`, `/openapi.json` automáticos)
- REST (DRF) — `backend-clinic/apps/samples/urls.py` — 25 rutas bajo `/api/clinic/`
- REST (DRF) — `backend-admin/apps/*/urls.py` — ~15 rutas bajo `/api/admin/`, `/api/auth/`, `/api/internal/`

### Frameworks & Libraries
- FastAPI — `>=0.110` (instalado 0.140.0) — API de backend-ml
- uvicorn[standard] — `>=0.29` — servidor ASGI
- OpenCV (opencv-python-headless) — `>=4.9` (instalado 5.0.0) — segmentación watershed
- NumPy — `>=1.26` — arrays de imagen
- torch / torchvision — `>=2.2` / `>=0.17` (instalado 2.13.0+cpu) — EfficientNet-B3, Grad-CAM
- pytest / httpx — `>=8.0` / `>=0.27` (instalado pytest 8.3.2) — pruebas
- Django 5.0.6 + DRF 3.15.2 — backend-clinic y backend-admin
- React 18.3 + Vite 5.3 + TypeScript 5.5 + Vitest 1.6 + MSW 2.3 — frontends; Konva 9 + react-konva 18 y Playwright 1.63 en frontend-clinic

### Test Coverage
- **Test Directories**: `backend-ml/tests/`, `backend-clinic/apps/samples/tests/` (54 archivos), `backend-admin/apps/*/tests/`, `frontend-clinic/tests/` + `specs/`, `frontend-admin/tests/`
- **Test Frameworks**: pytest (+ `fastapi.testclient`, `httpx.AsyncClient` con `ASGITransport`), pytest-django, Vitest, Playwright
- **Coverage Config**: ausente en backend-ml (sin `pytest.ini`/`pyproject.toml`; hay un `.coverage` suelto); presente en backend-clinic (`--cov-fail-under=90`, RN-09) y backend-admin

### Code Quality Indicators
- **Linting**: no hay configuración en backend-ml; `ruff==0.5.5` declarado en backend-admin sin config visible; frontends sin ESLint/Prettier confirmado
- **CI/CD**: no se encontró `.github/` ni otro pipeline
- **Documentation**: buena — docstrings extensos en español con trazabilidad a ADR/DD/RN; `backend-ml/README.md` desactualizado (habla de "Fase B" y 11 tests)

### Technical Debt Signals
- `backend-ml/app/concurrencia.py:39` — `LimiteInferencias` solo guarda el `BoundedSemaphore`; no expone cuántas inferencias hay en curso (el contador interno `_value` es privado de CPython).
- `backend-clinic/apps/samples/pipeline_client.py:34-57` — `trigger_processing` y `get_status` llaman a `/api/v1/samples/{id}/process/` y `/status/`, que backend-ml no expone.
- `backend-ml/README.md` — desfasado frente al código (clasificador real v3, `/xai/`, `/classify/`, límite de inferencias).
- `backend-ml/app/main.py:23` — la descripción de la app aún dice "Baseline OpenCV + placeholder".
- backend-ml sin `pytest.ini`, sin umbral de cobertura ni linter, aunque el proyecto exige RN-09 (≥ 90 %).
- `backend-ml/app/pipeline.py:41` — `except Exception` amplio al cargar el modelo (degradación RN-07 intencionada, pero silenciosa: no registra el motivo).
- `/xai/` y `/classify/` devuelven `dict` sin `response_model` (contrato no tipado en OpenAPI).
- Dependencias Python de backend-ml sin fijar versión exacta (`>=`).

## Handoff Summary
- **Intent-relevant finding**: el estado que pide el intent vive en `backend-ml/app/concurrencia.py:29-58`. `LimiteInferencias` ya tiene `maximo` y `espera_s` públicos (de `ML_MAX_INFERENCIAS` y `ML_ESPERA_MAX_S`), pero NO lleva la cuenta de inferencias en curso: `turno()` (líneas 47-58) solo hace `acquire(timeout)`/`release()` sobre un `threading.BoundedSemaphore`. Para `en_curso` y `libres` hace falta un contador propio protegido por lock, que se incremente tras el `acquire` y se decremente en el `finally`. La instancia es el global de módulo `limite` en `backend-ml/app/main.py:30`, que las pruebas sustituyen con `monkeypatch.setattr(main, 'limite', ...)`. El endpoint nuevo debe ser `def` y no entrar en `limite.turno()`, igual que `GET /health/` (`main.py:33-41`).
- **Risks / follow-up**: (1) Ninguna regla aparte de esta convención impide que el endpoint de estado pase por el semáforo; la prueba debe demostrar que responde con el límite ocupado (patrón de `tests/test_concurrencia.py:150-159`, que ocupa el turno con `with limite.turno():`). (2) Para que el estado sea coherente, el contador tiene que actualizarse dentro del mismo `try/finally` que libera el semáforo. Si no, una inferencia que falle deja `en_curso` inflado; ya existe la prueba `test_libera_el_turno_aunque_falle_la_inferencia` como modelo. (3) `espera_max_s` es `float` (por defecto 25.0); el contrato debe fijar el tipo. (4) No hay autenticación en backend-ml: el endpoint quedaría público como `/health/`. (5) Hay que mantener en verde las 65 pruebas existentes. Se ejecutan con `py -3.12 -m pytest` desde `backend-ml/`; el `.venv` de backend-clinic no tiene `cv2`.
