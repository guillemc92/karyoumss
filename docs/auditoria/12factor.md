# Auditoría 12-factor — 

> **Módulo 8 · Actividad de auditoría (parte 1 de 2\) · Entrega: domingo 18 de octubre de 2026, 23:59.** Este archivo es a la vez **las instrucciones para el asistente de IA** y **la ficha que se entrega**. El asistente lo rellena en su lugar; el grupo lo revisa, responde las preguntas y lo sube a su repositorio.

## Cómo se usa (para el grupo)

1. Copien este archivo a su repositorio como `docs/auditoria/12factor.md`.  
2. Creen la etiqueta o rama `release/8.0.0` sobre su rama principal actual (es el estado de partida del módulo) y trabajen sobre ese commit.  
3. Abran su asistente con acceso al repositorio (Claude Code, Codex, Cursor u otro) y escríbanle:  
     
   > Sigue las instrucciones de la sección 0 de `docs/auditoria/12factor.md` y rellena ese archivo.  
     
4. Respondan las preguntas que el asistente les haga al final de cada oleada. Pueden contestar en el chat o escribiendo la respuesta directamente en la sección 4\.  
5. Revisen el resultado, corran ustedes la autoverificación (sección 6\) y hagan los commits **cada integrante con su propia cuenta**.

**Si su asistente no tiene acceso al repositorio** (un chat sin herramientas): pídanle que les indique qué comandos correr, córranlos ustedes y péguenle la salida. El resto del proceso es igual.

**Cómo se califica la parte de preguntas:** cada pregunta debe terminar respondida o cerrada como `NO VERIFICABLE` con su motivo. **Si quedan más de 3 preguntas sin responder en este archivo, baja la nota de la actividad.** No saber un dato no es un error; dejar sin respuesta lo que el grupo sí podría averiguar, sí.

---

## 0\. Instrucciones para el asistente de IA (no editar esta sección)

**Rol.** Eres el asistente de auditoría de un grupo de maestría que desarrolla un backend. Vas a revisar su repositorio contra seis prácticas 12-factor y a **rellenar este mismo archivo**. No produces otros archivos.

**Reglas que no puedes romper.**

1. **Solo lectura del producto.** No modificas código, configuración ni dependencias del repositorio. El único archivo que editas es este.  
2. **No inventas.** Cada estado distinto de `N/A` lleva evidencia comprobable: `ruta/archivo:línea` con el fragmento relevante, o el comando exacto que ejecutaste y las primeras líneas de su salida. Si no puedes comprobar algo, no lo supones: lo preguntas o lo marcas `NO VERIFICABLE` con su motivo.  
3. **No copias secretos.** Si encuentras una contraseña, token o clave, reportas la ruta y la línea, **nunca el valor**. No abras ni muestres archivos `.env` ni de claves en el chat.  
4. **Todas las comprobaciones aparecen**, una vez cada una (F12-01 a F12-06), aunque el resultado sea negativo. No agregas ni quitas comprobaciones.  
5. **Escribes en español** y en frases claras.

**Estados permitidos.** `OK`, `PARCIAL`, `FALLA`, `N/A` (no aplica, con razón) y `NO VERIFICABLE` (no se pudo comprobar, con razón). Mientras trabajas puedes usar `PENDIENTE`, pero **al terminar no puede quedar ninguno**.

**Cómo preguntar sin bloquear.** Cuando te falte un dato que no está en el código (por ejemplo, cómo se despliega en producción):

- Marca la comprobación como `PENDIENTE`, agrega la pregunta a la sección 4 con un número (P1, P2…) y la comprobación a la que afecta, y **continúa con la siguiente**. Nunca te detengas a esperar.  
- Al **terminar cada oleada**, muestra al grupo todas las preguntas nuevas juntas, cada una con su número. Si tu herramienta permite preguntas con opciones, úsalas; si no, escríbelas en el chat.  
- Si el grupo responde, anota la respuesta en la sección 4 y actualiza la comprobación. Si no responde o no lo sabe, en la oleada 3 cierra la comprobación como `NO VERIFICABLE` y la pregunta como "sin respuesta".  
- Pregunta solo lo necesario: **antes de preguntar, búscalo en el repositorio** (README, `docker-compose`, Dockerfile, manifiestos, configuración, scripts).

