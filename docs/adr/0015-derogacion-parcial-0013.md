---
id: ADR-0015
title: Derogación Parcial de ADR-0013 — Stack Django + React para Bounded Context Muestras (Clínico)
date: 2026-07-12
status: accepted
supersedes: ADR-0013 §Decisión "Django se introduce solo para el bounded context admin, no reemplaza FastAPI globalmente" (parcialmente, solo para Muestras)
related: [ADR-0011, ADR-0013, ADR-0004, ADR-0007, DD-CRUD-MUESTRA-001, FSD-UC-001]
fase: desarrollo
autor: Ing. Guillermo Mamani Chambi
---

# ADR 0015: Derogación Parcial de ADR-0013 — Stack Django + React para Muestras (Clínico)

## Contexto

`ADR-0013` (2026-06-27) formalizó la división de stack por bounded context: **Django 5 + DRF + React 18 para el admin**; **FastAPI + vanilla HTML para el clínico** (pipeline U-Net + EfficientNet-B3 + Grad-CAM + audit Merkle). El `DD-CRUD-MUESTRA-001` (2026-07-11) propuso inicialmente mantener el CRUD de Muestras en FastAPI + vanilla HTML, decisión que respetaba el split del ADR-0013.

El arquitecto reconsideró en sesión 2026-07-12 con la siguiente motivación:

1. **Consistencia arquitectónica:** el bounded context Muestras es un CRUD tabular clásico sobre 9 campos (CHN, status, analyst FK, etc.), funcionalmente análogo al CRUD de AdminUser. Reusar el mismo stack (Django/DRF/React) reduce la fragmentación cognitiva del equipo.

2. **DX + tooling maduro:** el equipo ya invirtió 5 commits (`a58b52a`, `d3fab63`, `0b7aac0`, `032140e`, `7942ba8`) en bootstrap Django+DRF+React+MSW+vitest para el admin (RN-09 = 99% lines/funcs/statements). Replicar el patrón para Muestras es ~2× más rápido que improvisar uno nuevo sobre FastAPI vanilla.

3. **Pipeline de IA no se toca:** el FastAPI clínico (U-Net, EfficientNet, audit Merkle, Celery) sigue siendo dueño del pipeline de inferencia. El Django clínico solo consume el pipeline vía cliente HTTP (`pipeline_client.py` con circuit breaker), NO lo reescribe.

4. **Hallazgo clave:** el código FastAPI de Muestras **no existe en el repo** (verificado: no hay `backend/` ni `backend-clinic/` commiteados; `crudmuestra.html` es 100% vanilla con datos hardcoded en `localStorage`). Esto elimina el riesgo de "reescribir FastAPI de Muestras" — la "migración" es en realidad **poblar el seed Django con las 8 muestras del HTML legacy**.

5. **AGENTS §3 declarativo vs realidad:** React 18 + Vite 5 + TypeScript 5 están declarados como stack del proyecto pero solo el admin los operacionaliza. Extender la operacionalización a Muestras cumple la promesa de AGENTS §3.

## Decisión

**Derogar parcialmente ADR-0013** SOLO para el bounded context "Muestras" del clínico. Adoptar el siguiente stack para el CRUD de Muestras:

| Capa | Stack | Puerto / ruta |
|---|---|---|
| **Backend CRUD clínico (NUEVO, este ADR)** | Django 5 + DRF 3.15 + SimpleJWT 5 + SQLite (dev) | `:8002`, namespace `/api/clinic/` |
| **Frontend CRUD clínico (NUEVO, este ADR)** | React 18 + Vite 5 + TypeScript 5 + TanStack Query 5 + React Router 6 | `:5174` |
| **Backend pipeline clínico (intacto)** | FastAPI + Celery + Redis + PostgreSQL | `:8000`, ruta `/api/v1/samples/{id}/process/` |
| **Frontend pipeline clínico (intacto)** | vanilla HTML + JS (`correccion de cariotipo.html`, `supervisor.html`, `informe.html`, `registrarmuestrafinal.html`) | rutas legacy |

