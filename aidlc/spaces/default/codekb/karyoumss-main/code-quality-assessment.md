# Evaluación de calidad del código — karyoumss-main

## Pruebas

| Servicio | Pruebas | Estado verificado en este escaneo |
|---|---|---|
| backend-ml | 9 archivos en `tests/` | **65 passed, 1 warning (29,85 s)** con `py -3.12 -m pytest` desde `backend-ml/`. El `.venv` de backend-clinic no sirve (le falta `cv2`). |
| backend-clinic | 54 archivos en `apps/samples/tests/` | No ejecutado; `pytest.ini` exige `--cov-fail-under=90` |
| backend-admin | `apps/*/tests/` | No ejecutado; pytest-django + pytest-cov |
| frontends | Vitest; Playwright en frontend-clinic | No ejecutado |

Calidad de las pruebas de backend-ml: buena. `test_concurrencia.py` reproduce el bloqueo del event loop con `httpx.AsyncClient` + `ASGITransport` (documenta que `TestClient` no lo detectaría), cubre el 503 con `Retry-After`, la espera con éxito, que `/xai/` y `/classify/` pasan por el límite, la carga única del modelo, la validación del entorno y que el turno se libera aunque la inferencia falle. Las pruebas usan imágenes sintéticas (CI-safe) y no dependen del dataset. La advertencia es una deprecación de Starlette sobre `httpx` en `TestClient`.

## Cobertura

backend-ml no tiene configuración de cobertura (ni `pytest.ini`/`pyproject.toml` ni umbral). Hay un `.coverage` suelto de una ejecución anterior. El proyecto exige RN-09 (≥ 90 %), y backend-clinic lo aplica con `--cov-fail-under=90`.

## Linting y formato

No hay configuración en backend-ml. backend-admin declara ruff 0.5.5 sin configuración visible. El estilo observado es consistente: `snake_case`, anotaciones de tipo y `from __future__ import annotations`.

## CI/CD

No se encontró ningún pipeline (`.github/` ausente). DD-AUD-001 aplaza Dockerfiles, Compose y el apagado limpio a las sesiones S05–S07.

## Documentación

Docstrings excelentes, con razonamiento medido y trazabilidad (ADR-0007, DD-AUD-001, RN-07, ADR-0033). Corpus documental amplio en `docs/` (ADR-0001..0036, DD-*, auditorías). `backend-ml/README.md` está **desactualizado**: describe la "Fase B" con placeholder y 11 pruebas, y no documenta `/xai/`, `/classify/` ni el límite.

## Deuda técnica

| Señal | Ubicación | Impacto |
|---|---|---|
| El límite no expone su ocupación | `backend-ml/app/concurrencia.py` | No se puede observar la saturación; es lo que cubre el intent |
| Rutas inexistentes en el cliente | `backend-clinic/.../pipeline_client.py:34-57` (`/api/v1/samples/{id}/process|status/`) | Código muerto o roto en el contrato con backend-ml |
| README y descripción de la app desfasados | `backend-ml/README.md`, `main.py:23` | Documentación engañosa |
| `/xai/` y `/classify/` sin `response_model` | `backend-ml/app/main.py:60,114` | OpenAPI sin tipar |
| `except Exception` silencioso al cargar el modelo | `backend-ml/app/pipeline.py:41` | Degrada a placeholder sin registrar la causa |
| Dependencias Python sin fijar y sin lockfile | `backend-ml/requirements.txt` | Builds no reproducibles |
| Sin cobertura ni linter en backend-ml | — | RN-09 no se verifica automáticamente |
| Sin CI ni contenedores | repo | Las pruebas dependen de la disciplina local |
| `CLAUDE.md` describe U-Net/Celery/Redis que no existen | `CLAUDE.md` | Riesgo de suposiciones erróneas de los agentes |

Calificación rápida de backend-ml (escala de 3): nombres, **bueno**; tamaño de funciones, **bueno** (los endpoints `xai`/`classify` duplican la validación del bbox); manejo de errores, **bueno**, salvo la carga del modelo; presencia de pruebas, **buena**; duplicación, **regular** (validación de bbox y cálculo de `ref_h` repetidos); código muerto, **bueno**.
