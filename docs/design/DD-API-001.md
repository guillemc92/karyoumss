# DD-API-001 — Contrato OpenAPI generado desde el código y validado en CI

| Campo | Valor |
|---|---|
| **ID** | DD-API-001 |
| **Origen** | Módulo 8, Demo 2 (lun 26/10, `release/8.2.0`): consigna de Classroom, sesión 5 (partes B y C) y plan del módulo (actividad 8, «Contrato OpenAPI validado en CI») |
| **Servicios** | backend-clinic (Django + DRF), backend-ml (FastAPI) |
| **Reglas** | RN-09 (cobertura ≥ 90 %) · DD-KARYO-007 (sus endpoints tienen que estar en el contrato) |
| **Estado** | **Implementado** el 2026-10-24 (aprobado ese mismo día) · verificación en §6 |
| **Fecha** | 2026-10-24 |

## 1. Por qué

La consigna de la Demo 2 pide tres cosas:

- **El contrato sale del código.** El backend lo genera, un comando lo exporta a
  `openapi.json` y el archivo se sube al repositorio.
- **Ese contrato incluye los endpoints de las funcionalidades que se presentan.** La
  que se presenta es la corrección manual de DD-KARYO-007 (FSD-UC-003).
- **Un workflow en `.github/workflows/` lo comprueba en cada pull request:**
  - *drift* (que el archivo coincida con lo que genera el código) y Spectral, obligatorios;
  - oasdiff y Schemathesis, opcionales y suman.

La pregunta fija de la demo es: *«Rompe tu contrato y muestra qué detecta el CI»*.

**Hoy no hay nada de eso.** backend-clinic no genera contrato, el repositorio no
tiene `.github/` y nadie compara la API con su descripción.

## 2. Decisiones

### D1 · Dos contratos, uno por servicio
| Servicio | Generador | Archivo |
|---|---|---|
| backend-clinic, la API del producto (la usa el frontend) | `drf-spectacular` a partir de vistas y serializers | `backend-clinic/openapi.json` |
| backend-ml, la API interna de inferencia | FastAPI, a partir de sus modelos Pydantic | `backend-ml/openapi.json` |

backend-admin queda fuera de esta entrega: no tiene endpoints de la funcionalidad que se
presenta.

### D2 · Los endpoints de DD-KARYO-007 se describen a mano; el resto, como los infiere el generador
Las vistas de backend-clinic son `APIView` que leen `request.data` sin un
serializer de entrada. Así `drf-spectacular` no sabe qué cuerpo esperan ni qué errores
devuelven.

- **Los endpoints de la funcionalidad presentada llevan `@extend_schema`** con el cuerpo
  de entrada, la respuesta y cada código de error con su `code`. Son: contornos,
  objetos, descartar, separar, deshacer y orientar.
- **El resto queda como lo infiere el generador.** Describir a mano las ~30 vistas no
  cabe antes del lunes; queda declarado y la deuda se mide (D4).

### D3 · Un comando por servicio, y el archivo es determinista
- **backend-clinic:** `python manage.py spectacular --file openapi.json --validate`.
- **backend-ml:** `python -m app.exportar_openapi`, que escribe `app.openapi()` con las
  claves ordenadas.

Ejecutados dos veces seguidas, cada comando debe dar el mismo archivo byte a byte. Si
no, el *drift* fallaría sin que nadie haya cambiado nada.

### D4 · El workflow `contrato-openapi.yml`
Se ejecuta en cada `pull_request` y en cada push a `release/**`.

| Paso | Herramienta | Falla si… | Consigna |
|---|---|---|---|
| Drift | exportar y `git diff --exit-code` | el archivo del repositorio no es el que genera el código | Obligatorio |
| Lint | Spectral, `.spectral.yaml` que extiende `spectral:oas` | hay algún **error**; los avisos se cuentan en el log, pero no fallan (D2) | Obligatorio |
| Cambios incompatibles | `oasdiff breaking` contra la rama base del PR | se borra un campo, un endpoint o un código de respuesta que ya existía | Opcional |
| Conformidad | Schemathesis contra backend-ml levantado en el job | un endpoint responde 5xx, o con una forma que no está en su contrato | Opcional |