### Lo que se mantiene de ADR-0013 sin cambios

- **AGENTS §3 stack clínico predominante:** la pipeline U-Net + EfficientNet + Grad-CAM sigue en FastAPI. El Django clínico es un **satélite** del clínico FastAPI, no un reemplazo.
- **PostgreSQL como motor único en prod** (RN-09 docs); SQLite es solo para dev/demo, mismo patrón que `backend-admin/demo_admin.sqlite3` per `admin_backend/settings.py:91-100`.
- **AGENTS §3 React/Vite/TS:** ya declarados, ahora operacionalizados para 2 bounded contexts (admin + muestras).
- **AGENTS §11 no pushear a `main`:** rama `feature/clinic-django-stack` → PR a `release/2.0.0`.
- **RN-04/05:** `iscn_nomenclature` y `edits` siguen siendo read-only/append-only; el Django clínico NO los escribe, solo delega al FastAPI.
- **RN-06 segregación analista/supervisor/admin:** los 3 roles se replican en el Django clínico con scoping de queryset.
- **RN-09 cobertura ≥90%:** dos gates separados (`pytest --cov-fail-under=90` en `backend-clinic/`, `vitest --coverage` con thresholds 90/88/90/90 en `frontend-clinic/`).
- **ADR-0004 hexagonal + Strangler:** el Django clínico es un satélite del FastAPI clínico; ambos conviven sin refactor destructivo.

### Lo que se deroga de ADR-0013

- §Decisión "**Django se introduce solo para el bounded context admin**" — se amplía también al bounded context Muestras.
- §Estructura "**backend-clinical/ (existente, intacto)**" — se acepta que el clínico de Muestras es Django, mientras el pipeline sigue FastAPI.
- §Justificación "**Riesgo de regresión clínica → reescribir a Django duplica trabajo**" — refinado: Django **no reemplaza** el pipeline FastAPI, solo absorbe el catálogo CRUD que antes era vanilla HTML.

## Justificación

### Por qué derogar solo para Muestras (no para el clínico completo)

El clínico tiene **3 sub-bounded contexts** con naturalezas distintas:

| Sub-bounded context | Stack | Justificación |
|---|---|---|
| **Catálogo Muestras (CRUD)** | Django 5 + DRF (este ADR) | CRUD tabular sobre 9 campos; mismo perfil que AdminUser |
| **Pipeline de inferencia (U-Net + EfficientNet)** | FastAPI (intacto) | Async + Celery + TorchServe + Grad-CAM son idiomáticos en FastAPI |
| **Visor clínico (`correccion de cariotipo.html`)** | vanilla HTML + Konva (intacto) | Editor de cromosomas drag&drop con Konva.js; reescritura a React estimada en 4-6 sprints sin valor de release |

Derogar ADR-0013 para Muestras es coherente con la regla **"cada bounded context tiene su stack óptimo"** (ADR-0004 hexagonal), sin caer en la trampa de "Django global" o "React global".

### Por qué SimpleJWT propio y no reusar el auth_bridge del admin

- **Cero acoplamiento de tokens:** el admin usa `TokenAuthentication` DRF con `biomed.admin.token`; el clínico usa SimpleJWT HS256 con `biomed.clinic.access` + `biomed.clinic.refresh`. Tres namespaces de token distintos: ninguno comparte `AUTH_BRIDGE_SECRET`.
- **Costo operacional aceptable:** SimpleJWT es 1 línea en `INSTALLED_APPS` + 1 setting (`AUTH_CLINIC_SECRET`).
- **Riesgo mitigado:** si el Django clínico se compromete, el admin y FastAPI no quedan comprometidos. Defensa en profundidad.

### Por qué no reescribir `crudmuestra.html` como ruta React desde día 1

