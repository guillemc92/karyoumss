# Comparación: la misma feature con y sin AI-DLC

**Autor:** Ing. Guillermo Mamani Chambi — Módulo 8, práctica individual
**Feature:** endpoint `GET /api/v1/inferencias/` en backend-ml, que expone el estado del límite de inferencias de la issue #2 (cuántas plazas hay, cuántas están ocupadas y cuánto se espera antes del 503).
**Ramas:** las dos parten del mismo commit, `f005e52` (release/8.1.0).

| | `feature-sin-aidlc` | `feature-con-aidlc` |
|---|---|---|
| Commit de la feature | `292bbb2` | `a29934e` (y `4fc0de6`, la instalación de AI-DLC) |
| Forma de trabajo | Pedido directo a Claude Code | AWS AI-DLC 2.11.0, perfil **Express**, aprobando yo cada compuerta |

## 1. Tiempo total de cada versión

| | Sin AI-DLC | Con AI-DLC |
|---|---|---|
| Tiempo de reloj | **1 min 44 s** | **≈ 52 min** (20:28:11 → 21:20:02) |

Desglose con AI-DLC, según `aidlc/spaces/default/intents/261020-estado-inferencias/audit/`:

| Etapa | Duración | Nota |
|---|---|---|
| Arranque (reiniciar Claude Code, activar hooks, inicializar) | ≈ 5 min | |
| Reverse engineering | ≈ 11,5 min | Escaneo de todo el monorepo por un subagente, ≈ 160 k tokens |
| Análisis de requisitos | ≈ 7,5 min | 3 preguntas |
| Generación de código | ≈ 21 min | Plan + subagente desarrollador (6 min 20 s, ≈ 117 k tokens); la sesión se compactó a mitad |
| Build and test | ≈ 3 min | |
| Deployment pipeline, deployment execution, observability | ≈ 1 min | Las tres saltadas con motivo: no hay CD, ni Dockerfile, ni monitorización |

El 22 % del tiempo se fue en entender el monorepo entero, para un cambio que toca un solo servicio.

## 2. Intervenciones y correcciones

| | Sin AI-DLC | Con AI-DLC |
|---|---|---|
| Intervenciones mías | **0** (aparte de pedir la feature) | **10** |
| Correcciones al contenido | 0 | 0 |
| Tropiezos de proceso del agente | 0 | 4 |

Las 10 intervenciones con AI-DLC:

- reiniciar Claude Code para que cargara los hooks;
- aprobar el cambio de `settings.local.json` (`disableAllHooks: false`);
- elegir el modo de respuesta («Guide me»);
- responder 3 preguntas de requisitos;
- aprobar 4 compuertas: reverse engineering, requisitos, código, build and test.

Los 4 tropiezos de proceso, del agente y no del código:

- un hook bloqueó un comando con `cd` y redirección;
- un `report` sin la respuesta textual;
- un salto de etapa sin `--reason`;
- un comando lanzado desde el directorio equivocado.

Todos se resolvieron sin cambiar el resultado.

Las 3 preguntas de requisitos son la diferencia de fondo. Cambiaron la feature:

1. **¿Quién puede consultarlo?** → protegido con el secreto interno (`X-Internal-Secret`, 403 si no coincide).
2. **¿Se cuentan las peticiones en espera?** → sí, un quinto campo `en_espera`.
3. **¿Y si falta el secreto?** → backend-ml arranca igual y solo este endpoint responde 503.

Sin AI-DLC nadie hizo esas preguntas. La versión directa quedó **pública**, como `/health/`, y con 4 campos. No es un error en sí, pero es una decisión de seguridad que se tomó por omisión.

## 3. Artefactos que quedaron en el repo

| | Sin AI-DLC | Con AI-DLC |
|---|---|---|
| Código y pruebas | 4 archivos, +125 líneas | 5 archivos, +317 líneas |
| Documentación del proceso | Ninguna | 28 archivos, +2.161 líneas en `aidlc/` |
| Configuración del framework | — | 323 archivos en `.claude/` y `aidlc/` (commit `4fc0de6`) |

