# Plan de generación de código — estado del límite de inferencias

## Summary

- Builds: endpoint `GET /api/v1/inferencias/` con contadores `en_curso`/`en_espera` y acceso por secreto interno
- Touches: `backend-ml/app/concurrencia.py`, `backend-ml/app/main.py`, `backend-ml/app/schemas.py`, `backend-ml/.env.example`, `backend-ml/tests/test_estado_inferencias.py`
- Tests: 11 pruebas unitarias nuevas (pytest + TestClient), y las 65 existentes en verde

## Contexto

Trabajo de cero Units (ámbito express). Se parte de `inception/requirements-analysis/requirements.md` y del conocimiento del código en `aidlc/spaces/default/codekb/karyoumss-main/`. Proyecto brownfield: se modifican archivos existentes en su sitio, sin duplicados.

Radio de impacto (bajo): `concurrencia.py` lo usan `main.py` y `tests/test_concurrencia.py`; el cambio solo añade contadores dentro de `turno()` y un método nuevo, sin cambiar su comportamiento ni su firma. `main.py` y `schemas.py` solo ganan un endpoint y un esquema nuevos.

Línea base: 65 pruebas de backend-ml en verde (`py -3.12 -m pytest -q` desde `backend-ml/`).

## Pasos

- [x] **Step 1 — Estructura y configuración de producción.** Documentar `INTERNAL_SERVICE_SECRET` en `backend-ml/.env.example`, sin valor real, explicando que debe ser el mismo que en backend-clinic y backend-admin y que sin él solo el endpoint de estado responde 503 (FR4.3). Trazabilidad: FR4, FR4.3.
- [x] **Step 2 — Verificar el runner de pruebas.** Confirmar que `py -3.12 -m pytest -q tests/test_estado_inferencias.py` se ejecuta desde `backend-ml/` y registrar el comando exacto en `unit-test-instructions.md`.
- [x] **Step 3 — Lógica de negocio: implementar.** En `LimiteInferencias` (`concurrencia.py`) añadir `_en_curso` y `_en_espera`, protegidos por un `threading.Lock` propio. `en_espera` sube antes de `acquire` y baja al obtener turno o al rendirse con 503. `en_curso` sube al obtener turno y baja en el `finally`, también si la inferencia falla. Añadir `estado()`, que devuelve `{maximo, en_curso, libres, espera_max_s, en_espera}`. Trazabilidad: FR1.1–FR1.5, FR3.1–FR3.3.
- [x] **Step 4 — Lógica de negocio: escribir y ejecutar sus pruebas.** En `backend-ml/tests/test_estado_inferencias.py`:
  - estado en reposo;
  - `en_curso` con un turno ocupado y liberado;
  - `en_curso` vuelve a su valor si la inferencia falla;
  - un rechazo por espera agotada no cuenta en `en_curso` y deja `en_espera` en 0;
  - `en_espera` vale 1 mientras otra petición espera turno (hilos);
  - cuentas correctas con varios hilos a la vez.

  Trazabilidad: FR1, FR3.1–FR3.3.
- [x] **Step 5 — API: implementar.** En `schemas.py`, `EstadoInferenciasOut` con los cinco campos. En `main.py`, endpoint `def estado_inferencias()` en `GET /api/v1/inferencias/` que no llama a `limite.turno()`. Acceso:
  - lee `INTERNAL_SERVICE_SECRET` del entorno en cada petición;
  - si falta, responde 503 `no configurado`;
  - si la cabecera `X-Internal-Secret` falta o no coincide (comparada con `hmac.compare_digest`), responde 403;
  - si coincide, responde 200 con `limite.estado()`;
  - el valor del secreto no aparece en ninguna respuesta.

  Trazabilidad: FR1, FR2, FR4.1–FR4.3, NFR1, NFR2.
- [x] **Step 6 — API: escribir y ejecutar sus pruebas.** Con `TestClient` y `monkeypatch` sobre `main.limite` y el entorno:
  - 200 con el secreto correcto y el estado en reposo;
  - 200 con el límite ocupado, sin esperar turno;
  - 403 sin cabecera;
  - 403 con secreto incorrecto;
  - 503 sin secreto configurado, mientras `/health/` sigue respondiendo 200.

  Trazabilidad: FR2, FR4.1–FR4.3.