- **AGENTS §11 prohíbe romper lo que funciona.** `crudmuestra.html` es la única superficie operativa actual de Muestras.
- **Riesgo de regresión:** el HTML tiene un bug conocido (doble listener en `#btnNuevaMuestra`, líneas 727+730 del archivo) que podría amplificarse en React.
- **Decisión:** banner deprecado visible al cargar + link a nueva UI React en `:5174/clinic/samples`. Deprecación formal en release 2.1.

### Por qué `pipeline_client.py` con circuit breaker y no llamada directa

- **El FastAPI clínico no está commiteado en este repo** (verificado). El Django clínico debe ser **tolerante a FastAPI caído**: si el pipeline está en mantenimiento, el CRUD sigue funcionando y la UI muestra `DegradedBanner` (RN-07).
- **Circuit breaker simple (3 fallos → `MLDegradedError`):** evita que un FastAPI lento degrade el Django clínico. Ver R6 en el plan.
- **Cliente `httpx.AsyncClient` con timeout 2s:** un process de inferencia toma minutos; el endpoint `/process/` retorna `task_id` inmediato, pero la latencia de healthcheck debe ser corta.

## Consecuencias

### Positivas

- **Operacionaliza React/Django para un segundo bounded context.** Reduce la deuda técnica de AGENTS §3.
- **Reuso de patrón ya validado:** pytest-django, factory_boy, MSW, vitest, TanStack Query — todo ya en producción para el admin.
- **Mejor DX para Muestras:** filtros, paginación server-side, debounce de búsqueda, modal CRUD accesible, type safety con TypeScript.
- **RN-09 cobertura más fácil de sostener** con pytest-django + factory_boy (vs pytest-asyncio + httpx mock para FastAPI).
- **Coexistencia limpia:** FastAPI dueño del pipeline, Django dueño del catálogo, ambos vía contratos HTTP explícitos.

### Negativas

- **3er backend a mantener:** `backend-admin` (Django) + `backend-clinic` (Django, este ADR) + futuro `backend-clinical` (FastAPI cuando se commitee). Coste: doble deploy, triple secret management, monitorización.
  - **Mitigación:** `docker-compose.yml` documentado con los 4 procesos (T59 del plan); CI con matrix corre tests solo del stack modificado.
- **Doble auth bridge a la vista:** si en el futuro el FastAPI clínico se commitea, podría haber un puente FastAPI JWT → Django clínico SimpleJWT. Decisión pospuesta hasta que aparezca la necesidad (YAGNI).
- **Doble DB:** `backend-admin/demo_admin.sqlite3` + `backend-clinic/clinic_demo.sqlite3`. Mitigación: cada proceso abre su propio archivo físicamente, cero acoplamiento.
- **Curva de aprendizaje TanStack Query + React Router 6** si el equipo solo conoce vanilla JS del clínico.
- **Riesgo de scope creep:** tentación de migrar `correccion de cariotipo.html` o `supervisor.html` a React "ya que estamos". **Rechazado por este ADR** — el alcance es solo Muestras.

### Neutras

- TypeScript 5 sigue siendo el lenguaje del frontend clínico (nuevo).
- React 18 + Vite 5 se mantienen según AGENTS §3.
- Django 5 + DRF se mantienen según ADR-0013.
- Docker + docker-compose siguen siendo la estrategia de despliegue.

## Tensión con reglas del proyecto y cómo se resuelve