**Sobre `.aidlc-version`:** la versión 2.11.0 no crea ese archivo. Guarda la versión instalada en `.claude/tools/data/aidlc-stamp.json` (`"frameworkVersion": "2.11.0"`), que está versionado junto con `aidlc-manifest.json`.

Lo que quedó en `aidlc/`:

- **`codekb/karyoumss-main/`**: 9 documentos del monorepo (arquitectura, estructura, stack, dependencias, calidad del código, API, inventario de componentes). Se reutilizan en las próximas features.
- **`intents/261020-estado-inferencias/`**:
  - `requirements.md`, con FR1–FR4, NFR1–NFR3 y criterios Dado/Cuando/Entonces;
  - las preguntas con mis respuestas;
  - el plan de código con su *Testing Contract*;
  - las instrucciones de prueba;
  - `code-summary.md` y `traceability.json` (requisito → archivo);
  - los resultados de build and test con su matriz de verificación;
  - el registro de auditoría con la hora de cada evento.

## 4. ¿Pasan las pruebas en ambas?

Sí, en las dos.

| | Sin AI-DLC | Con AI-DLC |
|---|---|---|
| Pruebas nuevas | 7 | 11 |
| Suite completa de backend-ml | 72 / 72 en verde | 76 / 76 en verde |
| Cobertura del código nuevo | ≥ 90 % (RN-09) | 100 % en `concurrencia.py` y `main.py` |

Las 4 pruebas de más con AI-DLC cubren lo que solo existe en esa versión: el 403 sin cabecera, el 403 con secreto incorrecto, el 503 sin secreto y `en_espera` con hilos.

## 5. Qué salió mejor y qué peor

**Mejor con AI-DLC**

- **Las preguntas.** Sacaron a la luz una decisión de seguridad (exponer el estado interno sin autenticación) que en la versión directa nadie tomó conscientemente.
- **La trazabilidad.** Cada requisito apunta a un archivo y a una prueba, y queda escrito *por qué* se hizo así. En un proyecto clínico con auditoría, eso vale.
- **La verificación.** Build and test volvió a ejecutar la suite completa por su cuenta en vez de fiarse del informe del desarrollador.
- **El conocimiento del repo** (`codekb/`) queda para las siguientes features.

**Peor con AI-DLC**

- **30 veces más tiempo** (52 min frente a 1 min 44 s) para una feature de ≈ 100 líneas de código.
- **Coste fijo alto aun en Express.** El reverse engineering escanea todo el monorepo (≈ 160 k tokens) aunque el cambio toque un solo archivo de un solo servicio.
- **Fricción de la herramienta.** Hay que reiniciar Claude Code y aprobar hooks, y hay comandos que los hooks bloquean. Las 3 etapas de operación se abren solo para saltarlas, porque el proyecto no tiene CD ni monitorización.
- **El ruido:** 2.161 líneas de documentación para 317 de código.

## 6. ¿Usaría AI-DLC? ¿Por qué?

**Sí, pero no para todo.**

- **Lo usaría** cuando la feature tiene decisiones abiertas: seguridad, datos clínicos (RN-03), varios servicios, o requisitos que el docente o el laboratorio van a auditar. Ahí las preguntas y la trazabilidad valen más que el tiempo que cuestan, y encajan con el SDD que ya seguimos en BIOMED (BRD → FSD → spec → código).
- **No lo usaría** para cambios pequeños y bien definidos dentro de un servicio, como este. El trabajo directo los resuelve en minutos y con la suite en verde. Lo que AI-DLC aportó aquí lo habría conseguido igual pidiendo «antes de programar, hazme las preguntas que haga falta resolver».

Lo más útil del experimento fue ver que la diferencia no estuvo en el código, que en los dos casos pasó sus pruebas. Estuvo en **qué se decidió antes de escribirlo**.
