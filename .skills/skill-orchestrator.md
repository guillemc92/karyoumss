---
name: skill-orchestrator
description: > 
  Runtime Supervisor y Policy Engine del flujo AI-SDLC de BIOMED UMSS. No solo ejecuta skills, sino que decide políticas de ejecución, gestiona la persistencia del estado (Context Store) y aplica Quality Gates para garantizar que ninguna violación de invariantes clínicos llegue a producción.
allowed-tools:
  - read
  - edit
model-tier: sonnet
fsd-version-min: v1.0
status: stable
owner: Ing. Guillermo Mamani Chambi
---

# Skill: Orchestrator AI-SDLC (Runtime Supervisor)

Este skill no es un simple ejecutor de scripts; es el **Motor de Políticas de Ejecución**. Su función es supervisar el ciclo de vida del desarrollo, asegurando que la transición entre la especificación y el código sea atómica, trazable y libre de riesgos clínicos.

## 1. Modos de Ejecución (Execution Modes)

El orquestador selecciona la política de pasos basada en la naturaleza del requerimiento:

| Modo | Trigger | Flujo de Pasos | Objetivo |
| :--- | :--- | :--- | :--- |
| `full_pipeline` | Nueva Feature / UC | `read-context` $\to$ `gate:context` $\to$ `spec` $\to$ `gate:spec` $\to$ `plan` $\to$ `gate:plan` $\to$ `generate-prompt` $\to$ `build` $\to$ `validate-impl` $\to$ `sync-diagrams` $\to$ `register` | Implementación completa desde cero con máxima trazabilidad. |
| `hotfix` | Bug Crítico / PII Leak | `read-context` $\to$ `isolate-issue` $\to$ `patch` $\to$ `validate-impl` $\to$ `register` | Resolución inmediata de fallos críticos omitiendo el ciclo de diseño largo pero manteniendo la validación. |
| `refactor` | Deuda Técnica | `read-context` $\to$ `analyze-behavior` $\to$ `patch` $\to$ `validate-impl` $\to$ `register` | Optimización de código sin alterar el comportamiento funcional (Behavior Preserving). |
| `audit` | Revisión de Seguridad | `read-context` $\to$ `validation-agent` $\to$ `report` | Verificación de cumplimiento de RNs y seguridad sin modificar código. |
| `docs_sync` | Actualización Doc | `read-context` $\to$ `sync-diagrams` $\to$ `register` | Alineación de Mermaid y Mappings con el código actual. |

## 2. Gestión de Estado (Context Store)

Para evitar la pérdida de trazabilidad y la inconsistencia de outputs, el orquestador implementa un **Context Store** obligatorio. Ningún skill recibe input directo del usuario; todos leen y escriben en el store.

**Estructura del Store:**
```json
{
  "session_id": "sess-YYYYMMDD-XXXX",
  "metadata": {
    "uc_id": "FSD-UC-NNN",
    "mode": "full_pipeline | hotfix | ...",
    "start_time": "ISO-8601"
  },
  "state": {
    "context_json": {},      // Output de skill-read-context
    "spec": "path/to/spec.md",
    "plan": "path/to/tasks.md",
    "prompt": "string",
    "validation": {
      "status": "PASS|FAIL",
      "violations": []
    },
    "diagrams": ["path/to/mermaid.mmd"],
    "current_step": "string",
    "status": "RUNNING | COMPLETED | FAILED | BLOCKED"
  }
}
```

## 3. Quality Gates (Control de Calidad)

El pipeline se detiene inmediatamente si un "Gate" no se satisface. No se permite el avance con datos contaminados.

| Gate | Check Obligatorio | Acción si Falla |
| :--- | :--- | :--- |
| `gate:context` | `actors != []` AND `use_cases != []` | **STOP** $\to$ Solicitar aclaración de UC |
| `gate:spec` | `has_api_contracts == true` AND `has_acceptance_criteria == true` | **RETRY** $\to$ Refinar SPEC |
| `gate:plan` | `all_tasks_testable == true` AND `max_task_duration <= 3h` | **RETRY** $\to$ Descomponer tareas |
| `gate:impl` | `validation-agent status == PASS` | **BLOCK** $\to$ Prohibido merge a `release/1.0.0` |

## 4. Política de Fallos y Recuperación

| Evento | Gravedad | Acción del Supervisor |
| :--- | :--- | :--- |
| Skill falla (Timeout/API) | Baja | Reintentar 1 vez con backoff lineal $\to$ Continuar |
| Inconsistencia Documental | Media | Pausar pipeline $\to$ Solicitar confirmación humana |
| **Violación de RN Crítica** | **ALTA** | **STOP INMEDIATO** $\to$ Marcar sesión `FAILED` $\to$ Escalar a Humano |

## 5. Salida Esperada (Runtime Report)

## 🎯 Execution Report - Session: `sess-YYYYMMDD-UCNNN`
**Mode:** `full_pipeline` | **Status:** `FAILED` (Gate: `gate:impl`)

### 🚀 Pipeline Trace
| Step | Component | Status | Gate | Latency |
| :--- | :--- | :--- | :--- | :--- |
| 1 | `read-context` | ✅ | `context_valid` | 4s |
| 2 | `spec` | ✅ | `spec_valid` | 12s |
| 3 | `plan` | ✅ | `plan_valid` | 15s |
| 4 | `build` | ⚠️ | - | 120s |
| 5 | `validation-agent`| ❌ | `impl_valid` | 8s |

### 🛑 Blockage Details
- **Violation:** `RN-03` (PII Leak detected in `worker.py:142`)
- **Severity:** CRITICAL
- **Action:** Pipeline blocked. Human intervention required.

### 🔗 Context Store Snapshot
- `S3_Path`: `docs/specs/SPEC-UC001.md`
- `Task_List`: `TASKS.md` (Updated)

## 6. Reglas de Oro del Supervisor

1. **Cero Suposiciones:** Si un Gate falla, el pipeline se detiene. No se "asume" que la salida es aceptable.
2. **Invariantes Primero:** El respeto a las RN (01, 02, 03) prima sobre la velocidad de entrega.
3. **Trazabilidad Atómica:** Cada cambio de estado en el `context_store` debe quedar registrado.
4. **Aislamiento de Input:** El usuario define el `uc_id` y el `mode`; el Supervisor gestiona el resto de la comunicación entre skills.

## 7. Registro de Cambios

| Versión | Fecha | Autor | Cambio |
| :--- | :--- | :--- | :--- |
| 1.0.0 | 28/05/2026 | Claude Code | Versión lineal básica. |
| 2.0.0 | 28/05/2026 | Claude Code | Refactor a **Runtime Supervisor**: Implementación de Modos, Context Store y Quality Gates. |