| Regla | Tensión | Resolución |
|---|---|---|
| **AGENTS §3 stack declarativo** (FastAPI para backend) | Este ADR introduce Django en el clínico | AGENTS §3 se actualiza en F10 del plan para aclarar: "bounded context admin y muestras → Django/DRF/React; pipeline clínico → FastAPI". El stack predominante del clínico sigue siendo FastAPI. |
| **ADR-0013 stack split "Django solo admin"** | Este ADR deroga parcialmente | Derogación **explícita y acotada** solo a Muestras; el resto del clínico (pipeline, audit Merkle, visor) sigue FastAPI. |
| **ADR-0004 hexagonal + Strangler** | ¿Django clínico es reemplazo o satélite? | Satélite del FastAPI clínico, no reemplazo. El Django consume el pipeline vía HTTP; no comparte schema, no comparte DB, no comparte auth. |
| **ADR-0011 segregación admin TI** | ¿Admin TI accede a datos clínicos? | No. El Django clínico es DIFERENTE proceso del Django admin. El Admin TI solo conoce el admin (DRF Token, `biomed.admin.token`). Cero tokens cruzados. |
| **RN-04 iscn_nomenclature read-only** | ¿Django clínico la edita? | NO. El Django clínico expone `patient_ref` y `metadata_json` solamente. `iscn_nomenclature` lo genera el FastAPI. Serializer rechaza explícitamente el campo. Test: `test_serializer_rejects_iscn_nomenclature`. |
| **RN-05 edits append-only** | ¿Django clínico escribe en `edits`? | NO. La tabla `edits` no existe en `backend-clinic/apps/samples/`. Verificado en grep post-implementación. |
| **RN-06 segregación analista/supervisor** | ¿Django clínico respeta scoping? | SÍ. `SampleService.list()` aplica `q.filter(analyst_id=request.user.id)` para rol analista. `permissions.py` tiene `IsAnalistaReadOnly`, `IsSupervisorOrAdmin`, `IsAdminOnly`. |
| **RN-07 modo degradado** | ¿Django clínico cae si FastAPI está caído? | NO. `pipeline_client.py` con circuit breaker (3 fallos → `MLDegradedError` → 503 con `code: ML_DEGRADED` → `DegradedBanner` en React). El CRUD sigue funcionando. |
| **RN-09 cobertura ≥90%** | ¿Cómo se mide? | 2 gates separados: `pytest --cov-fail-under=90` en `backend-clinic/`, `vitest --coverage` con thresholds 90/88/90/90 en `frontend-clinic/`. Mismo patrón que SPEC-007 + memoria `feedback-rn09-v8-html-trap`. |
| **AGENTS §11 no pushear a main, PR a release/2.0.0** | Este cambio es mayor | Rama `feature/clinic-django-stack` (NO `main`, NO `release/2.0.0` directo). PR con reviewers: Guillermo + 1 par. |

## Plan de migración

### 5.1 Datos del `crudmuestra.html` (8 muestras demo)

| Paso | Acción | Archivo |
|---|---|---|
| M1 | Extraer las 8 muestras del array `samples` (líneas 473-482 del HTML) a JSON canónico | `backend-clinic/fixtures/samples_seed.json` (NUEVO) |
| M2 | Mapear campos: `id` (CB-2026-XXXX) → `chn_code` (prefijo `CHN-`); `patientName` → `patient_ref` (ya pseudoanonimizado); `analyst` (3 strings) → 3 usuarios Django creados por `seed_analysts`; `gender`/`age`/`notes` → `metadata_json` (JSONField opcional) | (mapping en `import_legacy_samples.py`) |
| M3 | Status: `review` → `READY`, `processing` → `PROCESSING`, `completed` → `VALIDATED` | (mapping en el fixture) |

### 5.2 Datos en `localStorage` del usuario (caso opcional)

| Paso | Acción | Archivo |
|---|---|---|
| L1 | Usuario abre `crudmuestra.html` en su navegador | (navegador) |
| L2 | Banner deprecado (T58) lo invita a migrar; link a `export_localstorage_samples.js` | `crudmuestra.html` (MODIFICAR) |
| L3 | Usuario corre el script en la consola del navegador → descarga `samples-legacy-export.json` | `frontend-clinic/public/export_localstorage_samples.js` (NUEVO) |
| L4 | `python manage.py import_legacy_samples samples-legacy-export.json` ingesta las muestras al Django clínico | `backend-clinic/apps/samples/management/commands/import_legacy_samples.py` (NUEVO) |

