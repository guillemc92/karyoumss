# Architecture Decision Records (ADR)

Registro de decisiones arquitectónicas de **BIOMED UMSS — Plataforma de
Cariotipado Asistido por IA**.

Formato: MADR simplificado con frontmatter YAML — Contexto → Decisión →
Alternativas descartadas → Consecuencias.

> **La tabla de abajo se genera, no se escribe.** Se lee del frontmatter de cada
> fichero con `python docs/adr/generar_indice.py`. Un índice a mano se
> desincroniza: el 21/08/2026 había dos ADRs marcadas `proposed` que llevaban
> meses en producción, y nadie lo vio porque no había dónde verlo.

<!-- INDICE:INICIO -->

**36 ADRs**: 27 aceptada, 7 propuesta, 1 sin estado, 1 rechazada.

| ADR | Título | Estado | Fecha |
|-----|--------|--------|-------|
| [0001](0001-tiling.md) | Tiling and NMS for High-Resolution Meta-phase Images | Aceptada | 2026-05-20 |
| [0002](0002-async-pipeline.md) | Async Pipeline using Redis and Celery | Aceptada | 2026-05-22 |
| [0003](0003-chn-anonymization.md) | CHN Anonymization at the Edge | Aceptada | 2026-05-25 |
| [0004](0004-Estrategia-Evolucion-Arquitectonica.md) | Estrategia de Evolución Arquitectónica (Monolito Modular + Satélites) | **Propuesta** | 2026-05-29 |
| [0005](0005-cloud-provider-y-estilo-de-despliegue.md) | AWS Cloud Provider & Deployment Strategy | — | — |
| [0006](0006-semaforizacion-visual.md) | Implementación de Semaforización Visual Basada en Confidence Score | Aceptada | 2026-06-10 |
| [0007](0007-microservicio-inferencia.md) | Plan de Extracción de AI Inference a Servicio Satélite (Fase 2 de ADR-0004) | Aceptada | 2026-06-23 |
| [0008](0008-audit-trail-merkle.md) | Audit Trail Inmutable con Hash Chain + Extensión Merkle para Pruebas de Inclusión | Aceptada | 2026-06-23 |
| [0009](0009-websocket-celery-notifications.md) | Detalles Operativos del Push WebSocket (Implementación de ADR-0002) | Aceptada | 2026-06-23 |
| [0010](0010-testing-strategy.md) | Estrategia de Testing (TDD + Gherkin + Integración Clínica) | Aceptada | 2026-06-10 |
| [0011](0011-rol-administrador.md) | Diseño del Rol de Administrador (Inicio Simple) | Aceptada | 2026-06-23 |
| [0012](0012-persistencia-admin-postgres.md) | Persistencia de Usuarios Administrador en PostgreSQL con API Dedicada | Aceptada | 2026-06-27 |
| [0013](0013-stack-django-react-admin.md) | Stack de Administración — React 18 + Django REST Framework + PostgreSQL schema admin | Aceptada | 2026-06-27 |
| [0014](0014-configuracion-panel-react-real-backend.md) | Port del panel "Configuración del Sistema" desde configuracion.html a React con backend Django real | **Propuesta** | 2026-07-08 |
| [0015](0015-derogacion-parcial-0013.md) | Derogación Parcial de ADR-0013 — Stack Django + React para Bounded Context Muestras (Clínico) | Aceptada | 2026-07-12 |
| [0016](0016-registro-muestras-captura-metafases.md) | Registro de Muestras — PatientVault cifrada, SampleImage, estado DRAFT | Aceptada | 2026-07-12 |
| [0017](0017-sistema-autenticacion-login.md) | Sistema de Autenticación (Login) — backend-admin como autoridad JWT única | Aceptada | 2026-07-12 |
| [0018](0018-permisos-rol-backend-clinic.md) | Permisos por rol en backend-clinic — mapeo analista/supervisor/admin a is_staff/is_superuser | Aceptada | 2026-07-13 |
| [0019](0019-rbac-granular-funcionalidad-rol.md) | RBAC jerárquico (TipoObjeto→Objeto→Opción, Grupo con deny-overrides + excepción individual) en backend-clinic, portado del módulo Security/ real | **Propuesta** | 2026-07-17 |
| [0020](0020-sso-backend-admin-autoridad-jwt.md) | SSO real — backend-admin como autoridad única de JWT para todo el sistema (deroga parcialmente ADR-0015 D5 y ADR-0017 D7) | Aceptada | 2026-07-20 |
| [0021](0021-visor-correccion-cariotipo.md) | Visor y Corrección de Cariotipo — modelo de datos y arquitectura del editor clínico | Aceptada | 2026-07-23 |
| [0022](0022-audit-trail-clinico-django.md) | Audit Trail append-only del cariotipo en backend-clinic (Django) — materialización de ADR-0008 | Aceptada | 2026-07-23 |
| [0023](0023-supervisor-auditoria-firma-iscn.md) | Flujo del Supervisor — auditoría 5%, firma MFA y generación ISCN | Aceptada | 2026-07-24 |
| [0024](0024-llm-local-narrativa-informe.md) | LLM local (Ollama) para la narrativa del informe — IA generativa vía SDK | Aceptada | 2026-07-27 |
| [0025](0025-motor-iscn-en-django-clinico.md) | El motor ISCN vive en el Django clínico (deroga parcialmente ADR-0015) | Aceptada | 2026-07-28 |
| [0026](0026-estimacion-bandas-solapamientos.md) | Estimación de conteo de bandas y detección de solapamientos | Aceptada | 2026-08-05 |
| [0027](0027-rag-similitud-enrutado-consultas.md) | Enrutado por similitud vectorial (RAG) como tercer camino del tool calling | Rechazada | 2026-08-05 |
| [0028](0028-corpus-clinico-fundamentacion-narrativa.md) | Corpus clínico determinístico para fundamentar la narrativa asistida | Aceptada | 2026-08-06 |
| [0029](0029-rag-documental-corpus-proyecto.md) | RAG documental sobre el corpus del proyecto, con el modelo como juez de pertinencia | Aceptada | 2026-08-16 |
| [0030](0030-agente-react-servidor-mcp.md) | Un agente ReAct con guardrails, y las herramientas publicadas por MCP | Aceptada | 2026-08-16 |
| [0031](0031-orquestacion-pipeline-clinico.md) | La orquestación del pipeline clínico es una cola de tareas, no un sistema multiagente | Aceptada | 2026-08-17 |
| [0032](0032-memoria-conversacional-langgraph.md) | Memoria conversacional del agente con LangGraph — y por qué el estado clínico no entra ahí | Aceptada | 2026-08-18 |
| [0033](0033-asignacion-global-cariotipo.md) | Asignación global con cupos blandos — el modelo propone la clase, el código reparte el cariotipo | **Propuesta** | 2026-08-21 |
| [0034](0034-segmentacion-interactiva-sam2.md) | Segmentación interactiva asistida (SAM 2) — y la anotación como producto secundario | **Propuesta** | 2026-08-31 |
| [0035](0035-detector-instancias-cromosomas.md) | Detector de instancias de cromosomas — decisión diferida, con protocolo de evaluación y derogación de AGENTS §11 | **Propuesta** | 2026-08-31 |
| [0036](0036-multimetafase-consenso.md) | El consenso multi-metáfase se difiere — medido, hoy no hay nada sobre lo que votar | **Propuesta** | 2026-09-08 |

