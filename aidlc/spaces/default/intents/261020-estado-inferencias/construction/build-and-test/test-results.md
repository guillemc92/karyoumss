# Resultados de build y pruebas

## Build

backend-ml no tiene paso de compilación. La suite importa `app.main` sin errores.

## Pruebas unitarias del cambio

Desde `backend-ml/` se ejecutó:

```
py -3.12 -m pytest -q tests/test_estado_inferencias.py
11 passed, 1 warning in 1.58s
```

## Suite completa y cobertura

Desde `backend-ml/` se ejecutó:

```
py -3.12 -m pytest -q --cov=app.concurrencia --cov=app.main --cov-report=term-missing
Name                  Stmts   Miss  Cover   Missing
app\concurrencia.py      46      0   100%
app\main.py              75      0   100%
TOTAL                   121      0   100%
76 passed, 1 warning in 40.26s
```

| | Cantidad |
|---|---|
| Total | 76 |
| Pasan | 76 |
| Fallan | 0 |
| Omitidas | 0 |

El único aviso, `StarletteDeprecationWarning` (httpx en TestClient), ya existía antes del cambio.

## Matriz de verificación de objetivos

| Target ID | Fuente | Esperado | Real | Evidencia | Etapa responsable | Veredicto |
|---|---|---|---|---|---|---|
| NFR3-tests-por-FR | `requirements.md` NFR3 | ≥ 1 prueba por FR (FR1–FR4) | 11 pruebas; FR1, FR2, FR3 y FR4 cubiertos | `cross-unit-traceability.md`, salida de pytest | build-and-test | Met |
| NFR3-suite-existente | `requirements.md` NFR3; contrato `scope_floor` | 65 existentes en verde | 65 de 65 (76 de 76 con las nuevas) | salida de la suite completa | build-and-test | Met |
| NFR3-cobertura | `requirements.md` NFR3 (RN-09) | ≥ 90 % de líneas en el código nuevo | 100 % en `concurrencia.py` y `main.py` | salida de `--cov` | build-and-test | Met |
| TC-minimal-happy-path | Testing Contract, `strategy_volume` | ≥ 1 prueba de camino feliz por componente | lógica: estado en reposo; API: 200 con secreto correcto | `tests/test_estado_inferencias.py` | build-and-test | Met |