### 5.3 `crudmuestra.html` legacy

| Paso | Acción |
|---|---|
| C1 | Banner deprecado al inicio del HTML: "Esta vista está deprecada. Use la nueva UI React en http://localhost:5174/clinic/samples" |
| C2 | NO se elimina el HTML (preserva AGENTS §11). Sigue funcionando offline con `localStorage`. |
| C3 | Deprecación formal programada para release 2.1. |

### 5.4 Pipeline FastAPI (no se migra)

El FastAPI clínico sigue dueño de `/api/v1/samples/{id}/process/` y `/api/v1/samples/{id}/status/`. El Django clínico consume esos endpoints vía `pipeline_client.py` con:
- `httpx.AsyncClient` apuntando a `CLINIC_FASTAPI_URL` (default `http://localhost:8000`).
- Timeout 2s.
- Circuit breaker: 3 fallos consecutivos → `MLDegradedError` → respuesta 503 al frontend → `DegradedBanner` (RN-07).

### 5.5 Bounded context admin (no se toca)

`backend-admin/` queda intacto. Mismo Django, otra app, otro puerto, otra DB. Cero acoplamiento.

## Decisiones técnicas fijadas

| # | Decisión | Valor | Por qué |
|---|---|---|---|
| 1 | Puerto backend Django clínico | `:8002` | `:8000` reservado para FastAPI clínico; `:8001` ocupado por `backend-admin` per `backend-admin/README.md` |
| 2 | Puerto frontend React clínico | `:5174` | `:5173` ocupado por `frontend-admin` per `frontend-admin/vite.config.ts`; `:5174` libre y sigue orden Vite |
| 3 | DB | SQLite archivo `backend-clinic/clinic_demo.sqlite3` | Mismo patrón que `backend-admin/demo_admin.sqlite3` (`settings.py:91-100` con override `DB_ENGINE=sqlite`) |
| 4 | Schema | Schema por defecto de SQLite (cero acoplamiento con `admin`) | DB físicamente separado |
| 5 | Auth | SimpleJWT HS256 propio con `AUTH_CLINIC_SECRET` INDEPENDIENTE | Tres namespaces de token: `biomed.admin.token`, `biomed.clinic.access`, `biomed.clinic.refresh` |
| 6 | Cliente Django → FastAPI | `httpx.AsyncClient` timeout 2s + circuit breaker 3 fallos | Tolerancia a FastAPI caído (R9 del plan) |
| 7 | Frontend → pipeline | React → Django → FastAPI (Django dueño del catálogo) | React nunca habla directo con FastAPI en este release |
| 8 | Seed 8 muestras | Fixture JSON + management command `seed_analysts` (3 usuarios) + `loaddata` | Cubre el seed base |
| 9 | `crudmuestra.html` legacy | Banner deprecado + NO eliminar | Cumple AGENTS §11 |
| 10 | CORS allowlist | `http://localhost:5174,http://localhost:3000` desde env `CORS_ALLOWED_ORIGINS` | Réplica del patrón admin |

## Alternativas evaluadas y rechazadas

### A1. Mantener CRUD de Muestras en FastAPI + vanilla HTML (status quo del DD-CRUD-MUESTRA-001 original)
- **Pro:** Respeta ADR-0013 al pie de la letra. Sin curva Django en el clínico.
- **Contra:** React/Django quedan "declarados pero operacionalizados a medias" (solo admin). El equipo tiene que aprender FastAPI CRUD + vanilla JS para Muestras, en vez de reusar el patrón Django ya validado. El HTML legacy tiene bugs conocidos (doble listener, datos hardcoded).
- **Rechazado** por inconsistencia con el patrón admin ya en producción.

