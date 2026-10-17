# DD-AUD-001 — Correcciones de la auditoría 8.0.0 (concurrencia y secretos)

| Campo | Valor |
|---|---|
| **ID** | DD-AUD-001 |
| **Origen** | Auditorías de M8 sobre `release/8.0.0` (`d4175a9`): [`docs/auditoria/concurrencia.md`](../auditoria/concurrencia.md) y [`docs/auditoria/12factor.md`](../auditoria/12factor.md) |
| **ADR relacionados** | ADR-0007 (microservicio de inferencia), ADR-0015 #6 (circuit breaker), ADR-0024 (LLM local) |
| **Reglas** | RN-03 (sin PII), RN-07 (degradación elegante), RN-09 (cobertura ≥ 90 %) |
| **Estado** | **Aprobado** por el autor el 2026-10-16 · en implementación · issues #2, #3 y #4 |
| **Fecha** | 2026-10-16 |
| **Entrega** | Demo 1 de M8, lunes 19 de octubre de 2026 (`release/8.1.0`) |

## 1. Alcance

Tres correcciones, una por issue de GitHub, elegidas por severidad entre los
hallazgos de la auditoría. Ninguna cambia la API pública ni el comportamiento
clínico; cambian **cómo se comporta el sistema cuando hay varias peticiones a
la vez o falta configuración**.

| Feature | Hallazgo | Severidad |
|---|---|---|
| F1 · La inferencia deja de congelar backend-ml | CON-02 | alta |
| F2 · Llamadas al LLM con reintentos explícitos y límite de concurrencia | CON-04 | alta |
| F3 · Sin secretos por defecto ni `.env` sin ignorar | F12-02 (+ `DEBUG` de F12-01) | media |

## 2. F1 · La inferencia deja de congelar backend-ml (CON-02)

**Problema medido.** Los tres endpoints de inferencia son `async def` y hacen
unos 19 s de CPU síncrona (mediana sobre 5 metafases reales). Mientras dura,
el único event loop de uvicorn no atiende nada, ni siquiera `/health/`.

**Decisiones.**
- **D1.1** `segment`, `xai` y `classify` pasan a `def`. FastAPI los ejecuta
  en su threadpool y el event loop queda libre para `/health/` y para aceptar
  conexiones. La firma y la respuesta de los endpoints no cambian.
- **D1.2** Un `threading.BoundedSemaphore` limita las inferencias simultáneas
  (`ML_MAX_INFERENCIAS`, por defecto **1**). La CPU tiene 4 núcleos y PyTorch
  ya usa varios hilos por inferencia: dos en paralelo no van más rápido, se
  reparten la CPU.
- **D1.3** Contrapresión: si el semáforo no se obtiene en `ML_ESPERA_MAX_S`
  (por defecto **25 s**, por debajo de los 30 s del cliente), el endpoint
  responde **503 con `Retry-After`** en vez de dejar la petición colgada. El
  cliente ya trata el 503 como degradación (RN-07).
- **D1.4** La carga perezosa del clasificador (`pipeline.py:26-35`) se protege
  con un `Lock`. Con hilos, dos peticiones a la vez cargarían el modelo dos
  veces (16 s y ~42 MB cada vez).

**Criterios de aceptación.**
1. Con una inferencia en curso, `GET /health/` responde en menos de 1 s.
2. Con `ML_MAX_INFERENCIAS=1`, una segunda inferencia simultánea espera; si
   supera `ML_ESPERA_MAX_S`, recibe 503 con `Retry-After`.
3. Dos peticiones simultáneas cargan el modelo **una** sola vez.
4. Las pruebas existentes de `backend-ml/tests/` siguen en verde.

## 3. F2 · Llamadas al LLM con reintentos explícitos y límite de concurrencia (CON-04)

**Problema.** El SDK de OpenAI reintenta 2 veces por defecto también tras un
timeout (`openai/_base_client.py:1095-1105`, `DEFAULT_MAX_RETRIES = 2`). Con
`CLINIC_LLM_TIMEOUT = 240 s`, una petición puede esperar unos 12 minutos. No
hay límite de llamadas simultáneas, y el LLM tarda entre 30 y 120 s por
respuesta (P4 de la auditoría).

**Decisiones.**
- **D2.1** Un único punto construye los clientes del LLM
  (`crear_cliente_llm()` en `llm_client.py`). Lo usan los cinco sitios que hoy
  lo construyen por separado: `llm_client.py`, `tool_router.py`, `rag_qa.py`,
  `agente.py` y `agente_grafo.py` (`ChatOpenAI`, `max_retries` equivalente).
- **D2.2** `max_retries` explícito, `CLINIC_LLM_MAX_RETRIES`, por defecto **0**.
  Un reintento tras 240 s de espera solo duplica la espera del usuario; los
  fallos de disponibilidad ya los cubre el circuit breaker.