- **Schemathesis solo contra backend-ml.** Arranca sin base de datos ni login, y sus
  endpoints de edición (`split`, `join`, `contours`) son justo los de la funcionalidad.
  Contra backend-clinic haría falta una base de datos con datos y un JWT válido en el
  job: queda fuera de esta entrega.
- **Secretos del job.** Los secretos obligatorios (issue #4) van al job con valores de
  prueba generados en el propio job; nunca se usan los del `.env`.

### D5 · La demostración: romper el contrato a propósito
Desde una rama, en un pull request:

1. Se renombra un campo que la funcionalidad usa, `contour` → `silueta` en
   `ChromosomeSerializer`, **sin regenerar** el contrato. **El drift falla.**
2. Se regenera el contrato y se sube. El drift pasa, pero **oasdiff marca el cambio como
   incompatible**: desaparece una propiedad de la respuesta, que el frontend lee.
3. Se deshace y todo vuelve a verde.

El mismo guion queda escrito en `docs/demos/demo-2.md` para repetirlo en vivo.

## 3. Pruebas (RN-09)
- **Contrato de backend-clinic:** una prueba genera el esquema y comprueba que están
  todos los endpoints de DD-KARYO-007, con sus códigos de error. Si alguien borra un
  `@extend_schema`, falla en local antes de llegar al CI.
- **Contrato de backend-ml:** la misma prueba, para `split`, `join` y `contours`.
- **Determinismo:** exportar dos veces da el mismo archivo.
- **El workflow en sí:** se prueba con un pull request de verdad en GitHub, con el
  renombrado de D5.
  - **Control positivo:** el CI tiene que fallar.
  - **Control negativo:** sin el cambio, tiene que pasar.

## 4. Plan
| # | Tarea | Estimación |
|---|---|---|
| T1 | `drf-spectacular` en backend-clinic, `@extend_schema` en los endpoints de DD-KARYO-007, exportar y probar | 2 h |
| T2 | Exportador de backend-ml y su prueba | 0,5 h |
| T3 | `.spectral.yaml` y workflow con drift + Spectral | 1 h |
| T4 | oasdiff y Schemathesis (opcionales) | 1,5 h |
| T5 | PR de prueba con D5 (falla y luego pasa), `docs/demos/demo-2.md`, `8.2.0-aportes.md`, `release/8.2.0` | 1 h |

## 5. Fuera de alcance, declarado
- Describir a mano todas las vistas de backend-clinic (D2).
- Contrato de backend-admin.
- Schemathesis contra backend-clinic (D4).
- Prism (simulación) y Pact (contratos cliente-servidor), que el sílabo menciona pero la
  consigna de la demo no pide.

## 6. Verificación (2026-10-24)

- **CI en GitHub, en verde** con el contrato correcto: [run 40055443260](https://github.com/guillemc92/karyoumss/actions/runs/40055443260).
- **El CI detecta la ruptura** (PR de demostración #6, D5):
  - quitar `contour` sin regenerar → **falla el drift** ([run 40055492310](https://github.com/guillemc92/karyoumss/actions/runs/40055492310));
  - regenerar → el drift pasa y **oasdiff marca 8 endpoints que pierden `contour`** ([run 40055614994](https://github.com/guillemc92/karyoumss/actions/runs/40055614994)).
- **Dos fallos del propio CI**, cazados antes de la demo y corregidos:
  - en Linux, drf-spectacular autodetectaba otro prefijo y los `operationId` cambiaban → `SCHEMA_PATH_PREFIX` fijo;
  - la action de oasdiff corre en un contenedor que no ve `$RUNNER_TEMP` → el contrato base va dentro del espacio de trabajo.
- **Limitación de Schemathesis**, que queda declarada: casi todos los datos que genera
  se rechazan con 400, porque `bbox`, `linea` y `contour` viajan como texto JSON dentro
  de un formulario y el contrato solo puede decir «texto». Comprueba sobre todo que no
  haya 5xx y que los errores respeten su forma, no los caminos de éxito.
- **Pruebas:** backend-clinic 1111/1111 (90,80 %), backend-ml 117/117 (90 %).