**Oleadas.** Trabaja en este orden y actualiza la sección 2 al terminar cada una:

- **Oleada 0 · Reconocimiento.** Rellena la sección 1 (commit, stack, carpetas de código, cómo se ejecuta) y escribe en la sección 2 un plan breve: qué carpetas revisarás y qué comandos usarás para cada comprobación. No preguntes nada todavía, salvo que no encuentres el código fuente.  
- **Oleada 1 · Evidencia automática.** Ejecuta los comandos de cada comprobación (adáptalos a las carpetas reales del proyecto) y anota la evidencia. No decidas estados aún.  
- **Oleada 2 · Juicio.** Con la evidencia, decide el estado de cada comprobación y escribe la observación. Lo que no se pueda decidir sin un dato externo, pregúntalo como se indica arriba. Al terminar, muestra las preguntas.  
- **Oleada 3 · Cierre.** Integra las respuestas recibidas; cierra lo que quede sin respuesta como `NO VERIFICABLE`; escribe los hallazgos priorizados (sección 5); marca la autoverificación (sección 6\) y rellena el resumen (sección 7). Termina diciendo al grupo cuántas preguntas quedaron sin respuesta.

**Si el proyecto tiene varios servicios** (por ejemplo, un backend en NestJS y otro en Python), evalúa cada comprobación sobre todos y anota la evidencia de cada uno; el estado es el del servicio peor evaluado.

---

## 1\. Datos del repositorio (oleada 0\)

- **Grupo:** BIOMED UMSS — Intelligent Karyotyping Platform (grupo de 1 integrante)
- **Repositorio:** https://github.com/guillemc92/karyoumss
- **Commit auditado (`release/8.0.0`):** `d4175a996c2d2343d3b2affaa4c17d8e710d35d9` (rama local `release/8.0.0`, creada sobre `feature/clinic-django-stack`)
- **Fecha de la auditoría:** 16 de octubre de 2026
- **Stack detectado:** tres servicios backend en Python.
  - `backend-admin` — Django 5.0 + DRF, PostgreSQL (psycopg 3) o SQLite de demo, JWT (simplejwt), gunicorn declarado en `requirements.txt`.
  - `backend-clinic` — Django 5.0 + DRF, SQLite, cliente HTTP `httpx`, SDK `openai` contra **Ollama local** (LLM y embeddings), LangGraph con checkpointer SQLite, servidor MCP.
  - `backend-ml` — FastAPI + uvicorn, OpenCV y PyTorch (EfficientNet-B3).
  - Fuera del alcance (consumidores de la API): `frontend-admin` y `frontend-clinic` (React + Vite).
- **Carpetas de código fuente:** `backend-admin/admin_backend/`, `backend-admin/apps/`, `backend-clinic/clinic_backend/`, `backend-clinic/apps/`, `backend-ml/app/`. Se excluyen de la búsqueda `*/tests/*`, `backend-ml/training/` (cuadernos de entrenamiento) y los comandos de gestión de demostración.
- **Cómo se ejecuta (verificado):**
  - `cd backend-clinic && .venv/Scripts/python.exe manage.py check` → `System check identified no issues (0 silenced).`
  - `cd backend-admin && .venv/Scripts/python.exe manage.py check` → `System check identified no issues (0 silenced).`
  - `cd backend-ml && py -3.12 -c "import app.main"` → importa sin error.
  - Arranque documentado: `python manage.py runserver 0.0.0.0:8001` (`backend-admin/README.md:67`) y `uvicorn app.main:app --reload --port 8000` (`backend-ml/README.md:15`). Son servidores de desarrollo.
- **Integrantes y qué revisó cada uno:** Guillermo Mamani Chambi → F12-01 a F12-06 (grupo de una persona).

## 2\. Plan y avance por oleadas

