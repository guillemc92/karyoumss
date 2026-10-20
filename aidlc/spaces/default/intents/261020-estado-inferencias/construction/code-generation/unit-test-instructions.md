# Instrucciones de pruebas unitarias — estado del límite de inferencias

## Framework y configuración

- pytest + `fastapi.testclient.TestClient`, la configuración que ya usa backend-ml (`backend-ml/tests/conftest.py`). No hace falta configuración nueva.
- Intérprete: `py -3.12`. backend-ml no tiene `.venv` propio, y el `.venv` de backend-clinic no sirve porque le falta `cv2`.

## Cómo ejecutar SOLO las pruebas de este cambio

Desde `backend-ml/`:

```bash
py -3.12 -m pytest -q tests/test_estado_inferencias.py
```

Cobertura del código tocado:

```bash
py -3.12 -m pytest -q tests/test_estado_inferencias.py --cov=app.concurrencia --cov=app.main --cov-report=term-missing
```

## Objetivo de cobertura

- Código nuevo de `concurrencia.py` y del endpoint en `main.py`: ≥ 90 % de líneas (RN-09, NFR3).
- Las 65 pruebas existentes siguen en verde (lo verifica Build and Test con la suite completa).

## Volumen (estrategia Minimal)

Una prueba por requisito, 11 en total:

| Requisito | Prueba |
|---|---|
| FR1 (campos en reposo) | estado en reposo del límite |
| FR3.1 | `en_curso` sube y baja con un turno |
| FR3.1 (fallo) | `en_curso` vuelve si la inferencia falla |
| FR3.2, FR3.3 | rechazo por espera: no cuenta en `en_curso` y `en_espera` vuelve a 0 |
| FR1.5, FR3.2 | `en_espera` = 1 mientras otra petición espera (hilos) |
| FR3 (concurrencia) | cuentas correctas con varios hilos |
| FR1, FR4.1 | endpoint 200 con secreto correcto |
| FR2 | endpoint 200 con el límite ocupado, sin esperar turno |
| FR4.2 | 403 sin cabecera |
| FR4.2 | 403 con secreto incorrecto |
| FR4.3 | 503 sin secreto configurado, y `/health/` sigue en 200 |

## Mocks y datos de prueba

- `monkeypatch.setattr(main, 'limite', LimiteInferencias(maximo=..., espera_s=...))` para un límite controlado.
- `monkeypatch.setenv` / `monkeypatch.delenv('INTERNAL_SERVICE_SECRET')` para el secreto, con un valor de prueba fijo; nunca un secreto real.
- Las pruebas con hilos usan `threading.Barrier` y `Event` para sincronizar, sin `sleep`.
- `/health/` usa un clasificador falso ya cargado en `pipeline._classifier_singleton`, para no cargar el modelo real (~16 s).
