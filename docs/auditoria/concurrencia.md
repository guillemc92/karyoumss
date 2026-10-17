# Auditoría de concurrencia del backend — 

> **Módulo 8 · Actividad de auditoría (parte 2 de 2\) · Entrega: domingo 18 de octubre de 2026, 23:59.** Este archivo es a la vez **las instrucciones para el asistente de IA** y **la ficha que se entrega**. El asistente lo rellena en su lugar; el grupo lo revisa, responde las preguntas y lo sube a su repositorio.

## Cómo se usa (para el grupo)

1. Copien este archivo a su repositorio como `docs/auditoria/concurrencia.md`.  
2. Trabajen sobre el mismo commit que la parte 1 (`release/8.0.0`).  
3. Abran su asistente con acceso al repositorio y escríbanle:  
     
   > Sigue las instrucciones de la sección 0 de `docs/auditoria/concurrencia.md` y rellena ese archivo.  
     
4. Respondan las preguntas que el asistente les haga al final de cada oleada. Aquí habrá más preguntas que en la parte 1, porque varios datos (cuántas réplicas corren, cuánto tarda la IA, cuánto tráfico esperan) no están en el código.  
5. Revisen el resultado, confirmen la autoverificación (sección 6\) y hagan los commits **cada integrante con su propia cuenta**.

**Si su asistente no tiene acceso al repositorio:** pídanle los comandos, córranlos ustedes y péguenle la salida.

**Cómo se califica la parte de preguntas:** cada pregunta debe terminar respondida o cerrada como `NO VERIFICABLE` con su motivo. **Si quedan más de 3 preguntas sin responder en este archivo, baja la nota de la actividad.** Si no tienen el dato exacto (por ejemplo, el tráfico esperado), una estimación razonada cuenta como respuesta.

---

## 0\. Instrucciones para el asistente de IA (no editar esta sección)

**Rol.** Eres el asistente de auditoría de un grupo de maestría que desarrolla un backend. Vas a revisar cómo maneja la concurrencia su servicio y a **rellenar este mismo archivo**. No produces otros archivos.

**Conceptos que debes aplicar.**

- **Dónde espera una petición:** casi todo el tiempo de una API es espera (base de datos, red, servicio de IA). Saturar es que un recurso finito (hilos, conexiones del pool, el único hilo del event loop, el cupo de la API de IA) esté al 100 % y las peticiones nuevas hagan cola: primero sube la latencia y luego llegan los errores.  
- **Modelos por runtime:** Node.js usa un event loop de un hilo (cualquier trabajo síncrono lo bloquea); Java 21+ con hilos virtuales permite código bloqueante que escala, pero el pool de la base de datos sigue siendo el límite; Python con `async def` bloquea el loop si llama a librerías síncronas, y las rutas `def` corren en un threadpool finito (40 hilos por defecto en AnyIO).  
- **Ley de Little:** conexiones ocupadas en promedio \= peticiones por segundo que usan la base de datos × tiempo medio que cada una retiene la conexión. Cada instancia tiene su propio pool: la base de datos recibe `instancias × tamaño del pool`.  
- **Llamadas lentas (LLM):** necesitan timeout explícito, reintentos con backoff y jitter, límite de llamadas simultáneas y no retener una conexión de base de datos mientras se espera.

**Reglas que no puedes romper.**

1. **Solo lectura del producto.** No modificas código ni configuración; el único archivo que editas es este. No ejecutas pruebas de carga contra servicios compartidos o en producción.  
2. **No inventas.** Cada estado distinto de `N/A` lleva evidencia comprobable: `ruta/archivo:línea` con el fragmento relevante, o el comando exacto y las primeras líneas de su salida. Las cifras que no salen del código (tráfico, latencias, réplicas) se preguntan, no se suponen.  
3. **No copias secretos.** Rutas y líneas sí; valores de claves, nunca.  
4. **Todas las comprobaciones aparecen**, una vez cada una (CON-01 a CON-05). No agregas ni quitas comprobaciones.  
5. **Escribes en español** y en frases claras.

**Estados permitidos.** `OK`, `PARCIAL`, `FALLA`, `N/A` (con razón) y `NO VERIFICABLE` (con razón). Mientras trabajas puedes usar `PENDIENTE`, pero **al terminar no puede quedar ninguno**.