| Oleada | Qué se hizo | Estado |
| :---- | :---- | :---- |
| 0 · Reconocimiento | Rama `release/8.0.0` creada en `d4175a9`. Identificados 3 servicios backend y sus carpetas. Configuración verificada con `manage.py check` (clinic y admin) e importación de `backend-ml`. Plan: `git grep` sobre `release/8.0.0` en las carpetas de código, excluyendo tests, con los comandos sugeridos adaptados a Python (`os.environ`, `env(`, `FileHandler`, `httpx`, `OpenAI(`, `SIGTERM`, `lifespan`). Para secretos, solo comandos que cuentan o enmascaran valores. | Hecha |
| 1 · Evidencia | Comandos ejecutados para las 6 comprobaciones; evidencia anotada en la sección 3. `gitleaks` y `trufflehog` no están instalados: se usó `git grep -c` y `git log --all -G` con los valores enmascarados. | Hecha |
| 2 · Juicio | Estados decididos para las 6 comprobaciones. Una pregunta al grupo (P1) para precisar el contexto de despliegue de F12-03 y F12-06. | Hecha |
| 3 · Cierre | P1 respondida: hoy solo se ejecuta en la máquina de desarrollo, una instancia por servicio. Integrada en F12-03 y F12-06 (no cambia sus estados). Hallazgos priorizados, autoverificación y resumen completos. Preguntas sin respuesta: 0. | Hecha |

## 3\. Comprobaciones

### F12-01 · Configuración fuera del código (factor III)

- **Qué se busca:** todo lo que cambia entre entornos (URLs, puertos, credenciales, banderas) se lee del entorno al arrancar, y la aplicación valida al inicio que esté presente. Mismo código en dev, pruebas y producción; solo cambia la configuración.  
- **Señales de falla:** `localhost`, IPs o puertos escritos en el código; URLs de servicios fijas; condiciones del tipo `if (env === 'production')` repartidas por el código.  
- **Comandos sugeridos:**  
    
  git grep \-nE "localhost|127\\.0\\.0\\.1|:5432|:3306|:6379|:27017|https?://" \-- \<carpetas de código\>  
    
  git grep \-nE "process\\.env|ConfigService|getOrThrow|@Value|@ConfigurationProperties|BaseSettings|os\\.environ|os\\.getenv" \-- \<carpetas de código\>  
    
- **Evidencia:**
  - Comando: `git grep -nE "localhost|127\.0\.0\.1|:5432|:11434|https?://" release/8.0.0 -- backend-admin backend-clinic backend-ml ':!*/tests/*'` (22 líneas; las relevantes abajo).
  - **Lectura del entorno con validación** — `backend-admin/admin_backend/settings.py:18-21` y `backend-clinic/clinic_backend/settings.py:19-22`: función `env(key, default, required)` que lanza `RuntimeError("Missing required env var")` si falta una obligatoria. Son obligatorias, por ejemplo, `DJANGO_SECRET_KEY` (admin `:29`), `AUTH_BRIDGE_SECRET` (`:170`), `AUTH_ADMIN_JWT_SECRET` (`:181`, y clinic `:128`), `TOTP_VAULT_KEY` (`:187`) y `PATIENT_VAULT_KEY` (clinic `:136`).
  - **URLs de servicios desde el entorno, con `localhost` como valor por defecto** — `backend-clinic/clinic_backend/settings.py:143` `CLINIC_FASTAPI_URL = env('CLINIC_FASTAPI_URL', 'http://localhost:8000')`, `:156` `ADMIN_INTERNAL_URL`, `:165` `CLINIC_LLM_URL`; `backend-admin/admin_backend/settings.py:108` `env('POSTGRES_HOST', 'localhost')`.
  - **URL fija que ignora la configuración** — `backend-clinic/apps/samples/rag_index.py:63` `base_url: str = 'http://localhost:11434'` en `embeber()`, y `rag_index.py:138` la llama en cada consulta sin pasar `base_url`. La búsqueda del RAG no usa `CLINIC_LLM_URL`.
  - **Valor por defecto duplicado en 5 módulos** — `getattr(settings, 'CLINIC_LLM_URL', 'http://localhost:11434/v1')` en `agente.py:108`, `agente_grafo.py:138`, `llm_client.py:218`, `rag_qa.py:231` y `tool_router.py:241` (todos en `backend-clinic/apps/samples/`).
  - **Banderas con valor por defecto inseguro** — `backend-clinic/clinic_backend/settings.py:31` `DEBUG = env('DJANGO_DEBUG', 'True')`: sin variable, el servicio arranca en modo depuración. En admin (`settings.py:30`) el valor por defecto es `False`.
  - **backend-ml** — `backend-ml/app/efficientnet.py:21` `MODELS_DIR` fijo relativo al código; el puerto solo en la línea de comandos (`README.md:15`). Lee del entorno solo un interruptor (`efficientnet.py:31`).
