---
id: ADR-0038
title: La bitácora de auditoría se queda en el monolito — medido, extraerla añade fallos sin ganar nada medible
date: 2026-11-02
status: accepted
related: [ADR-0008, ADR-0020, ADR-0022, ADR-0015]
---

# ADR-0038: No extraer la bitácora de auditoría a un servicio aparte

- **Autores:** Ing. Guillermo Mamani Chambi (G04), con Claude
- **Origen:** experimento E3 de M8, «Monolito modular frente a servicio
  extraído»
- **Diseño:** [DD-E3-001](../design/DD-E3-001.md)
- **Evidencia:** [`bench/e3/INFORME.md`](../../bench/e3/INFORME.md)
- **Aceptado:** 2026-11-04, por el autor

## Contexto

La bitácora de auditoría (ADR-0022) es la tabla `clinic_audit_events` de
`backend-clinic`. Es append-only (RN-05) y encadena cada evento al anterior del
mismo caso con un hash SHA-256.

**Había una razón real para extraerla:** es un registro de cumplimiento (21 CFR
Part 11). Con una base y un servicio propios, nadie de la parte clínica podría
tocarla, ni siquiera por error.

**Hay tres hechos de código que la atan al monolito:**
- **La escritura comparte transacción:** `emit_audit_event()`
  ([services.py](../../backend-clinic/apps/samples/services.py)) escribe el
  evento en la misma transacción que la acción clínica, bajo
  `select_for_update` sobre el último evento del caso. Si la acción se revierte,
  el evento también; y dos acciones a la vez no pueden bifurcar la cadena.
- **Deshacer lee la bitácora como estado del dominio:** «deshacer»
  (DD-KARYO-007) busca en ella la última edición para compensarla.
- **Hay 17 llamadas a `emit_audit_event()`** repartidas en `services.py`.

**Qué se midió en el E3.** Solo la **lectura** (`GET /samples/{id}/audit/`),
con las dos formas detrás de una interfaz (`BitacoraPort`, `BITACORA_MODO`):
- 20 corridas, 5 por combinación;
- k6 a 10 pet/s por ruta;
- Toxiproxy rompiendo la red a mitad de cada corrida;
- `down -v` y un seed fijo de 1.000 casos entre corridas.

Para repetirlo:

    bench/e3/correr.sh corridas 5 && py -3 bench/e3/resumir.py

## Decisión

### D1 — La bitácora sigue dentro de `backend-clinic`

En producción, `BITACORA_MODO=proceso`, el valor por omisión. No se despliega
el servicio extraído.

### D2 — La interfaz se queda

`BitacoraPort` y sus dos implementaciones (`en_proceso`, `http`) se conservan:
- cuestan poco: unas 240 líneas, con 100 % de cobertura;
- si la condición de reversión se cumple, volver a medir cuesta un comando, no
  un rediseño;
- el banco (`bench/e3/`) se queda en el repo por la misma razón.

### D3 — Si un día se extrae, se extrae también la escritura, o no se extrae

Extraer solo la lectura, como en el experimento, exige mantener dos bases
sincronizadas. Eso no tiene sentido fuera de un banco de pruebas.

Extraer la escritura exige resolver antes:
- la atomicidad con la acción clínica (una *outbox* o una saga);
- el orden de la cadena de hashes entre servicios;
- la lectura que hace «deshacer».

Nada de eso se midió. Necesita su propio ADR.

## Evidencia

Cada cifra es la mediana de 5 corridas, con el rango entre paréntesis. El
detalle está en [`INFORME.md`](../../bench/e3/INFORME.md).

- **Lectura sana** (sin falla, fase *antes*):
  - p95 de `…/audit/`: **179,5 ms** en proceso frente a **194,1 ms** extraída
    (+14,6 ms);
  - p50: 44 frente a 57 ms.
  - El coste en latencia es pequeño y cabe dentro del ruido, porque el rango en
    proceso va de 100 a 255 ms.
- **Errores sin falla:** en proceso, **0 en las 5 corridas**. En la forma
  extraída, **algún 503 en 10 de 15**, con hasta un 9 %. Las protecciones
  mismas (300 ms por intento) cortan las respuestas lentas en frío.
- **Con la bitácora colgada, caída o lenta:**
  - la API no se cae: `…/audit/` responde 503 con `Retry-After`, con un p95 de
    757, 217 y 754 ms;
  - la ruta de control sigue con **0 % de errores**;
  - pero el p95 de control **sube ×2,7–3,3** (de 53,7 a 145–177 ms), aunque su
    p50 no se mueve.
- **Recuperación:** **11–13 % de 503** en los 10 s que siguen a la falla, que
  equivalen a 1,1–1,3 s sin bitácora. Lo causan los 2 s del breaker, y hay uno
  por cada proceso de gunicorn.
