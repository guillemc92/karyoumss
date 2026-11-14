# DD-OBS-001 — Trazas distribuidas con OpenTelemetry y prueba de carga con k6

| Campo | Valor |
|---|---|
| **ID** | DD-OBS-001 |
| **ADR origen** | [ADR-0007](../adr/0007-microservicio-inferencia.md) (microservicio de inferencia) y [ADR-0015](../adr/0015-arquitectura-clinica-django.md) (backend clínico) |
| **Parte de** | [DD-OPS-001](DD-OPS-001.md) (el stack de producción sobre el que corre) |
| **Casos de uso (FSD)** | FSD-UC-002 (segmentación y clasificación) y FSD-UC-007 (modo degradado); NFR-001 (tiempo de segmentación + clasificación) y NFR-004 (monitoreo) |
| **Reglas** | RN-03 (sin PII), RN-07 (degradación elegante), RN-09 (cobertura ≥ 90 %) |
| **Estado** | Aprobado por el autor el 2026-11-12. En implementación |
| **Fecha** | 2026-11-12 |

## 1. Problema

El sistema no puede responder hoy a esta pregunta: **«¿en qué tramo se va el
tiempo de una petición lenta?»**.

Procesar una metafase cruza tres procesos: `web` (Caddy) → `backend-clinic`
(Django) → `backend-ml` (FastAPI). Dentro de `backend-ml` hay cuatro tramos:
esperar turno en el límite de inferencias, segmentar, clasificar y sacar los
contornos. De esa petición hoy solo se conoce la duración total, medida desde
fuera. En DD-OPS-001 se anotó «segmentar tarda ~19 s en CPU», pero nadie puede
decir cuánto de eso es segmentar y cuánto es clasificar o esperar.

La Demo 4 del Módulo 8 lo pide como pregunta fija: mostrar el p95 con k6 y
explicar una traza de OpenTelemetry abierta en Grafana (Explore → Tempo).

## 2. Decisiones

### D1 · Trazas con OpenTelemetry, exportadas por OTLP/HTTP directo a Tempo

- `backend-clinic` y `backend-ml` llevan el SDK de OpenTelemetry (1.45.2) y
  exportan por OTLP/HTTP a `tempo:4318`.
- **Sin Collector.** Con dos servicios y un solo destino, un Collector sería una
  pieza más que mantener y no aporta nada. Se añadirá si un día hay más destinos
  (métricas, logs) o hace falta muestreo por cola.
- `backend-admin` **no se instrumenta** en este DD. La petición que se analiza no
  pasa por él: `backend-clinic` valida el JWT en local (ADR-0017). Se declara
  como pendiente.

### D2 · Apagado por omisión; se enciende con una variable

La instrumentación se activa solo si existe `OTEL_EXPORTER_OTLP_ENDPOINT`.

- **Sin la variable** (desarrollo, tests, el stack sin perfil): no se crea
  proveedor ni exportador, y no se instrumenta nada. El comportamiento es el de
  hoy.
- **Si el paquete no está instalado**, el servicio arranca igual (RN-07). Es la
  misma regla que ya siguen `openai` y `langgraph`.
- **Si Tempo se cae** con la variable puesta, las peticiones no fallan. El
  exportador por lotes descarta las trazas que no pudo enviar.

### D3 · Qué se instrumenta

| Servicio | Automático | Manual |
|---|---|---|
| `backend-clinic` | Django (una traza por petición), `httpx` (la llamada a `backend-ml`, que propaga `traceparent`) y `sqlite3` (cada consulta) | — |
| `backend-ml` | FastAPI (continúa la traza que llega) | Un tramo por etapa: `esperar_turno`, `segmentar`, `clasificar` y `contornos` |

Los tramos manuales son la razón de este DD. Sin ellos la traza diría solo
«`backend-ml` tardó 19 s», que es lo que ya se sabía.

### D4 · Sin PII en las trazas (RN-03)