- **Estado:** PARCIAL
- **Observación:** La base es correcta: los dos servicios Django leen la configuración del entorno y fallan al arrancar si falta un secreto obligatorio. Fallan tres cosas: (1) la búsqueda del RAG tiene la URL de Ollama escrita en el código y no obedece `CLINIC_LLM_URL`, así que mover Ollama a otro host rompe el RAG en silencio; (2) `backend-clinic` arranca con `DEBUG=True` si falta la variable; (3) las URLs tienen `localhost` como valor por defecto, de modo que un despliegue con una variable olvidada apunta a la propia máquina en lugar de fallar.
- **Auditó:** Guillermo Mamani Chambi

### F12-02 · Secretos fuera del repositorio y de su historial (factor III)

- **Qué se busca:** ninguna contraseña, token o clave en el código, en archivos versionados ni en el historial de git. El `.env` real está en `.gitignore`; solo se versiona un `.env.example` sin valores reales.  
- **Señales de falla:** `.env` versionado; asignaciones del tipo `password = "..."` o `apiKey: '...'`; claves en `docker-compose.yml`, en un `Dockerfile` (`ENV` o `ARG`) o en archivos de configuración.  
- **Comandos sugeridos** (no muestran valores):  
    
  git ls-files | grep \-E '(^|/)\\.env\$' ; git check-ignore \-v .env  
    
  git log \--all \--oneline \-- .env  
    
  git grep \-c \-I \-i \-E '(password|secret|api\[\_-\]?key|token)\[\[:space:\]\]\*\[:=\]' \-- . ':\!\*.lock'  
    
  git log \--all \--pickaxe-regex \-S'(?i)password' \--oneline \--name-only  
    
  gitleaks detect \--source . \--redact \--no-banner   \# opcional, si está instalado  
    
- **Evidencia:**
  - `git ls-tree -r --name-only release/8.0.0 | grep -E '(^|/)\.env$'` → sin resultados: **ningún `.env` versionado**. Solo `.env.example` en los cuatro servicios que lo usan.
  - `git log --all --oneline -- '*.env' '.env'` → sin resultados: **ningún `.env` en el historial**.
  - `git check-ignore -v <servicio>/.env` → ignorado en `backend-admin/.gitignore:19`, `backend-clinic/.gitignore:4` y `frontend-admin/.gitignore:34`; **sin regla** para `backend-ml/.env` y `frontend-clinic/.env`. El `.gitignore` raíz no tiene ninguna línea `.env`. Hoy esos dos archivos no existen.
  - **Secretos con valor por defecto en el código** (valor no copiado): `backend-clinic/clinic_backend/settings.py:30` `SECRET_KEY = env('DJANGO_SECRET_KEY', '***')`, `:157` `INTERNAL_SERVICE_SECRET = env('INTERNAL_SERVICE_SECRET', '***')`; `backend-admin/admin_backend/settings.py:195` `INTERNAL_SERVICE_SECRET = env('INTERNAL_SERVICE_SECRET', '***')`.
  - **Literales en código de producción**: `git grep -c ... -- backend-* ':!*/tests/*'` → 5 coincidencias, todas `api_key='***'` del cliente de Ollama (`agente.py:109`, `agente_grafo.py:139`, `llm_client.py:158`, `rag_qa.py:232`, `tool_router.py:242`). Es el marcador que exige el SDK de OpenAI; Ollama no valida claves, así que no es una credencial.
  - **Historial**: `git log --all -G"(PASSWORD|SECRET|api_key)[A-Z_]* *= *['\"][^'\"]{6,}" --oneline | wc -l` → 11 commits. Revisados con el valor enmascarado: el marcador de Ollama, `settings_test.py` (secretos de prueba) y valores simulados de MSW (`frontend-admin/src/admin/msw/handlers.ts`). Ninguna credencial real.
  - `gitleaks` y `trufflehog` no están instalados (`which` sin resultado).