**Cómo preguntar sin bloquear.** Cuando te falte un dato que no está en el código:

- Marca la comprobación como `PENDIENTE`, agrega la pregunta a la sección 4 con un número (P1, P2…) y la comprobación a la que afecta, y **continúa con la siguiente**. Nunca te detengas a esperar.  
- Al **terminar cada oleada**, muestra al grupo todas las preguntas nuevas juntas. Si tu herramienta permite preguntas con opciones, úsalas (por ejemplo, para el número de réplicas: 1, 2, 3 o más, no sabemos).  
- Si el grupo responde, anota la respuesta y actualiza la comprobación. Si no responde, en la oleada 3 cierra la comprobación como `NO VERIFICABLE` y la pregunta como "sin respuesta".  
- **Antes de preguntar, búscalo** en el README, `docker-compose`, Dockerfile, manifiestos de Kubernetes, archivos de configuración y scripts de arranque.

**Oleadas.** Trabaja en este orden y actualiza la sección 2 al terminar cada una:

- **Oleada 0 · Reconocimiento.** Rellena la sección 1: runtime y framework de cada servicio, punto de arranque, librería de acceso a datos y cliente HTTP o SDK de IA. Escribe en la sección 2 el plan (qué archivos y comandos usarás).  
- **Oleada 1 · Evidencia automática.** Ejecuta los comandos de cada comprobación (adaptados a las carpetas reales) y anota la evidencia.  
- **Oleada 2 · Juicio.** Decide el estado de CON-01 a CON-04 y pregunta lo que falte. Calcula con la ley de Little las conexiones necesarias cuando tengas los datos (tráfico estimado y tiempo de retención); si no los tienes, pregúntalos.  
- **Oleada 3 · Cierre.** Integra las respuestas; escribe la **hipótesis de cuello de botella** (CON-05) con base en las comprobaciones anteriores; cierra lo pendiente como `NO VERIFICABLE`; escribe los hallazgos (sección 5), marca la autoverificación (sección 6\) y rellena el resumen (sección 7). Termina diciendo cuántas preguntas quedaron sin respuesta.

**Si el proyecto tiene varios servicios**, evalúa cada uno y anota la evidencia por servicio; el estado es el del peor evaluado.

---

## 1\. Datos del repositorio (oleada 0\)

- **Grupo:** BIOMED UMSS — Intelligent Karyotyping Platform (grupo de 1 integrante)
- **Commit auditado (`release/8.0.0`):** `d4175a996c2d2343d3b2affaa4c17d8e710d35d9`
- **Fecha de la auditoría:** 16 de octubre de 2026
- **Servicios y runtime:**
  - `backend-clinic` · Python 3.12 + Django 5.0 + DRF, WSGI (`clinic_backend/settings.py:79`), servidor de desarrollo `runserver`.
  - `backend-admin` · Python 3.12 + Django 5.0 + DRF, WSGI (`admin_backend/settings.py:88`), `runserver` (`README.md:67`); `gunicorn` está declarado pero nada lo invoca.
  - `backend-ml` · Python 3.12 + FastAPI + uvicorn, un proceso (`README.md:15`, `uvicorn app.main:app --reload --port 8000`), OpenCV y PyTorch en CPU.
- **Acceso a datos:** ORM de Django · **base de datos:**
  - clínico: SQLite (`clinic_backend/settings.py:85-88`);
  - admin: PostgreSQL por variables, o SQLite de demo (`admin_backend/settings.py:94-116`);
  - backend-ml: sin base de datos.
- **Cliente HTTP o SDK de IA:**
  - `httpx` síncrono, hacia backend-ml (`apps/samples/pipeline_client.py`), backend-admin (`admin_client.py`) y los embeddings de Ollama (`rag_index.py`);
  - SDK `openai` 3.2.0 apuntando a Ollama local, para la narrativa, el enrutador y el RAG (`llm_client.py`, `tool_router.py`, `rag_qa.py`, `agente.py`);
  - `langchain-openai`, para el agente con LangGraph (`agente_grafo.py`).
- **Integrantes y qué revisó cada uno:** Guillermo Mamani Chambi → CON-01 a CON-05 (grupo de una persona).

