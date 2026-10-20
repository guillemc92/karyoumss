# Práctica: AI-DLC de AWS con y sin herramienta

## 1. Datos

- **Modalidad:** individual
- **Repositorio:** https://github.com/guillemc92/karyoumss
- **Rama sin herramienta (A):** [`feature-sin-aidlc`](https://github.com/guillemc92/karyoumss/tree/feature-sin-aidlc)
- **Rama con herramienta (B):** [`feature-con-aidlc`](https://github.com/guillemc92/karyoumss/tree/feature-con-aidlc)
- **Video (opcional):** no

**Responsables:**

| Integrante | Qué hizo | Commits o PR |
| :---- | :---- | :---- |
| Ing. Guillermo Mamani Chambi | Todo: las dos versiones, la aprobación de las puertas y la comparación | A: `292bbb2` · B: `4fc0de6`, `a29934e` y los commits de este documento |

Las dos ramas parten del mismo commit, `f005e52` (release/8.1.0), para que la comparación sea justa.

## 2. El feature

`GET /api/v1/inferencias/` en **backend-ml** (FastAPI) devuelve el estado del límite de inferencias simultáneas introducido en la issue #2.

- **Entrada:** ninguna. En la versión B, además, la cabecera `X-Internal-Secret`.
- **Salida:** JSON con estos campos:
  - `maximo`: plazas totales (`ML_MAX_INFERENCIAS`);
  - `en_curso`: plazas ocupadas;
  - `libres`: `maximo − en_curso`;
  - `espera_max_s`: lo que se espera antes del 503.

  La versión B añade `en_espera`, las peticiones que esperan turno.
- **Comportamiento:** la consulta **no pasa por el semáforo**. Responde aunque el límite esté lleno y no ocupa plaza.
- **Errores (solo en B):**
  - 403 si la cabecera falta o es incorrecta;
  - 503 si backend-ml no tiene `INTERNAL_SERVICE_SECRET` configurado. El resto del servicio sigue funcionando.
- **Criterio de aceptación:**
  - con una inferencia ocupando la única plaza, la consulta responde al instante con `en_curso = 1` y `libres = 0`;
  - si la inferencia falla, los contadores vuelven a su valor;
  - las pruebas de backend-ml que ya existían siguen en verde.

## 3. Versión A: sin la herramienta

- **Cómo trabajé:** con un asistente de IA directo (Claude Code), con un único pedido y TDD: primero las pruebas en rojo y después la implementación. No hubo preguntas, plan ni puertas.
- **Resultado:** rama [`feature-sin-aidlc`](https://github.com/guillemc92/karyoumss/tree/feature-sin-aidlc), commit `292bbb2`. Toca 4 archivos (+125 líneas): `concurrencia.py`, `main.py`, `schemas.py` y 7 pruebas nuevas.

## 4. Versión B: con AI-DLC de AWS 2.11.0 (perfil Express)

- **Comando usado:** `/aidlc express Añadir a backend-ml un endpoint GET /api/v1/inferencias/ que devuelva el estado del límite de inferencias: maximo, en_curso, libres y espera_max_s, sin pasar por el semáforo, con sus pruebas.`
- **Salida de `aidlc version`:** `aidlc 2.11.0 (runtime 2.11.0)`
- **Puertas revisadas:**

  | Puerta | Resultado | Request Changes |
  | :---- | :---- | :---- |
  | Reverse Engineering | Approve | Ninguno |
  | Requirements Analysis | Approve, tras responder 3 preguntas: Q1 B, Q2 B, Q3 B | Ninguno |
  | Code Generation | Approve. La aprobación del plan viene apagada en Express, así que solo hubo esta puerta final | Ninguno |
  | Build and Test | Approve | Ninguno |

  Las 3 etapas de operación (Deployment Pipeline, Deployment Execution, Observability Setup) se **saltaron con motivo registrado**: el proyecto no tiene pipeline de CD, Dockerfile ni pila de monitorización.

  No usé Request Changes en ninguna puerta. Lo que cambió el feature fueron las respuestas a las 3 preguntas de requisitos:
  1. protegerlo con el secreto interno;
  2. añadir `en_espera`;
  3. que backend-ml arranque igual sin el secreto.
- **Artefactos versionados** (rama B):
  - `aidlc/spaces/default/intents/261020-estado-inferencias/`:
    - `aidlc-state.md`;
    - la auditoría en `audit/`;
    - `inception/requirements-analysis/requirements.md` y las preguntas con mis respuestas;
    - en `construction/code-generation/`: `code-generation-plan.md`, `unit-test-instructions.md`, `code-summary.md` y `traceability.json`;
    - en `construction/build-and-test/`: `test-results.md`, el resumen y la trazabilidad final.
  - `aidlc/spaces/default/codekb/karyoumss-main/`: 9 documentos del monorepo generados por Reverse Engineering.
  - **`.aidlc-version`:** la versión 2.11.0 no crea ese archivo. La versión instalada queda registrada en `.claude/tools/data/aidlc-stamp.json` (`"frameworkVersion": "2.11.0"`), que está versionado junto con `aidlc-manifest.json` en el commit `4fc0de6`.

## 5. Comparación

| Aspecto | A · sin herramienta | B · con AI-DLC de AWS |
| :---- | :---- | :---- |
| Tiempo total | **1 min 44 s** (20:23:48 → 20:25:32) | **≈ 52 min** (20:28:11 → 21:20:02). Reverse Engineering ≈ 11,5 min; requisitos ≈ 7,5 min; código ≈ 21 min; Build and Test ≈ 3 min; arranque y cierre, el resto |
| Veces que tuve que intervenir o corregir | **0** intervenciones y 0 correcciones | **10** intervenciones: reiniciar Claude Code, aprobar el cambio de hooks, elegir el modo de respuesta, 3 respuestas y 4 puertas. **0** correcciones del resultado. Hubo 4 tropiezos de proceso del agente con los hooks y los comandos del motor, resueltos sin cambiar el código |
| Artefactos que quedaron en el repositorio | 4 archivos de código y pruebas (+125 líneas); ninguna documentación del proceso | 5 archivos de código y pruebas (+317 líneas) y 28 archivos en `aidlc/` (+2.161 líneas): requisitos, plan, trazabilidad, resultados y auditoría. Antes, 323 archivos de configuración de la herramienta |
| ¿Las pruebas pasan? (ejecutadas por mí) | Sí: 7 nuevas, **72 / 72** en verde en backend-ml, código nuevo ≥ 90 % | Sí: 11 nuevas, **76 / 76** en verde en backend-ml, 100 % de cobertura en `concurrencia.py` y `main.py` |
| Qué salió mejor | Rapidez. Para un cambio de este tamaño, el resultado funciona y está probado en menos de 2 minutos | Las preguntas obligaron a decidir la **seguridad** del endpoint y a contar las peticiones en espera. Cada requisito quedó trazado a un archivo y a una prueba |
| Qué salió peor | Las decisiones de diseño se tomaron solas: el endpoint quedó **público**, igual que `/health/`, sin que nadie lo preguntara | 30 veces más tiempo. Reverse Engineering escanea todo el monorepo (≈ 160 k tokens) para un cambio en un solo servicio. Hay que reiniciar y aprobar hooks. Las etapas de operación se abren solo para saltarlas |

## 6. Conclusiones

1. **¿Qué decisiones tomó el agente sin que yo las viera?**
   - **En A:**
     - dejar el endpoint sin autenticación;
     - no contar las peticiones en espera;
     - cómo y dónde llevar los contadores (un lock aparte del semáforo);
     - el número y el tipo de las pruebas.

     Ninguna me la consultó.
   - **En B:** las decisiones de *qué* construir quedaron a la vista en las preguntas. Siguieron siendo invisibles las de *cómo*:
     - el texto del error 403 (copiado de backend-admin);
     - bajar `en_espera` en un `finally` alrededor del `acquire`;
     - saltar las tres etapas de operación;
     - qué contaba como «una prueba por requisito».

     Están escritas en `code-summary.md` y en la auditoría, pero las aprobé sin discutirlas.
2. **¿Cuántas puertas aprobé por inercia?** Entre que me mostraron cada puerta y que la aprobé pasaron entre ~8 s y ~45 s, según la auditoría. En Reverse Engineering y Requirements revisé el contenido porque acababa de responder sus preguntas. **Code Generation y Build and Test las aprobé por inercia (2 de 4):** me fié del resumen y de que las pruebas estaban en verde, sin leer el código en ese momento.
3. **¿Qué evidencia explica por qué se hizo así?**
   - **En B, la auditoría de AI-DLC.** Lleva la hora de cada evento, mis respuestas con su opción, los requisitos con criterios Dado/Cuando/Entonces y la trazabilidad de requisito a archivo.
   - **En A** solo queda el mensaje de commit. No hay PR en ninguna de las dos ramas, así que el historial del PR no aporta nada aquí.
   - Una persona que llegue después entiende el *por qué* del 403 o de `en_espera` solo en B.
4. **¿Para qué tamaño de cambio vale la pena?**
   - **Vale la pena** para cambios con decisiones abiertas: seguridad, datos clínicos (RN-03), varios servicios, o requisitos que alguien va a auditar.
   - **No vale la pena** para cambios pequeños y bien delimitados en un solo servicio, como este. El coste fijo (Reverse Engineering del repo entero, hooks, puertas) supera al trabajo en sí.
5. **¿Lo usaría en mi proyecto? ¿Por qué?** **Sí, de forma selectiva.**
   - En BIOMED ya trabajamos con SDD (BRD → FSD → spec → código), y AI-DLC encaja con eso para las features clínicas, donde la trazabilidad y las preguntas previas valen más que el tiempo.
   - Para los cambios pequeños seguiría con el asistente directo, con una regla: pedirle primero las preguntas que haga falta resolver. Lo que AI-DLC aportó aquí no fue mejor código, porque las dos versiones pasaron sus pruebas. Fueron las **decisiones tomadas antes de escribirlo**.

## 7. Antes de entregar

- [x] Las dos ramas están en el repositorio y las pruebas pasan en ambas (A: 72/72, B: 76/76).
- [x] `aidlc/` está versionado en la rama B. La versión de AI-DLC está en `.claude/tools/data/aidlc-stamp.json`, porque la 2.11.0 no genera `.aidlc-version` (ver sección 4).
- [x] No hay secretos, `.env` ni archivos `*.local.json` en los commits: solo las plantillas `backend-ml/.env.example` y `.claude/settings.local.json.example`, sin valores reales.
- [x] Trabajo individual: tabla de responsables completa.