- **Estado:** PARCIAL
- **Observación:** No hay secretos reales versionados ni en el historial. Dos debilidades: (1) tres secretos tienen un valor por defecto escrito en el código; si el despliegue olvida la variable, el servicio arranca con un secreto que cualquiera con acceso al repositorio conoce. En especial `INTERNAL_SERVICE_SECRET`, que protege la llamada entre servicios de la firma con MFA. (2) El `.gitignore` no cubre `.env` en `backend-ml` ni en `frontend-clinic`.
- **Auditó:** Guillermo Mamani Chambi

### F12-03 · Procesos sin estado (factor VI)

- **Qué se busca:** nada importante vive en la memoria del proceso ni en su disco local entre peticiones: sesiones, archivos subidos y cachés compartidas van a servicios de apoyo (base de datos, Redis, almacenamiento de objetos). Así se pueden levantar varias instancias.  
- **Señales de falla:** archivos subidos guardados en una carpeta local; sesiones en memoria; un `Map` o diccionario global usado como caché compartida; trabajos programados que asumen una sola instancia.  
- **Comandos sugeridos:**  
    
  git grep \-nE "writeFileSync|writeFile\\(|createWriteStream|diskStorage|mkdirSync|open\\(.\*\['\\"\]w|UploadFile" \-- \<carpetas de código\>  
    
  git grep \-nE "express-session|MemoryStore|new Map\\(|@Cron|setInterval\\(" \-- \<carpetas de código\>  
    
- **Evidencia:**
  - Comando: `git grep -nE "write_bytes|write_text|mkdir|MEDIA_ROOT|global |threading\.|sqlite" release/8.0.0 -- backend-admin backend-clinic backend-ml ':!*/tests/*'`.
  - **Imágenes subidas en el disco local** — `backend-clinic/apps/samples/services.py:149-151`: `abs_path = Path(settings.MEDIA_ROOT) / rel_path`, `mkdir(...)`, `abs_path.write_bytes(raw)`. Las metafases de cada caso viven en `backend-clinic/media/` y se vuelven a leer en `services.py:246`.
  - **Base de datos en un archivo local** — `backend-clinic/clinic_backend/settings.py:85-88`: `ENGINE: django.db.backends.sqlite3`, `NAME: BASE_DIR / env('CLINIC_DB_NAME', 'clinic_demo.sqlite3')`.
  - **Memoria del agente en un archivo local** — `backend-clinic/apps/samples/agente_grafo.py:113` `RUTA_MEMORIA = ... / 'agente_memoria.sqlite3'` (checkpointer de LangGraph).
  - **Estado en memoria del proceso** — `rag_index.py:177-179` (`global _indice`, índice RAG cargado una vez, solo lectura); `backend-ml/app/pipeline.py:28` (`global _classifier_singleton`, modelo cargado una vez, solo lectura); `backend-clinic/apps/samples/mcp_conexion.py:83-92` (hilo propio por proceso para el cliente MCP).
  - **backend-admin** — base de datos PostgreSQL por variables (`settings.py:103-108`); no escribe en disco. `django-ratelimit` está en `requirements.txt:29`, pero `git grep -n ratelimit` no lo encuentra en el código: no se usa.
- **Estado:** FALLA
- **Observación:** `backend-admin` cumple. `backend-clinic`, el servicio peor evaluado, no: guarda en su disco local las tres cosas que importan entre peticiones (las imágenes de los casos, la base de datos SQLite y la memoria del agente). Una segunda instancia no vería los casos de la primera, y al reemplazar el contenedor se perderían. Hoy no duele porque solo corre una instancia en la máquina de desarrollo (P1), pero bloquea la contenedorización de S07 y cualquier réplica. Las cachés en memoria (índice RAG, modelo) son de solo lectura y se reconstruyen al arrancar: son optimizaciones aceptables.
- **Auditó:** Guillermo Mamani Chambi

### F12-04 · Logs a la salida estándar (factor XI)