## 2\. Plan y avance por oleadas

| Oleada | Qué se hizo | Estado |
| :---- | :---- | :---- |
| 0 · Reconocimiento | Runtimes, puntos de arranque, acceso a datos y clientes de IA identificados (sección 1). Plan: `git grep` sobre `release/8.0.0` en las carpetas de código, excluyendo tests, con los comandos sugeridos adaptados a Python/Django/FastAPI (`async def`, `WSGI_APPLICATION`, `transaction.atomic`, `CONN_MAX_AGE`, `timeout`, `retry`, `Semaphore`). | Hecha |
| 1 · Evidencia | Comandos ejecutados para CON-01 a CON-04. Además se midió **una sola ejecución local** del pipeline de backend-ml sobre 5 metafases reales (no es prueba de carga) para responder P3, y se leyó el código instalado del SDK de OpenAI para confirmar sus reintentos por defecto. | Hecha |
| 2 · Juicio | Estados de CON-01 a CON-04 decididos. Preguntas P2–P4 hechas al grupo; P1 se tomó de la respuesta del grupo en la parte 1 (12-factor). | Hecha |
| 3 · Cierre | Respuestas integradas; P3 cerrada con la medición. Hipótesis CON-05 formulada, hallazgos priorizados, autoverificación y resumen completos. Preguntas sin respuesta: 0. | Hecha |

## 3\. Comprobaciones

### CON-01 · Modelo de concurrencia e instancias

- **Qué se busca:** saber cómo atiende peticiones simultáneas cada servicio (event loop, hilos, hilos virtuales, procesos o *workers*) y **cuántas instancias** corren en el entorno donde se despliega.  
- **Señales de falla:** nadie sabe cuántas instancias corren; varias instancias pero un trabajo programado o un estado en memoria que supone una sola.  
- **Comandos sugeridos:**  
    
  git grep \-nE "NestFactory|app\\.listen|cluster|worker\_threads|spring\\.threads\\.virtual|uvicorn|gunicorn|granian|--workers|replicas:|deploy:" \-- .  
    
- **Evidencia:**
  - `git grep -nE "uvicorn|gunicorn|granian|--workers|WSGI_APPLICATION|ASGI_APPLICATION|runserver|replicas:" release/8.0.0 -- backend-admin backend-clinic backend-ml ':!*/tests/*'` →
    - `backend-admin/README.md:67` `python manage.py runserver 0.0.0.0:8001`
    - `backend-admin/admin_backend/settings.py:88` `WSGI_APPLICATION = 'admin_backend.wsgi.application'`
    - `backend-clinic/clinic_backend/settings.py:79` `WSGI_APPLICATION = 'clinic_backend.wsgi.application'`
    - `backend-ml/README.md:15` y `backend-ml/app/main.py:8` `uvicorn app.main:app --reload --port 8000`
  - Ninguna coincidencia de `--workers`, `gunicorn` en uso, `replicas:` ni `deploy:`.
  - Estado en memoria que supone una instancia: circuit breakers por proceso (`pipeline_client.py:21`, `admin_client.py:26`, `llm_client.py:67`) e índice RAG global (`rag_index.py:177`).
  - Instancias: **1 por servicio, solo en la máquina de desarrollo** (respuesta P1).
- **Estado:** OK
- **Observación:**
  - `backend-clinic` y `backend-admin` son Django síncrono (WSGI) sobre `runserver`, que atiende cada petición en un hilo nuevo, sin límite.
  - `backend-ml` es FastAPI sobre uvicorn: **un proceso con un único event loop**. Lo síncrono no se manda a otro hilo (ver CON-02).
  - Hay 1 instancia de cada uno (P1), así que el estado en memoria por proceso (breakers, índice RAG) es coherente. Se sabe qué corre y cuántas instancias hay.
  - **Advertencia para S07:** el número de hilos o workers hoy no está fijado en ningún lado. Al pasar a gunicorn o a varias réplicas habrá que fijarlo, y los breakers quedarán separados por instancia.
- **Auditó:** Guillermo Mamani Chambi

### CON-02 · Llamadas bloqueantes en el camino de una petición