- [x] **Step 7 — Configuración de entorno y build.** No hay build en backend-ml. Ejecutar la suite completa (`py -3.12 -m pytest -q` desde `backend-ml/`) y confirmar 65 + nuevas en verde. Medir la cobertura del código nuevo con `--cov=app` (objetivo ≥ 90 %, NFR3).
- [x] **Step 8 — Documentación y trazabilidad.** Docstrings con referencia a FR/NFR en el código nuevo; `code-summary.md` y `traceability.json` en el registro de la etapa.

Las capas «modelo de datos», «repositorio» y «frontend» no aplican: backend-ml no tiene persistencia ni interfaz.

## Testing Contract

```json
{
  "version": 1,
  "methodology": "test-after",
  "source": "org",
  "ordering": "implement each applicable testable layer, then write and run that layer's tests.",
  "scope": "express",
  "test_strategy": "minimal",
  "project_type": "brownfield",
  "applicable_notes": [
    {
      "layer": "org",
      "text": "We treat tests as a first-class deliverable in every Bolt. The specific\nmethodology (TDD, BDD, ATDD, or classic test-after) is affirmed at\npractices-discovery and recorded in `team.md` under this heading with explicit\n`Methodology` and `Ordering` fields; Code Generation resolves those fields\nindependently from coverage, tooling, and scope notes.\n\nWhen no posture has been affirmed, our default per scope is:\n- **Methodology**: test-after\n- **Ordering**: implement each applicable testable layer, then write and run\n  that layer's tests.\n- `mvp`, `enterprise`, `feature`, `infra`, `classic` add an 80% line-coverage\n  floor and CI execution before merge.\n- `bugfix`, `security-patch` add a targeted regression for the specific\n  bug/vulnerability and require the existing suite to remain green.\n- `express` uses the Minimal strategy: requirement-driven unit tests (one per\n  requirement, with a happy-path floor per component); existing tests remain\n  green.\n- `poc`, `refactor`, `workshop` add no extra new-test floor and require the\n  existing suite to remain green.\n\nThe active `Test Strategy` still applies in every scope and determines test\nvolume/types. Scope floors are additive; they never reduce or replace the\nselected strategy.\n\nBuild and Test verifies defined coverage floors and affirmed quality targets;\nthey may not be weakened to make a step pass.\n\nAffirm a stricter posture in `team.md` if the team commits to one."
    }
  ],
  "obligations": {
    "strategy": "minimal",
    "strategy_volume": [
      "One verifiable test per requirement at the narrowest effective level.",
      "At least one happy-path unit test per component.",
      "Unit tests are the default; a bugfix/security scope floor may require an integration or E2E regression when that is the narrowest level that reproduces the defect."
    ],
    "scope_floor": [
      "Keep the existing test suite green.",
      "This scope adds no extra new-test floor beyond the selected test strategy."
    ],
    "combination_rule": "Apply every selected-strategy obligation and every scope-floor obligation; neither replaces the other, and a targeted scope regression may add the narrowest necessary test type beyond the strategy default."
  },
  "plan_profile": {
    "methodology": "test-after",
    "runner_step": "Verify the existing test runner/configuration and record the exact unit-scoped command.",
    "runner_ready_before_first_test": true,
    "testable_layers": [
      "Data model / database behavior",
      "Repository / data access",
      "Business logic",
      "API / endpoint",
      "Frontend behavior"
    ],
    "steps": [
      "Project structure and production configuration skeleton.",
      "Verify the existing test runner/configuration and record the exact unit-scoped command.",
      "Data model / database behavior - implement.",
      "Data model / database behavior - write and run its tests after implementation.",
      "Repository / data access - implement.",
      "Repository / data access - write and run its tests after implementation.",
      "Business logic - implement.",
      "Business logic - write and run its tests after implementation.",
      "API / endpoint - implement.",
      "API / endpoint - write and run its tests after implementation.",
      "Frontend behavior - implement.",
      "Frontend behavior - write and run its tests after implementation.",
      "Environment/build configuration.",
      "Documentation and traceability."
    ]
  },
  "input_sha256": "sha256:c8f84e35190e007d9863fad236154d0269ab9bf633fc2a3ff106ed965ba4a9b9",
  "contract_sha256": "sha256:bb76c1b22f8307be6e5780d50cabab891684449d5b164bd0e825e9e4e5c61e5b"
}
```