- **Qué se busca:** la aplicación escribe sus eventos en la salida estándar (idealmente en formato estructurado, por ejemplo JSON); recogerlos y guardarlos es tarea de la plataforma.  
- **Señales de falla:** el logger escribe en archivos propios (`app.log`, rotación de archivos); `console.log` sueltos con datos sensibles.  
- **Comandos sugeridos:**  
    
  git grep \-nE "transports\\.File|DailyRotateFile|pino\\.destination|FileHandler|RotatingFileHandler|logging\\.file|logback.\*FILE" \-- .  
    
  git grep \-nE "winston|pino|nestjs-pino|Logger|logging\\.basicConfig|logback" \-- \<carpetas de código\>  
    
- **Evidencia:**
  - `git grep -nE "FileHandler|RotatingFileHandler|TimedRotating|logging\.file|\.log['\"]" release/8.0.0 -- backend-admin backend-clinic backend-ml ':!*/tests/*'` → sin resultados: **ningún servicio escribe logs en archivos**.
  - **backend-admin** — `admin_backend/settings.py:260-285`: `LOGGING` con un único `logging.StreamHandler` (consola) para los loggers `apps` y `auditlog`; formato de texto `{levelname} {asctime} {name} {message}`, no JSON.
  - **backend-clinic** — `git grep -c LOGGING release/8.0.0 -- backend-clinic/clinic_backend/settings.py` → 0: sin configuración. Cinco módulos crean `logging.getLogger(__name__)` (`agente.py:42`, `fuentes_confiables.py:54`, `llm_client.py:29`, `rag_qa.py:49`, `tool_router.py:35`). Sin handlers configurados, Python solo emite `WARNING` y superiores; los `logger.info` se pierden.
  - **backend-ml** — `git grep -nE "logging|logger" release/8.0.0 -- backend-ml/app` → sin resultados: no registra nada propio, solo el acceso de uvicorn.
- **Estado:** PARCIAL
- **Observación:** Se cumple lo esencial: nadie escribe en archivos y lo que se registra sale por la consola. Falta: (1) `backend-clinic` y `backend-ml` no tienen configuración de logs, y en el clínico se pierden los mensajes informativos; (2) no hay formato estructurado ni identificador de traza, que se necesitarán para explicar latencias con OpenTelemetry.
- **Auditó:** Guillermo Mamani Chambi

### F12-05 · Servicios de apoyo intercambiables (factor IV)

- **Qué se busca:** base de datos, colas, caché, almacenamiento y servicio de IA se conectan por una URL o variables de configuración, de modo que cambiar uno (por ejemplo, la base local por una gestionada) no exige tocar el código.  
- **Señales de falla:** el cliente de un servicio se construye con host, puerto o credenciales fijas; el código depende de un proveedor concreto sin una capa que lo aísle.  
- **Comandos sugeridos:**  
    
  git grep \-nE "DATABASE\_URL|REDIS\_URL|AMQP\_URL|S3\_|BUCKET|OPENAI|ANTHROPIC|\_URL\\b" \-- \<carpetas de código\>  
    
  git grep \-nE "createConnection|TypeOrmModule\\.forRoot\\(|PrismaClient|create\_engine|MongoClient|new Redis\\(" \-- \<carpetas de código\>  
    
- **Evidencia:**
  - Comando: `git grep -nE "httpx\.Client|OpenAI\(|base_url|_URL" release/8.0.0 -- backend-clinic backend-admin ':!*/tests/*'`.
  - **Intercambiables por configuración**:
    - servicio de inferencia: `CLINIC_FASTAPI_URL` (`clinic_backend/settings.py:143`), usado en `apps/samples/pipeline_client.py:129`;
    - backend-admin, para la verificación MFA: `ADMIN_INTERNAL_URL` (`settings.py:156`), usado en `admin_client.py:59`;
    - LLM: `CLINIC_LLM_URL` (`settings.py:165`), usado en `llm_client.py:218` con el SDK estándar de OpenAI;
    - base de datos de admin: `POSTGRES_DB/USER/PASSWORD/HOST/PORT` (`admin_backend/settings.py:103-108`).
  - **No intercambiables**:
    - la base de datos del clínico tiene el motor fijo en el código, `ENGINE: django.db.backends.sqlite3` (`clinic_backend/settings.py:85-88`): pasar a PostgreSQL exige editar el código;
    - el almacenamiento de imágenes es el sistema de archivos local, sin capa de almacenamiento (`apps/samples/services.py:149-151`);
    - los embeddings del RAG usan una URL fija (`apps/samples/rag_index.py:63` y `:138`).