- **Rutas:** llevan el id interno de la muestra (un UUID), nunca el CHN ni
  nombres.
- **Cabeceras y cuerpos:** no se capturan. Es el comportamiento por omisión y no
  se activa ninguna opción de captura. Una prueba lo fija.
- **SQL:** se registra la sentencia con sus marcadores (`?`), **sin los
  parámetros**. Una prueba lo fija.
- **Atributos de los tramos manuales:** solo números (cromosomas encontrados,
  ancho y alto de la imagen). Nada que venga del paciente.
- **Dónde quedan:** en el volumen local de Tempo. No salen de la máquina.

### D5 · Tempo y Grafana, con el perfil `obs`

    docker compose --profile obs up -d --wait

- **Tempo** (una sola instancia, almacenamiento local en un volumen) y **Grafana**
  con la fuente de datos Tempo ya configurada desde un archivo.
- **Imágenes fijadas por digest,** como el resto del stack.
- **Grafana solo en `127.0.0.1:3000`,** con acceso anónimo de rol Editor. El rol
  Editor hace falta para usar Explore. Es aceptable porque no sale de la máquina
  local; en un despliegue real iría detrás del SSO, y se declara.
- **Sin el perfil,** el stack de DD-OPS-001 no cambia: mismos servicios y mismo
  `up -d --wait`.

### D6 · La prueba de carga con k6

`bench/demo4/carga.js`, con el perfil `carga`. Lanza dos tipos de petición a la
vez, a ritmo fijo y contra `web`, es decir, por la misma entrada que usa una
persona:

| Petición | Ritmo | Para qué |
|---|---|---|
| `GET /api/clinic/samples/{id}/karyotype/` | 5 por segundo | La lectura habitual: el p95 «normal» |
| `POST /api/clinic/samples/{id}/process/` | 1 cada 10 s | La lenta: cruza los tres servicios y hace la inferencia |

- **Datos:** un comando de siembra crea las muestras con una metafase
  **sintética** (dibujada con OpenCV, sin datos de pacientes) y deja los ids y un
  token en un volumen. Es el mismo mecanismo que usó el E3.
- **Salida:** el p50, el p95 y el máximo de cada tipo de petición.
- **Cómo se llega a la traza lenta:** en Grafana → Explore → Tempo, con la
  consulta `{ resource.service.name = "backend-clinic" && duration > 5s }`.

### D7 · Una hipótesis antes de mirar

Se fija antes de medir, para que la traza la confirme o la desmienta:

> **H1.** En un `POST …/process/`, más del 80 % del tiempo está dentro de
> `backend-ml`, y dentro de él el tramo más largo es `clasificar` (EfficientNet-B3
> en CPU, un recorte por cromosoma), no `segmentar`.
>
> **H2.** Con `ML_MAX_INFERENCIAS=1`, cuando llegan dos `process` a la vez, el
> segundo pasa en `esperar_turno` casi lo mismo que tarda la inferencia del
> primero.

## 3. Criterios de aceptación

1. Con `--profile obs`, el stack levanta con `up -d --wait` y Tempo y Grafana
   quedan `healthy`. Sin el perfil, el stack levanta igual que en la 8.3.0.
2. Un `POST …/process/` produce **una sola traza** con tramos de `backend-clinic`
   y de `backend-ml`, todos con el mismo `trace_id`.
3. Esa traza contiene los tramos `esperar_turno`, `segmentar`, `clasificar` y
   `contornos`, con su duración.
4. Sin `OTEL_EXPORTER_OTLP_ENDPOINT`, no se exporta nada y las suites de hoy pasan
   sin cambios.
5. Ningún tramo lleva parámetros de SQL, cabeceras ni cuerpos (D4), y hay pruebas
   que lo comprueban.
6. `k6` informa el p95 de las dos peticiones, y la traza lenta se abre desde
   Grafana → Explore → Tempo.
