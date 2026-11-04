# Demo 3 (release 8.3.0) — Grupo BIOMED UMSS

| Campo | Valor |
|---|---|
| **Demo** | 3 · miércoles 4 de noviembre de 2026 |
| **Release** | `release/8.3.0` |
| **Repositorio** | https://github.com/guillemc92/karyoumss |
| **Integrantes** | 1 (grupo individual) |
| **Canal oficial** | Classroom (este archivo es la copia del repositorio) |

## Integrantes y funcionalidades

| Integrante | Funcionalidad | Tamaño | Caso de uso (FSD) | Diseño | Repositorio |
|---|---|---|---|---|---|
| Guillermo Mamani Chambi ([`guillemc92`](https://github.com/guillemc92)) | 1 · Enderezar cada cromosoma en el cariograma | Mediana | FSD-UC-003 (corrección manual) | [DD-KARYO-008](../design/DD-KARYO-008.md) | https://github.com/guillemc92/karyoumss |
| Guillermo Mamani Chambi | 2 · La bitácora de auditoría detrás de una interfaz, con degradación controlada | Mediana | FSD-UC-005 (audit trail) y FSD-UC-007 (modo degradado) | [DD-E3-001](../design/DD-E3-001.md) · [ADR-0038](../adr/0038-no-extraer-bitacora-auditoria.md) | https://github.com/guillemc92/karyoumss |

## Funcionalidad 1 — Enderezar cada cromosoma en el cariograma

**Caso de uso:** FSD-UC-003. **Antes:** los botones ↺ ↻ giraban **el lienzo entero**, y
un cromosoma en diagonal no se podía poner de pie. Solo se podía girar 180°, y el
backend rechazaba cualquier otro ángulo. En `metafase_1`, 27 de 38 cromosomas estaban
inclinados más de 10°.

**Criterios de aceptación:**

1. **Cada cromosoma se endereza solo.**
   - Se recorta por su silueta, no por su caja.
   - El ángulo sale de los momentos de área de la silueta.
   - Los casi redondos no se giran.
   - Prueba E2E (`tests/auditado/cariograma-enderezado.spec.ts`): un cromosoma 10
     inclinado 59° en la metafase queda a **26,5° con el código anterior (falla)** y
     a **1,7°** con este cambio.
2. **Ajuste fino auditado.**
   - El panel tiene «−5°», «+5°» y «Restablecer».
   - Cada cambio emite un evento `ORIENT` con la orientación de antes y la de después.
   - Prueba: «+5°» dos veces da +10° y dos eventos `ORIENT` (ajuste 0→5 y 5→10).
3. **La API valida el ajuste.**
   - Sin `ajuste`, se conserva el guardado.
   - Un valor fuera de [−90, 90], no entero o booleano responde 400, sin evento.
   - Un caso bloqueado responde 409 y un analista ajeno, 403.
4. **El giro de la vista se distingue.** La barra dice «Rotar vista», y rotar la
   vista no cambia la orientación guardada de ningún cromosoma.
5. **El contrato cambia sin romper a nadie.** `ajuste` es un campo opcional nuevo en la
   petición, y oasdiff no marca ninguna ruptura.

**Endpoint en el contrato** (`backend-clinic/openapi.json`):

| Método y ruta | Qué cambia |
|---|---|
| `POST /api/clinic/samples/{id}/chromosomes/{cid}/orient/` | Acepta `ajuste` (entero, −90..90, opcional) además de `giro` y `volteo` |

**Evidencia:**
- PR [#7](https://github.com/guillemc92/karyoumss/pull/7), con el CI en verde y oasdiff sin rupturas.
- Commits `b893fb0`, `d3554d3`, `3f4afe3`, `1cb711d` y `75ad49f`.
- 12 mutaciones, todas detectadas (DD-KARYO-008 §12).

## Funcionalidad 2 — La bitácora de auditoría detrás de una interfaz, con degradación controlada

**Casos de uso:**
- **FSD-UC-005**, la bitácora inmutable con cadena de hash.
- **FSD-UC-007**, el modo degradado: si una parte cae, la API responde y dice cuándo
  reintentar.

**Por qué:** es el experimento E3 de M8, monolito modular frente a servicio extraído.
La funcionalidad permite que la bitácora se lea desde el propio proceso o desde un
servicio aparte sin tocar el resto del código. Así la decisión de extraerla se toma
con datos.

**Criterios de aceptación:**

1. **En producción no cambia nada.** Con `BITACORA_MODO=proceso` (el valor por omisión),
   `GET …/audit/` devuelve **el mismo JSON que antes**. Una prueba de equivalencia lo
   compara.
2. **Puede leerse desde un servicio aparte.** Se activa con `BITACORA_MODO=http`. Es la
   misma imagen con otro punto de entrada.
   - **Acceso:** sin el secreto interno (`X-Internal-Secret`) responde 403.
   - **Protecciones:** plazo de 300 ms por intento, 2 intentos y 800 ms en total.
   - **Breaker:** se abre tras 3 fallos y prueba de nuevo a los 2 s.
3. **Si la bitácora no responde, la API no se cae.**
   - **Respuesta:** `GET …/audit/` devuelve `503 AUDIT_UNAVAILABLE` con `Retry-After: 2`.
   - **Contrato:** el 503 está declarado, y oasdiff lo clasifica como cambio aditivo.
   - **Resto de la API:** la ruta de control sigue con 0 % de errores.
4. **La decisión se tomó midiendo.**
   - **Banco:** reproducible en `bench/e3/`, con Docker, Toxiproxy y k6. Toxiproxy cuelga,
     tira o ralentiza la bitácora a mitad de la corrida.
   - **Corridas:** 20, a 10 peticiones por segundo por ruta.
   - **Hipótesis:** commiteadas **antes** de medir.
   - **Resultado:** [`bench/e3/INFORME.md`](../../bench/e3/INFORME.md) y la decisión
     [ADR-0038](../adr/0038-no-extraer-bitacora-auditoria.md): **no extraer**, con
     condiciones de reversión.

**Endpoint en el contrato:**

| Método y ruta | Qué cambia |
|---|---|
| `GET /api/clinic/samples/{id}/audit/` | Nueva respuesta `503 AUDIT_UNAVAILABLE`, con `Retry-After` |

**Fuera del contrato público, y por qué:** el servicio extraído expone
`GET /internal/bitacora/{id}/` y `GET /salud/`. Son internos entre servicios:
- solo los usa `backend-clinic`;
- piden el secreto interno;
- no se despliegan, porque el ADR-0038 decide no extraer.

No están en `openapi.json`, que es el contrato de la API pública.

**Evidencia:**
- PR [#8](https://github.com/guillemc92/karyoumss/pull/8), con el CI en verde ([run 41767134233](https://github.com/guillemc92/karyoumss/actions/runs/41767134233)).
- Commits `3526e3e` (hipótesis), `44416bd`, `2e89e3c`, `27b9c6b`, `619211e` y `e1727ed`.

## Guion

### Funcionalidad 1 (≈ 3 min)

1. **Abrir el cariotipo** de un caso con metafase. Los cromosomas aparecen de pie. Si se
   pregunta por el antes, citar el E2E: ese 10 quedaba a 26,5° y ahora a 1,7°.
2. **Seleccionar un cromosoma** y pulsar «+5°» dos veces. Abrir la auditoría del caso:
   aparecen dos `ORIENT`, con el ajuste 0→5 y 5→10.
3. **Pulsar «Rotar vista».** Gira la vista; la orientación guardada no cambia.
4. **Plan B, si el stack falla en vivo:** correr
   `npx playwright test tests/auditado/cariograma-enderezado.spec.ts` en
   `frontend-clinic`, o mostrar el CI del PR #7.

### Funcionalidad 2 (≈ 4 min)

1. **Lanzar una corrida al empezar la demo**, porque tarda unos 2,5 min (90 s solo el seed):

       bench/e3/correr.sh una http colgado

   Docker Desktop tiene que estar abierto.
2. **Mientras corre:** enseñar `BitacoraPort`, el 503 en el contrato y la H1–H5 de
   `bench/e3/HIPOTESIS.md`, commiteadas antes de medir.
3. **Leer la tabla que imprime k6:**
   - en la fase *falla*, `bitacora` responde 503 en lugar de colgarse;
   - `control` sigue en 0 % de errores;
   - en la fase *después*, quedan 503 durante un rato: es la H4, que no se cumplió.
4. **Cerrar con el ADR-0038:** no se extrae; se conservan la interfaz y el banco.
5. **Después de la demo, borrar lo que dejó la corrida en vivo**, para no mezclarlo con
   las 20 medidas:

       rm bench/e3/resultados/http-colgado-0.json && git checkout -- bench/e3/resultados/tiempos.csv

6. **Plan B, sin Docker:** `py -3 bench/e3/resumir.py` reimprime las tablas desde los
   resultados guardados.

### Preguntas probables

| Pregunta | Respuesta corta |
|---|---|
| ¿Por qué no extraerla, si la latencia casi no sube (H1)? | Sube poco, pero la fiabilidad baja: sin ninguna falla, la forma extraída da 503 en 10 de 15 corridas, porque las protecciones cortan las respuestas lentas en frío. El aislamiento que buscaba la extracción se consigue más barato con permisos de base de datos (R1). |
| ¿Por qué falló la H4? | Por cómo se planteó, no por el sistema. Un breaker que espera 2 s puede rechazar hasta 2 s de una fase de 10 s, o sea un 20 %. El ≤ 1 % no cabía en esos parámetros desde antes de medir. Está declarado en el informe, y la R2 del ADR lo tiene en cuenta. |
| ¿Por qué se triplica el p95 de control si no da errores? | Hay dos explicaciones posibles: los hilos de gunicorn compartidos o la CPU (2 núcleos). Comparar «caído» con «colgado» las distingue, y está escrito como condición en la R2. |
| ¿Por qué el 503 no usa `application/problem+json` (RFC 9457)? | Se usó el formato de error que ya tiene el resto de la API, `{code, …}`. Cambiar solo esta respuesta la haría distinta de las demás. Migrar todos los errores a RFC 9457 sería otro cambio, con su propio diseño. |
| ¿Por qué los endpoints internos no están en el contrato? | Son internos, piden el secreto entre servicios y no se despliegan. Ver la sección anterior. |