- **Estado:** PARCIAL
- **Observación:** Los servicios de red (inferencia, admin, LLM) se cambian con una variable, y el LLM pasa por el SDK estándar, que admite cambiar de proveedor. Pero el clínico no puede cambiar de base de datos ni de almacenamiento sin tocar código, y el RAG no sigue la URL configurada.
- **Auditó:** Guillermo Mamani Chambi

### F12-06 · Construcción inmutable y apagado limpio (factores V y IX)

- **Qué se busca:** se construye una vez (imagen o artefacto) y se ejecuta igual en todos los entornos, sin secretos dentro de la imagen; y el proceso, al recibir `SIGTERM`, deja de aceptar peticiones, termina lo que tiene en curso y cierra conexiones.  
- **Señales de falla:** `COPY .env` o `ENV` con secretos en el Dockerfile; `CMD` en forma de texto (`CMD npm start`) en lugar de forma exec; ningún manejo de cierre (en NestJS falta `app.enableShutdownHooks()`; en Spring alguien puso `server.shutdown: immediate`; en FastAPI no se cierran recursos en el `lifespan`).  
- **Comandos sugeridos:**  
    
  git ls-files | grep \-iE "dockerfile|compose"   
    
  git grep \-nE "COPY \\.env|^ENV .\*(PASS|SECRET|KEY|TOKEN)|^CMD \[^\\\[\]" \-- '\*Dockerfile\*'  
    
  git grep \-nE "SIGTERM|enableShutdownHooks|onModuleDestroy|beforeApplicationShutdown|server\\.shutdown|lifespan" \-- .  
    
- **Evidencia:**
  - `git ls-tree -r --name-only release/8.0.0 | grep -iE "dockerfile|compose|Procfile"` → sin resultados: **no hay Dockerfile, compose ni ningún artefacto de construcción**.
  - `git grep -nE "SIGTERM|signal\.|lifespan|on_event\(|shutdown|atexit" release/8.0.0 -- backend-admin backend-clinic backend-ml ':!*/tests/*'` → sin resultados en código: **ningún manejo de cierre**.
  - **backend-ml** — `app/main.py:18-22`: `FastAPI(...)` sin `lifespan`; el modelo se carga como variable global (`pipeline.py:28`).
  - **Recursos sin cierre en backend-clinic** — hilo del cliente MCP (`apps/samples/mcp_conexion.py:92`, `daemon=True`) y conexión SQLite global del agente (`agente_grafo.py:148`).
  - **Arranque documentado con servidores de desarrollo** — `runserver` (`backend-admin/README.md:67`) y `uvicorn --reload` (`backend-ml/README.md:15`). `gunicorn` está en `backend-admin/requirements.txt`, pero nada lo invoca.
- **Estado:** FALLA
- **Observación:** No existe una construcción inmutable: cada servicio se ejecuta desde el código fuente con su propio entorno virtual y servidor de desarrollo, así que lo que corre en una máquina no es necesariamente lo que corre en otra. Tampoco hay apagado controlado de los recursos propios (hilo MCP, conexión del agente, modelo). Hoy no hay ningún entorno distinto de la máquina de desarrollo (P1), así que la falta de imagen no ha causado diferencias entre entornos todavía; se resuelve en la sesión S07 (Docker multi-stage y Compose).
- **Auditó:** Guillermo Mamani Chambi

## 4\. Preguntas al grupo

| N.º | Comprobación | Pregunta | Respuesta del grupo | Estado (respondida / sin respuesta) |
| :---- | :---- | :---- | :---- | :---- |
| P1 | F12-03, F12-06 | El repositorio solo documenta la ejecución en la máquina de desarrollo. ¿El producto se despliega hoy en algún otro entorno (servidor del laboratorio, nube) y con cuántas instancias de cada servicio? | Solo en la máquina de desarrollo, una instancia por servicio. No hay servidor ni nube todavía. | respondida |

## 5\. Hallazgos priorizados