<!-- INDICE:FIN -->

## Cómo agregar una ADR

1. Copiar `template.md` a `NNNN-titulo-en-kebab-case.md`.
2. Estado inicial `proposed`. Pasa a `accepted`, `rejected` o `superseded`.
3. **Nunca editar el contenido de una ADR aceptada.** Se escribe una nueva que
   la reemplace o la derogue parcialmente — como hicieron ADR-0015 con la 0013
   y ADR-0025 con la 0015.
4. Regenerar el índice en el mismo PR: `python docs/adr/generar_indice.py`.

Para CI o un hook de pre-commit: `python docs/adr/generar_indice.py --check`
devuelve 1 si el índice está desactualizado o si alguna ADR tiene el
frontmatter incompleto.

## Estados, y qué significan aquí

| Estado | Significa |
|---|---|
| `proposed` | Decidido en el papel, **no** en el código |
| `accepted` | Implementado y en la rama principal |
| `rejected` | Se evaluó y se descartó — se conserva por el porqué |
| `superseded` | Reemplazada; el fichero dice por cuál |

**Una ADR `proposed` cuyo código ya está en producción es un defecto**, no un
matiz. Significa que se implementó sin cerrar la decisión, y que el registro
miente sobre el estado del sistema.

## Reglas propias de este proyecto

- **AGENTS.md es la fuente de verdad.** Una ADR que contradiga una regla
  constitucional (p. ej. §11, la prohibición de Mask R-CNN) debe **derogarla
  nominalmente** y actualizar `AGENTS.md` en el mismo cambio. Contradecirla en
  silencio invalida la ADR.
- **Toda afirmación con número lleva el comando que la reproduce.** Es la regla
  que sostiene el resto de la documentación del proyecto; las ADRs no se libran.
- Las decisiones que afectan a reglas clínicas (RN-01…RN-09) lo dicen
  explícitamente en Consecuencias.

## Relación con el resto de la documentación

- `docs/brd/` — qué problema de negocio se resuelve.
- `docs/fsd/` — cómo funciona el sistema hoy.
- `docs/adr/` — **por qué** se eligió cada enfoque y qué se descartó.
- `AGENTS.md` — las reglas que ninguna ADR puede saltarse sin derogarlas.