- **Arranque:** `up --wait` de **5,6 s** frente a **11,8 s** (+6,2 s): se
  arranca un Django más. El build en frío no cambia: 110,6 frente a 110,2 s,
  porque la imagen es una sola.

Hipótesis (fijadas antes de medir, `3526e3e`):
- **se cumplen** H1 (≤ 20 ms), H3 (≤ 900 ms colgado) y H5 (`up` +6,2 s; build igual);
- **no se cumplen** H2 (control ±10 %) ni H4 (≤ 1 % después).

## Consecuencias

**A favor**

- No se añade un servicio, un despliegue ni una red a un registro de
  cumplimiento. La lectura de la bitácora no puede fallar por la red, y hoy no
  falla: 0 errores en las corridas en proceso.
- La escritura sigue siendo atómica con la acción clínica. La cadena de hashes
  sigue protegida por un solo bloqueo en una sola base.
- Queda la interfaz y un banco que se repite con un comando.

**En contra, y hay que decirlo**

- **El aislamiento queda sin resolver.** Nadie de la parte clínica *debería*
  modificar la bitácora, pero comparte base con ella. Hoy lo impiden:
  - `AuditEvent.save()`, que rechaza los UPDATE;
  - la revisión de código.

  No lo impide la base de datos: un `queryset.update()` o una SQL directa
  pasarían.
- **Lo más importante no se midió:** escribir por la red. La decisión se apoya
  en un argumento para la escritura y en números solo para la lectura.
- **La máquina era modesta:** 2 núcleos físicos, SQLite, todo en un host. En
  una máquina mayor, el coste de las protecciones (errores en frío, cola de la
  ruta de control) podría bajar. Eso no invalida la decisión, pero sí la
  condición de reversión R2.

## Condición de reversión

Esta decisión se revisa si se cumple **cualquiera** de estas condiciones, y la
revisión empieza por repetir el E3 (`bench/e3/correr.sh corridas 5`):

- **R1 · Requisito de aislamiento.** Que una auditoría regulatoria o la UMSS
  exija que la bitácora viva en una base con credenciales que `backend-clinic`
  no tenga. Ese requisito pesa más que los números de este ADR.
- **R2 · Las protecciones dejan de costar.** Que, repetido el E3 en el
  hardware de producción **y con la configuración que se vaya a desplegar**, la
  forma extraída cumpla las tres cosas en 5 de 5 corridas:
  - 0 % de errores sin falla;
  - ≤ 1 % de errores en la fase *después*;
  - un p95 de control durante la falla dentro de ±10 % del de en proceso.

  **El hardware solo no basta.** El segundo punto depende del breaker. Con el
  de este ADR (reset de 2 s, uno por proceso), cada worker puede seguir
  rechazando hasta 2 s después de quitar la falla. En la fase *después*, que
  dura 10 s, eso es hasta un 20 %, en cualquier máquina. La H4 (≤ 1 %) ya era
  incompatible con esos parámetros antes de medir.

  Para que R2 pueda cumplirse, el banco tiene que repetirse antes con uno de
  estos cambios:
  - un reset ≤ 100 ms, que a 10 pet/s equivale al 1 % de la fase;
  - un breaker que se cierre en cuanto una llamada real tenga éxito, sin
    esperar al reset;
  - o un límite de llamadas simultáneas (*bulkhead*) en lugar del breaker.

  Ese mismo límite es también la prueba directa para el tercer punto. Si el
  p95 de control se triplica porque las llamadas a la bitácora ocupan los hilos
  de gunicorn, un bulkhead lo corrige. Si se triplica igual con «caído», que
  falla al instante sin retener hilos, la causa es la CPU compartida y la
  corrige el hardware.
- **R3 · La lectura pesa en la clínica.** Que en producción el p95 de
  `GET /samples/{id}/audit/` en proceso pase de **500 ms durante 7 días
  seguidos**, o que la tabla pase de **10 millones de eventos**. Sería la
  «carga distinta» que justifica separar un módulo.

## Alternativas descartadas

- **Extraer solo la lectura (la forma 2 del E3) en producción:** obliga a
  sincronizar dos bases para no ganar nada medible, y añade los errores y la
  recuperación lenta medidos.
- **Extraer con un breaker compartido entre procesos** (por ejemplo, en Redis):
  acortaría la recuperación de la H4, pero añade otra dependencia de red para
  proteger una dependencia de red. Si R2 se cumple sin él, no hace falta.
- **Aislar la tabla con permisos de la base y no con un servicio** (un usuario
  de Postgres con solo INSERT/SELECT sobre `clinic_audit_events`): es la
  respuesta probable a R1. Cuando se migre a Postgres, va en su propio ADR.