- **Qué se busca:** que ningún manejador de petición haga trabajo síncrono que congele el servicio: lectura de archivos síncrona, bucles pesados, `JSON.parse` de archivos grandes, librerías síncronas dentro de código asíncrono.  
- **Señales de falla:** en Node, `readFileSync`, `execSync`, cálculos pesados en el handler; en Python, `requests.` o `time.sleep` dentro de `async def`, o un SDK síncrono de IA llamado desde código asíncrono; en Java, bloqueo en WebFlux o `synchronized` alrededor de E/S con JDK anterior a 24\.  
- **Comandos sugeridos:**  
    
  git grep \-nE "readFileSync|writeFileSync|execSync|spawnSync|JSON\\.parse\\(fs" \-- \<carpetas de código\>  
    
  git grep \-nE "async def" \-- '\*.py'    \# luego revisar si dentro se usa requests., time.sleep o un SDK síncrono  
    
  git grep \-nE "Mono|Flux|WebClient|synchronized" \-- '\*.java'  
    
- **Evidencia:**
  - `git grep -nE "^(async )?def |@app\.(get|post)" release/8.0.0 -- backend-ml/app/main.py`:
    - `main.py:37` `async def segment_endpoint`
    - `main.py:52` `async def xai_endpoint`
    - `main.py:105` `async def classify_endpoint`
    - (`main.py:26` `def health` es síncrona)
  - **Trabajo de CPU síncrono dentro de `async def`:**
    - `main.py:48` `return run_pipeline(gray)`: segmentación OpenCV y clasificación EfficientNet-B3 con PyTorch;
    - `main.py:89` `segment(gray)` y `:94-95` `heatmap_png(...)` y `resumen_activacion(...)`: Grad-CAM.
    - Ninguno pasa por `run_in_threadpool` ni `asyncio.to_thread`.
  - **Medición** (una ejecución local de `run_pipeline` sobre 5 metafases de `datasets/metaclass/metafases/`, CPU de 4 núcleos):
    - `metafase_1.bmp: 17.66 s` · `metafase_10.bmp: 21.67 s` · `metafase_100.bmp: 17.55 s` · `metafase_101.bmp: 19.07 s` · `metafase_102.bmp: 20.20 s`
    - **mediana 19.07 s, máximo 21.67 s**; la carga inicial del clasificador, `16.30 s`.
  - **backend-clinic**: `git grep -nE "async def" release/8.0.0 -- backend-clinic/apps ':!*/tests/*'` → solo `mcp_conexion.py:117,130`, que corren en su propio hilo y bucle (`:91-92`). Las vistas son síncronas y llaman a la IA de forma síncrona (`services.py:75`, `:246`, `:379`, `:997`; `llm_client` en `:820`), lo que en WSGI ocupa un hilo, no bloquea a los demás.
- **Estado:** FALLA
- **Observación:**
  - `backend-ml` congela su único event loop durante unos 19 s por metafase. Mientras dura, no atiende **ninguna** otra petición, ni siquiera `/health/`, y dos segmentaciones simultáneas se ejecutan una detrás de otra.
  - En `backend-clinic` el patrón síncrono es correcto para WSGI: cada espera ocupa un hilo de `runserver`. Pero una petición puede retener ese hilo hasta varios minutos (ver CON-04).
  - Corrección mínima: declarar los tres endpoints con `def`, o envolver el trabajo en `run_in_threadpool`, y limitar con un semáforo cuántas inferencias corren a la vez.
- **Auditó:** Guillermo Mamani Chambi

### CON-03 · Pool de conexiones a la base de datos

- **Qué se busca:** que el tamaño del pool, el tiempo de espera para obtener una conexión y el error que devuelve la API cuando el pool se agota estén **definidos a propósito**, y que `instancias × tamaño del pool` no supere lo que admite la base de datos. Lo ideal al agotarse es un error rápido y claro (por ejemplo, 503), no una espera larga ni un 500 genérico.  
- **Señales de falla:** valores por defecto sin revisar; pool enorme "por si acaso"; transacciones abiertas mientras se espera al servicio de IA.  
- **Comandos sugeridos:**  
    
  git grep \-nE "poolSize|max:|connectionLimit|connection\_limit|maximum-pool-size|maximumPoolSize|pool\_size|max\_overflow|pool\_timeout|connectionTimeout|acquireTimeout" \-- .  
    