| \# | Comprobación | Severidad (alta / media / baja) | Qué falla | Corrección propuesta | Responsable | ¿Antes de contenedorizar (S07)? |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| 1 | F12-03 | alta | `backend-clinic` guarda imágenes, base de datos y memoria del agente en su disco local | Base de datos en PostgreSQL (como admin), imágenes en almacenamiento de objetos con metadatos en la BD, checkpointer del agente en PostgreSQL | Guillermo Mamani Chambi | Sí |
| 2 | F12-06 | alta | No hay construcción inmutable ni apagado controlado | Dockerfile multi-stage por servicio con `CMD` en forma exec (gunicorn/uvicorn sin `--reload`), `compose.yaml` y `lifespan` en FastAPI y cierre de recursos en el clínico | Guillermo Mamani Chambi | Sí (es el objetivo de S07) |
| 3 | F12-02 | media | Tres secretos tienen valor por defecto en el código; `.env` sin ignorar en `backend-ml` y `frontend-clinic` | `required=True` para `DJANGO_SECRET_KEY` e `INTERNAL_SERVICE_SECRET`; `.env` en el `.gitignore` raíz; `gitleaks` en pre-commit | Guillermo Mamani Chambi | Sí |
| 4 | F12-01 | media | El RAG ignora `CLINIC_LLM_URL`; el clínico arranca con `DEBUG=True` por defecto | Pasar `settings.CLINIC_LLM_URL` a `embeber()`; un solo punto de lectura de la URL; `DJANGO_DEBUG` por defecto `False` | Guillermo Mamani Chambi | Sí |
| 5 | F12-05 | media | El motor de base de datos del clínico está fijo en el código | Configurar la base por variables (`DATABASE_URL` o `POSTGRES_*`), igual que admin | Guillermo Mamani Chambi | Sí |
| 6 | F12-04 | baja | `backend-clinic` y `backend-ml` sin configuración de logs; formato de texto, sin traza | `LOGGING` a stdout en JSON con identificador de traza, junto con OpenTelemetry | Guillermo Mamani Chambi | No (puede ir con S12) |

## 6\. Autoverificación (la marca el asistente; el grupo la confirma)

- [x] Las seis comprobaciones F12-01 a F12-06 están en la sección 3, una vez cada una.  
- [x] Ninguna quedó en `PENDIENTE` ni sin estado; todos los estados son de los cinco permitidos.  
- [x] Todo estado distinto de `N/A` y `NO VERIFICABLE` tiene evidencia con ruta y línea, o con comando y salida.  
- [x] Cada `NO VERIFICABLE` y cada `N/A` explica su motivo. (No hay ninguno.)  
- [x] Todas las preguntas de la sección 4 están respondidas o marcadas "sin respuesta".  
- [x] Los hallazgos de severidad alta tienen responsable.  
- [x] No hay ningún secreto copiado en este archivo.  
- [x] No se modificó código del producto (`git diff --stat <commit auditado>..HEAD` solo muestra este archivo y el de aportes). Verificado: `git diff --stat release/8.0.0 c550d85` → solo `docs/auditoria/12factor.md` y `docs/auditoria/concurrencia.md` (2 files changed, 506 insertions). Las correcciones de los hallazgos van en commits posteriores (`89ad46b`, `3751877`, `209ff11`), no en el de la auditoría.  
- [x] Cada integrante aparece como auditor de al menos una comprobación y tiene al menos un commit con su propia identidad. Verificado: Guillermo Mamani Chambi audita todas las comprobaciones; el commit `c550d85` está firmado con su cuenta (`gh api .../commits/c550d85` → autor `guillemc92`).

## 7\. Resumen

| OK | PARCIAL | FALLA | N/A | NO VERIFICABLE | Preguntas sin respuesta |
| ----: | ----: | ----: | ----: | ----: | ----: |
| 0 | 4 | 2 | 0 | 0 | 0 |

**Conclusión en dos líneas:** La configuración y los secretos están bien encaminados: se leen del entorno, se validan al arrancar y no hay credenciales reales en el repositorio ni en su historial. Lo primero a corregir, antes de contenedorizar, es el estado local de `backend-clinic` (imágenes, SQLite y memoria del agente en disco) y la ausencia de una construcción inmutable.
