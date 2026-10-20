# Instrucciones de pruebas de integración

## Alcance

La estrategia es Minimal (ámbito express), así que no se generan pruebas de integración aparte. El cambio vive entero en backend-ml y ningún otro servicio consume todavía el endpoint (queda fuera de alcance en `requirements.md`).

## Cobertura existente

Las pruebas del endpoint en `backend-ml/tests/test_estado_inferencias.py` lo ejercitan a través de la aplicación FastAPI completa con `TestClient`, incluida la convivencia con `/health/`.

## Cómo ejecutarlas

Desde `backend-ml/`:

```bash
py -3.12 -m pytest -q tests/test_estado_inferencias.py
```
