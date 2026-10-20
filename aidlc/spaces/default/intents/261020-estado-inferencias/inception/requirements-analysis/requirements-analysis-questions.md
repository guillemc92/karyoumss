# Preguntas de análisis de requisitos — estado del límite de inferencias

El pedido es claro: un endpoint `GET /api/v1/inferencias/` en backend-ml que devuelva `maximo`, `en_curso`, `libres` y `espera_max_s` sin pasar por el semáforo, con pruebas. El reconocimiento del código confirmó dónde va (`LimiteInferencias` en `backend-ml/app/concurrencia.py`, instancia `main.limite`). Quedan dos decisiones que el código no resuelve.

## Pregunta 1: ¿Quién puede consultar el estado?

backend-ml no tiene autenticación en ningún endpoint: solo lo llama backend-clinic por la red interna, y `/health/` es público. El estado del límite no contiene datos de pacientes (solo cuatro números).

A. Público, igual que `/health/` (sin autenticación; coherente con el resto del servicio)
B. Protegido con el secreto interno compartido (`INTERNAL_SERVICE_SECRET`), como la llamada de backend-clinic a backend-admin
X. Other (please specify)

[Answer]: B

## Pregunta 2: ¿Se cuentan también las peticiones que esperan turno?

Hoy, mientras una inferencia ocupa la plaza, otra puede estar esperando hasta 25 s antes de recibir 503. El pedido menciona solo `maximo`, `en_curso`, `libres` y `espera_max_s`.

A. Solo los cuatro campos pedidos: `en_curso` cuenta las inferencias que tienen plaza; las que esperan no aparecen
B. Añadir un quinto campo `en_espera` con las peticiones que esperan turno
X. Other (please specify)

[Answer]: B

## Pregunta 3 (seguimiento de la 1): ¿Qué pasa si backend-ml no tiene el secreto configurado?

Elegiste proteger el endpoint con el secreto interno (respuesta B de la pregunta 1). backend-ml no lee hoy `INTERNAL_SERVICE_SECRET`; habría que añadirlo a su configuración. Se usaría la convención que ya existe en backend-admin: cabecera `X-Internal-Secret` y 403 si no coincide.

A. backend-ml no arranca sin el secreto y dice cuál falta (igual que clinic y admin desde la issue #4)
B. backend-ml arranca igual; solo este endpoint responde 503 «no configurado» mientras falte el secreto (la inferencia sigue funcionando)
X. Other (please specify)

[Answer]: B
