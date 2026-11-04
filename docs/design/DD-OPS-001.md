# DD-OPS-001 — Imagen y stack de producción

| Campo | Valor |
|---|---|
| **Estado** | Aprobado por el autor el 2026-11-04 (respuestas en §9) |
| **Origen** | Demo 3 de M8, «Lo técnico de esta demo · 1. Imagen y stack de producción» |
| **Release** | `release/8.3.0` |
| **ADR relacionados** | ADR-0012 (schema `admin`), ADR-0013 (proxy unificado, F8 nunca hecho), ADR-0020 (SSO por mismo origen), ADR-0024 (LLM local) |

## 1. Qué pide la consigna

- **Imágenes:** un Dockerfile multi-stage por servicio.
- **Stack:** un `compose.yaml` que levante **todo** con
  `docker compose up -d --wait` desde un clon limpio.
- **Revisión:** hadolint y Trivy, sin hallazgos altos ni críticos sin justificar.
- **Demo:** se presenta sobre ese stack.

Lo que el docente detalló en la Clase08:
- base de datos con volumen y healthcheck;
- un job de migraciones que termine con código 0;
- `depends_on` con `service_healthy` y `service_completed_successfully`;
- el frontend empaquetado;
- los servicios de IA dentro del stack;
- usuario no root y versiones fijas, de preferencia con digest;
- secretos que no estén ni en git ni en la imagen;
- las revisiones en el CI.

## 2. Lo que hay hoy

| Servicio | Cómo corre en desarrollo | Imagen |
|---|---|---|
| backend-clinic (Django) | `runserver :8002`, SQLite | La del E3 (`backend-clinic/Dockerfile`) |
| backend-admin (Django) | `runserver :8001`; Postgres si `DB_ENGINE` no es `sqlite` | No hay |
| backend-ml (FastAPI, torch CPU) | `uvicorn :8000` | No hay |
| frontend-admin y frontend-clinic (React + Vite) | `vite :5173` / `:5174` | No hay |
| Proxy de un solo origen | `Caddyfile.dev` en `:3000` | No hay |
| LLM local | Ollama en el host, `:11434` | No hay |

## 3. Decisiones

### D1 · Servicios del stack

| Servicio | Imagen | Para qué |
|---|---|---|
| `secretos` | backend-clinic | Un solo uso: genera los secretos que falten (D3) |
| `postgres` | `postgres:17` con digest | La base de backend-admin, con el schema `admin` (ADR-0012) |
| `migrar-admin`, `migrar-clinic` | La de cada backend | `migrate`; terminan con 0 |
| `sembrar` | backend-admin | Crea los tres usuarios de la demo si no existen (D6) |
| `admin`, `clinic` | La de cada backend | gunicorn |
| `ml` | backend-ml | uvicorn, con el clasificador entrenado (`models/classifier.pth`) |
| `web` | Caddy con los dos frontends compilados | El único puerto publicado (D4) |
| `ollama`, `ollama-modelo` | `ollama/ollama` con digest | Solo con `--profile ia` (D5) |

### D2 · Bases de datos

- **backend-admin usa Postgres.** Su `settings.py` ya lo admite.
- **backend-clinic sigue con SQLite**, en el volumen `clinic-datos`, porque su código
  solo admite SQLite. Queda declarado como deuda.

### D3 · Secretos generados al primer arranque

- **Generación:** el job `secretos` escribe en el volumen `secretos` un archivo por
  cada secreto que falte, con permisos 600 y valores aleatorios.
  - Si un secreto ya existe, no lo toca. Así sobreviven a un `down`, pero no a un
    `down -v`.
