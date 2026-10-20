# Requisitos — estado del límite de inferencias en backend-ml

## Intent analysis

**Pedido original** (`project-description.json`): «Añadir a backend-ml un endpoint GET /api/v1/inferencias/ que devuelva el estado del límite de inferencias: maximo, en_curso, libres y espera_max_s, sin pasar por el semáforo, con sus pruebas.»

**Objetivo:** dar visibilidad del límite de inferencias que introdujo la issue #2 (DD-AUD-001 F1). Hoy backend-clinic solo se entera de que backend-ml está saturado cuando recibe un 503 y degrada a modo manual (RN-07). Con este endpoint, quien opera el sistema puede ver en vivo cuántas plazas hay, cuántas están ocupadas, cuántas peticiones esperan y cuánto esperan antes del 503.

**Tipo:** mejora pequeña, de un solo componente (`backend-ml`), de complejidad simple. Profundidad: Minimal.

**Decisiones del autor** (preguntas 1–3 de `requirements-analysis-questions.md`): el endpoint va protegido con el secreto interno; se añade un quinto campo `en_espera`; sin secreto configurado, backend-ml sigue arrancando y solo este endpoint responde 503.

## Functional requirements

### Consulta del estado

- **FR1** — El sistema expone `GET /api/v1/inferencias/` en backend-ml, que devuelve un objeto JSON con exactamente estos campos:
  - **FR1.1** `maximo` (entero): inferencias simultáneas permitidas (`ML_MAX_INFERENCIAS`).
  - **FR1.2** `en_curso` (entero): inferencias que tienen plaza en este momento.
  - **FR1.3** `libres` (entero): plazas libres, igual a `maximo − en_curso`.
  - **FR1.4** `espera_max_s` (número): espera máxima por un turno antes del 503 (`ML_ESPERA_MAX_S`).
  - **FR1.5** `en_espera` (entero): peticiones de inferencia que esperan turno sin haber obtenido plaza todavía.
- **FR2** — La consulta no pasa por el límite de inferencias: responde aunque no quede ninguna plaza libre y no ocupa ninguna.
- **FR3** — Los contadores son correctos con varias peticiones a la vez:
  - **FR3.1** `en_curso` sube al obtener plaza y baja al terminar, también cuando la inferencia falla.
  - **FR3.2** `en_espera` sube al empezar a esperar turno y baja al obtenerlo o al rendirse con 503.
  - **FR3.3** Una petición rechazada con 503 por espera agotada no cuenta en `en_curso`.

### Acceso

- **FR4** — El endpoint exige el secreto interno de servicio, con la misma convención que backend-admin:
  - **FR4.1** La petición debe llevar la cabecera `X-Internal-Secret` con el valor de `INTERNAL_SERVICE_SECRET`.
  - **FR4.2** Sin cabecera o con un valor distinto, responde **403**.
  - **FR4.3** Si backend-ml no tiene `INTERNAL_SERVICE_SECRET` configurado, el endpoint responde **503** («no configurado»). backend-ml arranca igual, y el resto de los endpoints (inferencia y `/health/`) siguen funcionando.

### Criterios de aceptación

- Dado que no hay inferencias en curso, cuando se consulta con el secreto correcto, entonces responde 200 con `en_curso = 0`, `en_espera = 0` y `libres = maximo`.
- Dado que hay una inferencia ocupando la única plaza, cuando se consulta con el secreto correcto, entonces responde 200 con `en_curso = 1` y `libres = 0`, sin esperar turno.
- Dado que una segunda inferencia espera turno, cuando se consulta, entonces `en_espera = 1`; cuando se rinde con 503, entonces `en_espera` vuelve a 0 y `en_curso` no cambió.
- Dado que una inferencia falla con una excepción, cuando termina, entonces `en_curso` vuelve a su valor anterior.
- Dada una petición sin cabecera o con un secreto incorrecto, entonces responde 403.
- Dado que backend-ml no tiene el secreto configurado, cuando se consulta el endpoint, entonces responde 503; y `/health/` y `/api/v1/segment/` siguen respondiendo.

## Non-functional requirements

- **NFR1** — El endpoint es síncrono (`def`) y solo lee contadores protegidos por un lock; no hace E/S ni cómputo. Con una inferencia en curso, la consulta no espera a que termine (no pasa por el semáforo).
- **NFR2** — La comparación del secreto usa una comparación de tiempo constante (`hmac.compare_digest`), y el valor del secreto no aparece en respuestas, logs ni mensajes de error.
- **NFR3** — Pruebas (estrategia Minimal, ámbito express): al menos una prueba por requisito funcional. Las 65 pruebas existentes de backend-ml siguen en verde, y el código nuevo queda con cobertura de líneas ≥ 90 % (RN-09).

## Constraints

- Solo cambia backend-ml (FastAPI). La API y el comportamiento de los endpoints existentes no cambian.
- Configuración por entorno, igual que `ML_MAX_INFERENCIAS` y `ML_ESPERA_MAX_S`; `INTERNAL_SERVICE_SECRET` se documenta en `backend-ml/.env.example` sin valor real.
- Nombres en español, como el resto de `concurrencia.py` (`maximo`, `en_curso`, `libres`, `espera_max_s`, `en_espera`).

## Assumptions

- La cabecera `X-Internal-Secret` y la respuesta 403 siguen la convención existente de `backend-admin/apps/config/internal_views.py`, porque el autor eligió «como la llamada de backend-clinic a backend-admin» (pregunta 1).
- El valor del secreto en backend-ml es el mismo `INTERNAL_SERVICE_SECRET` que comparten backend-clinic y backend-admin; desplegarlo en el entorno de backend-ml es tarea de configuración, no de código.

## Out of scope

- Que backend-clinic consuma este endpoint o lo muestre en alguna interfaz.
- Métricas históricas, exportación a Prometheus u OpenTelemetry.
- Cambiar la autenticación de los demás endpoints de backend-ml.

## Open questions

Ninguna. Las tres decisiones abiertas se resolvieron en `requirements-analysis-questions.md`.
