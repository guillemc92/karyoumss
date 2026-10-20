# Instrucciones de build — backend-ml

## Dependencias

- Python 3.12 (`py -3.12`), con las dependencias de `backend-ml/requirements.txt` instaladas (`py -3.12 -m pip install -r requirements.txt`).
- Este cambio no añade dependencias: `hmac` y `os` son de la biblioteca estándar.

## Entorno

- `ML_MAX_INFERENCIAS` y `ML_ESPERA_MAX_S` (opcionales, valores por defecto 1 y 25).
- `INTERNAL_SERVICE_SECRET` (nuevo, opcional para arrancar). Tiene que ser el mismo valor que en backend-clinic y backend-admin. Sin él, `GET /api/v1/inferencias/` responde 503 y el resto del servicio funciona igual. Está documentado en `backend-ml/.env.example`, sin valor.

## Build

backend-ml es Python interpretado: no hay paso de compilación ni de empaquetado. Para verificar que la aplicación importa sin errores, ejecuta desde `backend-ml/`:

```bash
py -3.12 -c "import app.main"
```

La suite de pruebas, que importa `app.main`, cumple la misma función.

## Arranque

```bash
uvicorn app.main:app --port 8000
```

## Problemas habituales

- `ModuleNotFoundError: cv2`: estás usando el `.venv` de backend-clinic. Usa `py -3.12`.
- 503 «no configurado» en `/api/v1/inferencias/`: falta `INTERNAL_SERVICE_SECRET` en el entorno de backend-ml.