### A2. Reescribir TODO el clínico a Django (reemplaza FastAPI también para pipeline)
- **Pro:** Stack unificado; un solo ORM; una sola pipeline de tests.
- **Contra:** 6+ sprints de reescritura del pipeline U-Net + EfficientNet + audit Merkle + Celery. Riesgo de regresión en código que cumple RN-01/02/04/05/06. Viola ADR-0004 hexagonal.
- **Rechazado** por coste/riesgo y por противоречия con ADR-0004.

### A3. Next.js full-stack (Node.js) + React
- **Pro:** Un solo lenguaje end-to-end.
- **Contra:** Introduce un cuarto stack (Node). No usa Django que es lo solicitado. Menos maduro para admin UI que Django. Mismo motivo de rechazo que ADR-0013 §A3.
- **Rechazado.**

### A4. NestJS (Node.js + TypeScript backend)
- **Pro:** TypeScript end-to-end con React; comunidad creciente.
- **Contra:** Introduce un cuarto stack. No usa Django. No hay expertise en el equipo.
- **Rechazado.**

### A5. FastAPI + React (sin Django)
- **Pro:** Stack clínico unificado (FastAPI) + frontend moderno.
- **Contra:** Inconsistente con admin (Django). React queda "declarado pero no operacionalizado" en el clínico. Equivale a una mini-derogación del ADR-0013 sin abordar la inconsistencia.
- **Rechazado** porque el arquitecto explícitamente pidió Django + React.

### A6. (Aceptada) Django 5 + DRF + SimpleJWT para CRUD Muestras + React 18 + Vite + TS + TanStack Query + React Router 6, con FastAPI intacto como dueño del pipeline.
- Ya descrita en §Decisión.

## Trazabilidad

- **Sube a:** BRD §3.1 (Cariotipado clínico) → FSD-UC-001 (Ingesta + CHN) → DD-CRUD-MUESTRA-001 §0 (decisión revertida) → **este ADR-0015**.
- **Genera:** `SPEC-008-crud-muestra-react.md` (contratos Gherkin + JSON + wireframes); `PR-IMPL-MUESTRA-002` (bootstrap Django clínico + React clínico + tests).
- **Impacta:**
  - `AGENTS.md` §3 (nueva entrada: "bounded context Muestras → Django/DRF/React, clínico predominante sigue FastAPI").
  - `AGENTS.md` §5 (tabla ADRs agregar ADR-0015).
  - `AGENTS.md` §6 (estructura agregar `backend-clinic/`, `frontend-clinic/`).
  - `DD-CRUD-MUESTRA-001.md` §0 (marca `superseded_by: ADR-0015`).
  - `docs/PROMPT_MAPPING.md` (agregar `PM-CRUD-MUESTRA-002`).
  - `docs/specs/SPEC-008-crud-muestra-react.md` (NUEVO).
  - `backend-clinic/` (NUEVO, ~30 archivos).
  - `frontend-clinic/` (NUEVO, ~60 archivos).
  - `crudmuestra.html` (MODIFICAR: banner deprecado).
  - `docker-compose.yml` raíz (NUEVO: documentar 4 servicios).

## Notas

- Este ADR **no afecta** el pipeline FastAPI de inferencia (U-Net + EfficientNet + audit Merkle + Celery).
- Este ADR **no afecta** el `correccion de cariotipo.html`, `supervisor.html`, `informe.html` ni `registrarmuestrafinal.html` (siguen vanilla).
- Este ADR **no afecta** el bounded context admin (Django admin intacto, otro puerto, otra DB).
- La rama de trabajo es `feature/clinic-django-stack` (no `main`, no `release/2.0.0` directo — restricción AGENTS §11).
- T0 (firmar este ADR) es prerrequisito de T1+ (código).
- Si en el futuro el FastAPI clínico se commitee y se desea integración más profunda, abrir un nuevo ADR (ADR-0016) en lugar de modificar este.
- Si el alcance crece (migrar `correccion de cariotipo.html` a React), abrir un ADR específico — NO extender este.