- **Lectura:** `env()` en los dos `settings.py` acepta un fallback. Si la variable no
  existe y `BIOMED_SECRETS_DIR` apunta a una carpeta, lee el archivo de ese nombre.
  - Una variable de entorno, o un `.env` del host, gana siempre.
  - Sin ninguna de las dos fuentes, sigue fallando como hoy (issue #4).
- **Postgres** lee su contraseña con `POSTGRES_PASSWORD_FILE`.
- Nada de esto queda en git ni en una capa de imagen.

### D4 · Un solo origen

- **El servicio `web`** es una imagen multi-stage: compila los dos frontends con Node
  y entrega solo `dist/` a una imagen de Caddy.
- **Rutas:** la misma tabla que `Caddyfile.dev`:

  | Ruta | Destino |
  |---|---|
  | `/` | frontend-admin |
  | `/clinic/` | frontend-clinic, construido con `VITE_BASE_PATH=/clinic/` |
  | `/api/clinic/` | `clinic` |
  | `/api/admin/` y `/api/auth/` | `admin` |

- **SSO:** al compartir origen, la sesión se comparte (ADR-0020).
- **Puerto:** solo se publica `127.0.0.1:8080`. backend-ml, Postgres y los backends no
  se publican.

### D5 · El LLM, opcional

- **Por omisión:** `CLINIC_LLM_ENABLED=false`, y la narrativa se degrada sola (RN-07).
- **Con `--profile ia`:** se levanta Ollama, el job `ollama-modelo` descarga
  `llama3.2:3b` y `clinic` apunta a `http://ollama:11434/v1`.
- **Por qué no siempre:** son unos 2 GB de descarga en el primer `up`.

### D6 · Usuarios de la demo

- **Qué crea:** `manage.py sembrar_stack`, en backend-admin, crea `admin@biomed.local`,
  `analista@biomed.local` y `supervisor@biomed.local` con `create_admin_user`.
- **Contraseñas:** salen del volumen `secretos`, generadas como el resto.
- **Para consultarlas:**

      docker compose run --rm secretos cat /secretos/DEMO_PASSWORD_ANALISTA

- **Idempotente:** si un usuario ya existe, no lo toca.

### D7 · Imágenes

- **Base:** Python 3.12.7-slim y Node 22, con versión fija.
- **Multi-stage:** las dependencias se compilan en una etapa y solo pasan las ruedas
  o `dist/`.
- **Usuario:** no root, uid 10001.
- **Healthchecks:** el de cada servicio está en el Dockerfile y en el compose.
  - Los Django sirven `/admin/login/`. Así no hace falta código nuevo.
  - backend-ml sirve `/health/`.
  - Caddy, `/`.
- **Tiempos:** gunicorn de `clinic` con un timeout de 180 s, y
  `CLINIC_FASTAPI_TIMEOUT=120`. Segmentar una metafase tarda unos 19 s, y el plazo
  de 2 s de desarrollo cortaría la petición.
- **backend-ml:** torch CPU desde el índice oficial de PyTorch, con versiones fijas.

### D8 · Revisión y CI

- **Workflow nuevo:** `.github/workflows/imagenes.yml`, en cada PR y cada push a
  `release/**`.
- **hadolint** sobre cada Dockerfile.
- **`trivy config`** sobre los Dockerfiles y el compose.
- **`trivy image`** sobre cada imagen construida, con `--severity HIGH,CRITICAL`.
- **Prueba de humo:** `docker compose up -d --wait` desde el checkout, que es un clon
  limpio, seguida de un login real.
- **Hallazgos justificados:** van en `.trivyignore`, cada uno con su motivo. Los que
  sean de riesgo aceptado van además en un ADR.

## 4. Fuera de alcance, declarado

- **Postgres para backend-clinic:** exige cambiar su código. Es deuda.
- **TLS:** el stack es local (`127.0.0.1`).
- **Escalado y orquestador:** no hay Kubernetes.
- **Metafases:** el clon no trae ninguna (`datasets/` está ignorado). En la demo se
  sube una desde el registro de muestras.

## 5. Pruebas

| Qué | Cómo |
|---|---|
| Fallback de secretos | Pruebas unitarias de `env()` en los dos backends: la variable gana, el archivo se lee, sin ninguno se falla |
| `sembrar_stack` | Crea los tres usuarios; una segunda corrida no cambia nada; sin la contraseña, falla con un mensaje claro |
| Imágenes | hadolint y Trivy en el CI |
| Stack | En el CI: `up -d --wait`, login con `/api/auth/login/` a través de `web` y `GET /api/clinic/samples/` con ese token |
| Cobertura | RN-09 ≥ 90 % en los dos backends |

## 6. Plan

| # | Tarea |
|---|---|
| T1 | Fallback de secretos en `env()` y `sembrar_stack`, con pruebas |
| T2 | Dockerfiles de backend-admin, backend-ml y `web`, y ajustes del de backend-clinic |
| T3 | `compose.yaml` con healthchecks, jobs, volúmenes y el perfil `ia` |
| T4 | hadolint y Trivy en local; corrección o justificación de cada hallazgo |
| T5 | Workflow del CI, demo-3.md y aportes |

## 9. Respuestas (aprobación del 2026-11-04)

1. **Funcionalidades de la Demo 3:** stack de producción y análisis E3. El enderezado se
   muestra sobre el stack, pero sale de la tabla.
2. **Base de datos:** Postgres para admin, SQLite para clinic.
3. **LLM:** Ollama en un perfil opcional.
4. **Secretos:** generados al primer arranque.

## 10. Verificación (2026-11-04)

| Qué | Resultado |
|---|---|
| hadolint 2.15.1 | 0 hallazgos en los 4 Dockerfiles. El único aviso de la primera pasada (DL3066: `USER` con nombre) se corrigió con el uid numérico |
| `trivy config` 0.75.0 | 0 en los 4 Dockerfiles, en todas las severidades |
| `trivy image`, HIGH y CRITICAL con parche | **0 en las 4 imágenes**, después de actualizar (ADR-0039) |
| `docker compose up -d --wait` desde cero | Todo `healthy` y los 3 jobs terminados con 0; 55 s con las imágenes ya construidas |
| `deploy/humo.sh` | 7 de 7. Con un token falso, el paso 3 da FALLA y termina con 1 |
| Flujo clínico por `web:8080` | Login del analista, registro con 3 metafases BMP reales (201, 25 s), segmentación en backend-ml y cariotipo de 38 cromosomas, todos con silueta |
| backend-clinic con Django 5.2.18 | 1.181 de 1.182 y 91,31 %. La que falló (`test_decide_unknown_chromosome_404`) pasa sola y con su archivo (25 de 25): falla solo bajo carga |
| backend-admin con Django 5.2.18 | 355 de 356. `test_ordering_most_recent_first` es intermitente desde antes: en la release sin tocar pasó 2 de 3 veces |
| Contrato OpenAPI | Idéntico con las versiones nuevas: solo cambiaba el fin de línea del checkout |

**Fallos reales que destapó el stack**:
- **Dependencias no declaradas.** `rag_index.py` importa numpy, y `mcp_conexion.py`
  importa mcp. Ninguno de los dos estaba en `requirements.txt`. En el venv de
  desarrollo estaban instalados a mano, así que en la imagen el RAG habría dado 500.
- **Límite de tamaño de la petición.** Tres metafases BMP reales en base64 suman
  ~13 MB, y Django las rechazaba con un 400 genérico por su límite de 2,5 MB. Ahora
  el límite es `CLINIC_MAX_PETICION_MB`, 32 por defecto.
- **Tipos de las pruebas de frontend-admin.** `npm run build` comprueba también los
  tipos de las pruebas, y tres no compilaban. Desde un clon limpio, el build fallaba.

**Fallos del instrumento, cazados antes de creer el resultado**:
- **La prueba de humo daba verde con un paso fallido.** `cmd && ok` no dispara
  `set -e`. Se reescribió para que cada paso corte el script.
- **Git Bash reescribía las rutas.** Convertía `/secretos/…` y `/dev/null` en rutas
  de Windows. Se arregló con `MSYS_NO_PATHCONV` y sin archivos temporales.