7. El CI de imágenes (hadolint, Trivy y `up --wait` con humo) sigue en verde.
8. La cobertura de los módulos nuevos es ≥ 90 % (RN-09).

## 4. Riesgos

| Riesgo | Mitigación |
|---|---|
| gunicorn bifurca procesos y el exportador por lotes usa un hilo, que no sobrevive al `fork` | Se configura en `wsgi.py`. Sin `--preload` (así está hoy), `wsgi.py` se ejecuta en cada worker, después del `fork` |
| Las dependencias nuevas traen CVE y Trivy rompe el CI | Versiones fijas; si aparece algo sin arreglo, va a ADR-0039 como el resto |
| La instrumentación de `sqlite3` añade latencia a las lecturas | Se mide: p95 de la lectura con y sin trazas. Si sube más de un 10 %, se quita `sqlite3` y se dice |
| Tempo y Grafana pesan en una máquina de 2 núcleos y cambian el p95 | Van en un perfil aparte; el p95 se informa con las trazas encendidas, que es la condición de la demo, y se declara |
| H1 o H2 salen falsas | Es un resultado: se escribe lo que muestre la traza |

## 5. Fuera de alcance

- Métricas (Prometheus) y logs con `trace_id`. La pregunta de la demo es sobre
  trazas.
- Instrumentar `backend-admin`, el navegador o Caddy.
- Muestreo: se guardan todas las trazas. En producción habría que muestrear.
- Alertas y paneles. Solo Explore.

## 6. Pruebas (RN-09 ≥ 90 %)

Las pruebas usan un exportador en memoria; ninguna necesita Tempo.

- `observabilidad.configurar()`:
  - sin la variable → devuelve `False` y no cambia el proveedor;
  - con la variable → devuelve `True` y el recurso lleva `service.name`;
  - llamada dos veces → no instrumenta dos veces;
  - sin el paquete instalado → devuelve `False` y no lanza.
- `backend-ml`: una petición a `/api/v1/segment/` con la traza encendida produce
  los cuatro tramos, hijos del tramo de la petición. Si llega un `traceparent`,
  el `trace_id` se conserva.
- `backend-clinic`: la llamada a `backend-ml` sale con `traceparent`, y los tramos
  de SQL no llevan parámetros.
- **Sin PII:** ningún atributo de ningún tramo contiene el CHN de la muestra de
  prueba.

## 7. Plan

| # | Tarea | Sale |
|---|---|---|
| T1 | `observabilidad.py` en los dos backends, con sus pruebas | `configurar()` probado, apagado por omisión |
| T2 | Tramos manuales en `backend-ml` y propagación desde `backend-clinic` | Una traza con los tres servicios, en una prueba |
| T3 | Tempo y Grafana en `compose.yaml` (perfil `obs`), con sus archivos en `deploy/obs/` | `up --wait` con el perfil; la traza se ve en Grafana |
| T4 | Siembra sintética y `bench/demo4/carga.js` (perfil `carga`) | p95 de las dos peticiones |
| T5 | Medir: p95, la traza lenta, H1 y H2, y el coste de las trazas | `bench/demo4/INFORME.md` con una captura de la traza |
| T6 | CI: hadolint, Trivy y humo en verde con las dependencias nuevas | El workflow pasa |

## 8. Lo que cambió al implementar

Se anota aquí en vez de reescribir las decisiones, para que se vea qué se
supuso y qué resultó.

- **Los tramos manuales son tres, no cuatro** (D3). Los contornos no son una etapa
  aparte: `segmentar` ya los devuelve. Quedan `esperar_turno`, `segmentar` y
  `clasificar`.
- **La variable del stack es `BIOMED_TRAZAS`** (D2 y D5). Compose no puede poner
  una variable solo cuando un perfil está activo, así que el stack pasa
  `OTEL_EXPORTER_OTLP_ENDPOINT: ${BIOMED_TRAZAS:-}`; vacío significa apagado. Se
  enciende así:

      BIOMED_TRAZAS=http://tempo:4318 docker compose --profile obs up -d --wait