- **Cálculo (ley de Little):**
  - Conexiones ocupadas en promedio = λ × W.
  - λ < 1 petición/s (P2).
  - W es casi siempre milisegundos (lecturas del visor). El caso largo es el registro, que abre la conexión al escribir la muestra y la mantiene hasta el final de la petición mientras segmenta: **W ≈ 19 s** (medido en CON-02).
  - Cota superior, si todas las peticiones fueran registros: **L < 1 × 19 ≈ 19** conexiones. En el uso real, con pocos registros por hora, L queda **por debajo de 1**.
  - Total en la base de datos = 1 instancia (P1) × sin pool (una conexión por hilo, `CONN_MAX_AGE` por defecto) = **L**.
- **Evidencia:**
  - `git grep -nE "CONN_MAX_AGE|CONN_HEALTH|ATOMIC_REQUESTS|pool|busy_timeout|max_connections|'timeout'" release/8.0.0 -- backend-admin/admin_backend backend-clinic/clinic_backend` → sin resultados en `settings.py`. Solo `admin_backend/settings_test.py:51` `'timeout': 30`, para pruebas.
  - `backend-clinic/clinic_backend/settings.py:85-88`: SQLite sin `OPTIONS`, así que se usa el `timeout` por defecto del controlador (5 s) y no hay pool. Django 5.0 no trae pool propio.
  - `backend-admin/admin_backend/settings.py:103-116`: PostgreSQL sin `CONN_MAX_AGE` ni pool (solo `OPTIONS: search_path`).
  - **Transacciones y llamadas a la IA** (comprobado): `services.py:59-62` cierra la transacción **antes** de `pipeline_client.segment_image` (`:75`); `view_xai` llama a la IA (`:405`) antes de `transaction.atomic()` (`:407`); `sign_report` verifica el MFA (`:750`) antes de la transacción (`:761`); `generate_narrative` llama al LLM (`:820`) antes de la transacción (`:831`); `recrop_chromosome` clasifica (`:997`) antes de la transacción (`:1004`). **Ninguna transacción queda abierta esperando a la IA.**
- **Estado:** FALLA
- **Observación:**
  - Lo importante está bien: no se abre ninguna transacción mientras se espera a la IA o al MFA.
  - Pero nada del acceso a la base de datos está definido a propósito: ni pool, ni tiempo de espera, ni error. En el clínico (SQLite) el límite real es **un solo escritor**. Si una escritura espera más de 5 s, Django lanza `database is locked`, que llega al cliente como **500 genérico**, no como 503.
  - Con el tráfico declarado (P2) el riesgo es bajo hoy. Al pasar a PostgreSQL y a varias instancias, hay que fijar el pool y su error.
- **Auditó:** Guillermo Mamani Chambi

### CON-04 · Timeouts y reintentos en llamadas externas (incluida la IA)

- **Qué se busca:** que toda llamada a otro servicio (HTTP, IA, colas) tenga **timeout explícito**; que los reintentos usen backoff con jitter y solo en operaciones idempotentes; y que las llamadas al LLM tengan un límite de llamadas simultáneas y no retengan conexiones de base de datos.  
- **Señales de falla:** clientes HTTP sin timeout; reintentos inmediatos en bucle; la petición del usuario espera sin límite la respuesta del LLM.  
- **Comandos sugeridos:**  
    
  git grep \-nE "axios|fetch\\(|HttpService|httpx|requests\\.|RestClient|WebClient|OpenAI|Anthropic|ChatClient" \-- \<carpetas de código\>  
    
  git grep \-nE "timeout|retry|retries|backoff|AbortSignal|maxRetries|Semaphore|p-limit|bulkhead" \-- \<carpetas de código\>  
    