- **D2.3** Semáforo para el LLM, `CLINIC_LLM_MAX_CONCURRENTES`, por defecto
  **2**, con espera máxima `CLINIC_LLM_ESPERA_MAX_S` (por defecto 5 s). Si no
  hay hueco, se lanza `LlmServiceError('ocupado')`, que ya degrada:
  - narrativa no disponible, y el informe se emite igual (ADR-0024 D3);
  - el chat responde que el asistente está ocupado.
  Un rechazo por ocupado **no abre** el circuit breaker: no es un fallo del
  servicio.

**Criterios de aceptación.**
1. Todos los clientes del LLM se crean con `max_retries` igual a
   `CLINIC_LLM_MAX_RETRIES`; una prueba lo comprueba en los cinco sitios.
2. Con el límite alcanzado, una llamada más recibe `LlmServiceError('ocupado')`
   en ≤ `CLINIC_LLM_ESPERA_MAX_S`, y el circuito sigue cerrado.
3. Con hueco libre, el comportamiento actual no cambia (pruebas existentes en
   verde).

## 4. F3 · Sin secretos por defecto ni `.env` sin ignorar (F12-02)

**Problema.** Tres secretos tienen un valor por defecto escrito en el código
(`backend-clinic/clinic_backend/settings.py:30` y `:157`,
`backend-admin/admin_backend/settings.py:195`). Si el despliegue olvida la
variable, el servicio arranca con un secreto que conoce cualquiera con acceso
al repositorio. `backend-ml/.env` y `frontend-clinic/.env` no están ignorados.
Además, `backend-clinic` arranca con `DEBUG=True` por defecto
(`settings.py:31`).

**Decisiones.**
- **D3.1** `DJANGO_SECRET_KEY` (clinic) e `INTERNAL_SERVICE_SECRET` (clinic y
  admin) pasan a `required=True`: si faltan, el proceso no arranca y dice cuál.
- **D3.2** `DJANGO_DEBUG` del clínico, por defecto `False`, como en admin.
- **D3.3** Los valores de prueba se fijan **solo en las pruebas**, como ya
  hace admin en `settings_test.py:29-32` (`os.environ.setdefault`), sin tocar
  los `.env` reales de nadie.
- **D3.4** El `.gitignore` raíz ignora `.env` en cualquier carpeta (excepto
  `.env.example`). Los `.env.example` documentan las variables nuevas de F1, F2
  y F3, sin valores reales.

**Criterios de aceptación.**
1. Sin `DJANGO_SECRET_KEY` o sin `INTERNAL_SERVICE_SECRET`, el arranque falla
   con `Missing required env var: <nombre>`.
2. Sin `DJANGO_DEBUG`, el clínico arranca con `DEBUG=False`.
3. `git check-ignore -v backend-ml/.env frontend-clinic/.env` muestra una
   regla; `git check-ignore backend-ml/.env.example` no.
4. Las suites de clinic y admin siguen en verde.

## 5. Fuera de alcance

- Pasar el clínico a PostgreSQL y las imágenes a almacenamiento de objetos
  (F12-03, F12-05): es trabajo de S05–S07 con Docker Compose.
- Dockerfiles y apagado limpio (F12-06): sesión S07.
- Narrativa por cola + 202 y streaming (CON-04, punto 4): queda para el
  experimento E4 (llamada síncrona frente a cola + worker).
- Logs estructurados (F12-04): con OpenTelemetry, S12.

## 6. Pruebas (RN-09 ≥ 90 %)

| Feature | Pruebas |
|---|---|
| F1 | `backend-ml/tests/test_concurrencia.py`: `/health/` responde durante una inferencia lenta simulada; 503 + `Retry-After` al agotar la espera; carga única del modelo con dos hilos. |
| F2 | `backend-clinic/apps/samples/tests/test_llm_limites.py`: `max_retries` en los cinco constructores; rechazo por ocupado sin abrir el circuito; comportamiento normal con hueco. |
| F3 | Pruebas de settings: arranque fallido sin los secretos (subproceso con entorno limpio), `DEBUG` por defecto `False`; comprobación de `git check-ignore`. |

## 7. Plan

| # | Tarea | Issue | Estimación |
|---|---|---|---|
| T1 | F1: endpoints `def`, semáforo, 503 + `Retry-After`, lock del modelo, pruebas | Issue 1 | 2,5 h |
| T2 | F2: `crear_cliente_llm()`, `max_retries`, semáforo, pruebas | Issue 2 | 2,5 h |
| T3 | F3: secretos obligatorios, `DEBUG`, `.gitignore`, `.env.example`, pruebas | Issue 3 | 1,5 h |
| T4 | Demostración: dos segmentaciones simultáneas con `/health/` respondiendo; `release/8.1.0` y `8.1.0-aportes.md` | — | 1 h |