- **La URL se guarda sin su cadena de consulta** (D4). La instrumentación de
  Django guarda la URL completa, y la búsqueda de muestras viaja ahí
  (`?search=…`). Un gancho al abrir el tramo la recorta. No estaba previsto en el
  diseño: lo destapó la prueba de PII.
- **`backend-ml` se instrumenta una sola vez por proceso.** La librería no deja
  instrumentar dos veces la misma app de FastAPI, y además hay que hacerlo antes
  de la primera petición, porque Starlette guarda la cadena de middlewares ya
  armada. `configurar()` la obliga a rearmarse.
- **Los tramos de SQL solo aparecen en conexiones abiertas después de encender
  las trazas.** En producción es siempre así (se enciende en `wsgi.py`, antes de
  la primera consulta). En las pruebas la conexión ya existe y se envuelve a
  mano con el mismo instrumentador.
- **«Procesar» llega en parejas** (D6), no «1 cada 10 s». Dos peticiones a la vez
  en cada ciclo: una entra y la otra espera su turno. Es lo que H2 necesita ver,
  y a un ritmo fijo de 1 cada 10 s la cola solo crecería.
- **Un job más, `tempo-volumen`** (D5). Tempo corre como el usuario 10001 y el
  volumen nace de root. El job le da la carpeta antes de arrancar, con la misma
  imagen que ya usa el job `secretos`.
- **`web` entra en `DJANGO_ALLOWED_HOSTS`.** k6 llama a `http://web:8080` desde la
  red de Docker y Django rechazaba ese nombre de host con un 400. Desde un
  navegador, que usa `localhost`, no se veía.
- **Parches del sistema en las tres imágenes de Python.** Al pasar Trivy
  aparecieron 4 HIGH con parche en `apt` y `zlib1g`, publicados después de la
  Demo 3. No vienen de las dependencias de este diseño: están en la imagen base,
  que no se reconstruye desde el 21/10. Se añadió `apt-get upgrade` a la etapa
  final, como ya hacía la imagen de `web` con `apk upgrade` (ADR-0039 D1).
- **Una prueba de humo propia, `deploy/humo-trazas.sh`,** que el CI corre con el
  perfil `obs`: hace un «procesar» y le pregunta a Tempo si la traza cruza los dos
  servicios, si tiene los tres tramos y si no guarda el texto de búsqueda.

## 9. Resultados (2026-11-12)

El detalle, con las capturas de Grafana, está en
[`bench/demo4/INFORME.md`](../../bench/demo4/INFORME.md).

| Criterio (§3) | Resultado |
|---|---|
| 1 · Levanta con y sin el perfil `obs` | Sí. Con el perfil, todo `healthy` en 77 s |
| 2 · Una sola traza con los dos servicios | Sí: 68 tramos con el mismo `trace_id` |
| 3 · Los tramos manuales, con su duración | Sí: `esperar_turno`, `segmentar` y `clasificar` |
| 4 · Sin la variable no cambia nada | Sí. backend-clinic: 1.217 pruebas en verde, 91,60 % |
| 5 · Sin PII, con pruebas | Sí: URL sin consulta, SQL sin parámetros, sin token |
| 6 · p95 con k6 y la traza en Grafana | Lectura: p95 de 431 ms. Procesar: 53,8 s, con 50 % de errores que la traza explica |
| 8 · Cobertura de los módulos nuevos | 100 % en los dos `observabilidad.py` y en `sembrar_carga.py` |

**Las hipótesis:**
- **H1 se cumple.** `clasificar` es el 98,5 % de la petición; `segmentar`, el 0,9 %.
- **H2 no se cumple.** El segundo «procesar» no espera lo que tarda el primero:
  espera 25 s (`ML_ESPERA_MAX_S`) y falla con 503, porque la inferencia tarda de 46
  a 54 s. Dos analistas a la vez no caben en esta máquina.