- **Evidencia:**
  - **Timeouts explícitos y configurables:**
    - backend-ml: `CLINIC_FASTAPI_TIMEOUT = 2.0` (`settings.py:148`), elevado por endpoint a `max(timeout, 30.0)` para segmentar (`pipeline_client.py:65`) y `max(timeout, 60.0)` para XAI y clasificar (`:90`, `:114`);
    - MFA en admin: `admin_client.py:44` y `:61`;
    - LLM: `CLINIC_LLM_TIMEOUT = 240.0` (`settings.py:172`), usado en `llm_client.py:158` y `:220`, `agente.py:110`, `agente_grafo.py:142`, `rag_qa.py:233` y `tool_router.py:243`;
    - embeddings: `TIMEOUT_S = 600.0` (`rag_index.py:59`, `:78`);
    - MCP: `TIMEOUT_S = 300.0` (`mcp_conexion.py:41`, `:113`).
  - **Circuit breakers:** `pipeline_client.py:21-36` (3 fallos, 60 s de pausa; `settings.py:149-150`), `admin_client.py:26-42` y `llm_client.py:67-75`, `:139-140` (3 fallos, 120 s; `settings.py:173-174`). Al abrirse responden 503 `ML_DEGRADED` (`views.py:233`).
  - **Reintentos explícitos:** `git grep -nE "retry|retries|backoff|jitter|max_retries"` → ninguno en el código de BIOMED.
  - **Reintentos implícitos del SDK de OpenAI:** `DEFAULT_MAX_RETRIES = 2` (`python -c "from openai import _constants as c; print(c.DEFAULT_MAX_RETRIES)"` → `2`, openai 3.2.0). El SDK reintenta también tras un timeout (`openai/_base_client.py:1095-1105`, `if remaining_retries > 0`). BIOMED no fija `max_retries`.
  - **Límite de llamadas simultáneas al LLM:** `git grep -nE "Semaphore|BoundedSemaphore|bulkhead"` → ninguno.
  - **Latencia observada:** LLM entre 30 y 120 s (P4); segmentación 19 s de mediana y 21,7 s de máximo (CON-02).
- **Estado:** PARCIAL
- **Observación:** Bien resuelto: toda llamada externa tiene timeout explícito y configurable, y las tres dependencias tienen circuit breaker que degrada a 503 (RN-07). Falta:
  1. **Reintentos ocultos:** los del SDK de OpenAI, sumados al timeout de 240 s, permiten que una petición espere hasta unos 12 minutos (3 × 240 s).
  2. **Sin límite de concurrencia:** no hay semáforo para el LLM ni para la inferencia.
  3. **Margen estrecho:** el timeout de segmentación (30 s) apenas supera la latencia medida (21,7 s). Con dos segmentaciones simultáneas, la segunda espera unos 38 s (CON-02) y el cliente corta.
  4. **LLM síncrono:** la petición del usuario espera la respuesta entera, sin cola + 202 ni streaming.
- **Auditó:** Guillermo Mamani Chambi

### CON-05 · Hipótesis de cuello de botella

- **Qué se busca:** una frase que diga **qué recurso se saturará primero** cuando crezca el tráfico y por qué, basada en CON-01 a CON-04. Se comprobará con la primera prueba de carga con k6 (S04).  
- **Formato:** "Bajo carga, se saturará primero en , porque ."  
- **Hipótesis:** "Bajo carga, se saturará primero **el único event loop de backend-ml** (uvicorn, un proceso, CON-01), porque cada segmentación ocupa unos 19 s de CPU dentro de un `async def` sin pasar a un hilo (CON-02). Con dos registros simultáneos, el segundo espera unos 38 s, supera el timeout de 30 s del cliente (CON-04) y, tras 3 fallos, el circuit breaker deja a **todos** los usuarios en modo degradado durante 60 s. Esto ocurre mucho antes de que la base de datos se acerque a su límite: a menos de 1 petición/s, L < 1 conexión (CON-03)."
- **Estado:** OK
- **Auditó:** Guillermo Mamani Chambi

## 4\. Preguntas al grupo

| N.º | Comprobación | Pregunta | Respuesta del grupo | Estado (respondida / sin respuesta) |
| :---- | :---- | :---- | :---- | :---- |
| P1 | CON-01, CON-03 | ¿Dónde se despliega y con cuántas instancias de cada servicio? | Solo en la máquina de desarrollo, una instancia por servicio (respuesta dada en la parte 1, `docs/auditoria/12factor.md`, P1). | respondida |
| P2 | CON-03, CON-05 | ¿Cuántas peticiones por segundo recibiría backend-clinic en el momento de más uso? | Menos de 1 petición/s (laboratorio pequeño, 1–3 analistas a la vez). | respondida |
| P3 | CON-04, CON-05 | ¿Cuánto tarda backend-ml en segmentar y clasificar una metafase? | El grupo no lo sabía. Se cerró con una medición local (no de carga): mediana 19,07 s, máximo 21,67 s sobre 5 metafases reales; carga inicial del modelo 16,30 s. | respondida (por medición) |
| P4 | CON-04, CON-05 | ¿Cuánto tarda el LLM local en generar la narrativa o responder al chat? | Entre 30 y 120 s. | respondida |

