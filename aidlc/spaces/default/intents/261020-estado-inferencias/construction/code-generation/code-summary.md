# Resumen del código — estado del límite de inferencias

## Qué se construyó

Endpoint `GET /api/v1/inferencias/` en backend-ml. Devuelve el estado del límite de inferencias: `maximo`, `en_curso`, `libres`, `espera_max_s` y `en_espera`. No pasa por el semáforo y exige el secreto interno de servicio.

## Archivos

| Archivo | Cambio |
|---|---|
| `backend-ml/app/concurrencia.py` | `LimiteInferencias`: contadores `_en_curso` y `_en_espera` bajo un lock propio, cuenta en `turno()` y método nuevo `estado()` |
| `backend-ml/app/schemas.py` | Esquema `EstadoInferenciasOut` con los cinco campos |
| `backend-ml/app/main.py` | Endpoint `def estado_inferencias()`: 503 sin secreto configurado, 403 si la cabecera falta o no coincide (`hmac.compare_digest`), 200 con `limite.estado()` |
| `backend-ml/.env.example` | `INTERNAL_SERVICE_SECRET=` documentado, sin valor |
| `backend-ml/tests/test_estado_inferencias.py` | 11 pruebas nuevas: 6 de lógica (con hilos) y 5 del endpoint |

## Decisiones clave

- `en_espera` baja en un `finally` alrededor de `acquire`. Así no se descuadra ni si `acquire` lanza una excepción.
- `estado()` lee los dos contadores juntos bajo el lock, para que `libres` y `en_curso` sean coherentes entre sí.
- El secreto se lee del entorno en cada petición. Sin él, backend-ml arranca igual y solo este endpoint responde 503 (FR4.3).
- El texto del 403 («Secreto de servicio inválido») es el mismo que usa backend-admin (`apps/config/internal_views.py`).

## Pruebas

- Pruebas nuevas: 11 de 11 en verde.
- Suite completa de backend-ml: 76 de 76 en verde (65 existentes + 11 nuevas).
- Cobertura de líneas de `app/concurrencia.py` y `app/main.py` con la suite completa: 100 %. Las líneas nuevas están cubiertas solo con las pruebas nuevas.