**El coste de las trazas:** el p50 de lectura sube unos 6 ms (de ~46 a ~52 ms). En
el p95 los rangos se solapan y no se puede afirmar una diferencia.

## 10. Ampliación (2026-11-13) — D8 · «Ocupado» no es «degradado»

Aprobada por el autor el 13/11. Nace del hallazgo de H2 (§9).

**El problema.** `backend-ml` atiende una inferencia por vez. A quien espera turno
más de `ML_ESPERA_MAX_S` le responde 503 con `Retry-After`. `backend-clinic`
trataba ese 503 igual que una caída, con dos consecuencias:

- **El analista veía «Pipeline de IA no disponible»** y un enlace al modo manual,
  con el motor sano y trabajando.
- **Cada «ocupado» contaba para el circuit breaker.** Con el umbral del stack,
  unos pocos analistas sin turno abrían el circuito y dejaban a todos en modo
  manual durante el enfriamiento. No se había visto: lo destapó leer el código
  para esta ampliación.

**La decisión.**

- **La señal es el par 503 + `Retry-After`.** Los demás 503 de `backend-ml` (modelo
  sin cargar, clasificador sin resultado) no llevan esa cabecera. No se cambia
  `backend-ml` ni su contrato.
- **`PipelineClient` lanza `MLBusyError`,** que hereda de `MLDegradedError` y lleva
  los segundos. No cuenta como fallo del circuito y borra los fallos anteriores:
  el motor contestó. Vale para `segment`, `xai` y `classify`.
- **`POST …/process/` responde `503 ML_BUSY`,** con `retry_after_seconds` y la
  cabecera `Retry-After`. La muestra no cambia. `ML_DEGRADED` queda para la caída.
- **El visor muestra un aviso, no una alerta:** «El motor de IA está procesando
  otro caso», con la cuenta atrás y un botón para reintentar. No ofrece el modo
  manual.
- **El endpoint entra en el contrato.** `process` estaba entre los «sin describir»
  (deuda de DD-API-001 D2); ahora tiene sus respuestas, con los dos códigos del 503.

**Criterios de aceptación.**

1. Un 503 con `Retry-After` de `backend-ml` llega al analista como `503 ML_BUSY`
   con los mismos segundos, en el cuerpo y en la cabecera.
2. Cinco «ocupado» seguidos no abren el circuito, con el umbral en 2.
3. Un 503 sin `Retry-After`, un timeout o un fallo de conexión siguen siendo
   `ML_DEGRADED` y siguen abriendo el circuito.
4. Tras un `ML_BUSY` la muestra conserva su estado y no tiene cariotipo nuevo.
5. El visor muestra el aviso con los segundos del backend, sin el banner de modo
   degradado ni el enlace al modo manual; «Reintentar» procesa si ya hay turno.
6. `backend-clinic/openapi.json` describe `process` con `ML_BUSY` y `ML_DEGRADED`.

**Fuera de alcance.**

- **No acorta la inferencia.** El segundo analista sigue sin poder procesar hasta
  que termine el primero; ahora lo sabe. Procesar en segundo plano con una cola es
  lo que prevé ADR-0031, y es otro trabajo.
- **Los demás endpoints que llaman a `backend-ml`** (separar, recortar, mapa de
  calor) siguen respondiendo `ML_DEGRADED` cuando no hay turno. Dejan de sumar al
  circuito, que era lo dañino; su mensaje se cambia aparte.
- **El visor no reintenta solo.** Lo decide el analista.

**Resultados (13 y 14/11).** Los seis criterios se cumplen. 1 a 4 y 6, con
pruebas (`test_motor_ocupado.py`, 23) y sobre el stack; 5, con pruebas del visor
y en Chromium con dos pestañas. El detalle está en `docs/demos/demo-4.md`,
funcionalidad 4.