## 5\. Hallazgos priorizados

| \# | Comprobación | Severidad (alta / media / baja) | Qué falla | Corrección propuesta | Responsable |
| :---- | :---- | :---- | :---- | :---- | :---- |
| 1 | CON-02 | alta | Inferencia de ~19 s de CPU dentro de `async def` en backend-ml: congela el único event loop | Endpoints `def` o `run_in_threadpool`; semáforo que limite las inferencias simultáneas; varios workers de uvicorn medidos con k6 | Guillermo Mamani Chambi |
| 2 | CON-04 | alta | Reintentos implícitos del SDK de OpenAI (hasta ~12 min por petición) y sin límite de llamadas simultáneas al LLM | Fijar `max_retries` a propósito (0 o 1); semáforo para el LLM; narrativa por cola + 202 + consulta de estado, o streaming | Guillermo Mamani Chambi |
| 3 | CON-04 | media | Timeout de segmentación (30 s) casi igual a la latencia medida (21,7 s) | Pasar la segmentación a una operación asíncrona (202 + estado) en vez de esperar en la petición de registro; ajustar el timeout con la p95 medida en k6 | Guillermo Mamani Chambi |
| 4 | CON-03 | media | Acceso a BD con valores por defecto; SQLite con un solo escritor y `database is locked` como 500 | PostgreSQL en el clínico con `CONN_MAX_AGE`/pool fijados a propósito; error de agotamiento mapeado a 503 | Guillermo Mamani Chambi |
| 5 | CON-01 | baja | Hilos de `runserver` sin límite; ningún número de workers fijado | Servidor de producción (gunicorn/uvicorn) con workers e hilos fijados y justificados con la ley de Little | Guillermo Mamani Chambi |

## 6\. Autoverificación (la marca el asistente; el grupo la confirma)

- [x] Las cinco comprobaciones CON-01 a CON-05 están en la sección 3, una vez cada una.  
- [x] Ninguna quedó en `PENDIENTE` ni sin estado; todos los estados son de los cinco permitidos.  
- [x] Todo estado distinto de `N/A` y `NO VERIFICABLE` tiene evidencia con ruta y línea, o con comando y salida.  
- [x] Las cifras usadas (tráfico, latencias, réplicas) vienen del código o de una respuesta del grupo, no de una suposición. (La latencia de segmentación viene de una medición, documentada en P3.)  
- [x] CON-05 está formulada con el formato pedido y cita las comprobaciones en que se basa.  
- [x] Todas las preguntas de la sección 4 están respondidas o marcadas "sin respuesta".  
- [x] No hay ningún secreto copiado en este archivo.  
- [ ] No se modificó código del producto. (Se confirma al hacer el commit.)  
- [ ] Cada integrante aparece como auditor de al menos una comprobación y tiene al menos un commit con su propia identidad. (Se confirma al hacer el commit.)

## 7\. Resumen

| OK | PARCIAL | FALLA | N/A | NO VERIFICABLE | Preguntas sin respuesta |
| ----: | ----: | ----: | ----: | ----: | ----: |
| 2 | 1 | 2 | 0 | 0 | 0 |

**Hipótesis de cuello de botella (copia de CON-05):** Bajo carga, se saturará primero el único event loop de backend-ml (uvicorn, un proceso, CON-01), porque cada segmentación ocupa unos 19 s de CPU dentro de un `async def` sin pasar a un hilo (CON-02). Con dos registros simultáneos, el segundo espera unos 38 s, supera el timeout de 30 s del cliente (CON-04) y, tras 3 fallos, el circuit breaker deja a todos los usuarios en modo degradado durante 60 s. Esto ocurre mucho antes de que la base de datos se acerque a su límite: a menos de 1 petición/s, L < 1 conexión (CON-03).
