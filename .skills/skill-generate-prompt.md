---
name: skill-generate-prompt
description: > 
  Arquitecto de prompts especializado en Spec-Driven Development. Transforma casos de uso del FSD en prompts de sistema listos para producción, asegurando que el agente implementador respete estrictamente los invariantes clínicos y la arquitectura de BIOMED UMSS.
allowed-tools:
  - read
model-tier: sonnet
fsd-version-min: v1.0
status: stable
owner: Ing. Guillermo Mamani Chambi
---

# Skill: Generador de Prompts de Implementación (Spec-Driven Prompting)

Este Skill actúa como un puente entre la especificación funcional y la ejecución de código. Su objetivo es generar un **System Prompt** tan preciso que cualquier agente de codificación pueda implementar la funcionalidad sin ambigüedades, sin alucinaciones de negocio y respetando todas las restricciones reguladoras.

## 1. Cuándo activarlo (triggers)
- **DURANTE:** La transición entre la planificación (`/plan`) y la codificación real.
- **ARRANCA cuando:** El usuario solicita un prompt de sistema para una tarea específica, menciona un ID de caso de uso (ej. `FSD-UC-001`) para generar instrucciones de IA, o invoca explícitamente `@skill-generate-prompt`.
- **NO ACTIVAR cuando:** El usuario está en fase de descubrimiento o definición de requerimientos; este Skill requiere una especificación (FSD) ya cerrada.

## 2. Entradas obligatorias (Inputs)
El usuario MUST proporcionar al menos una de:
- **ID del UC:** Referencia exacta a `FSD-UC-NNN`.
- **Contexto del FSD:** Texto o ruta al documento (`docs/FSD_v1.md`) con la descripción del flujo.
- **Fragmento de Spec:** El contenido de una especificación técnica (`SPEC_TEMPLATE.md`) ya generada.

## 3. Proceso de Construcción (Workflow)
El agente debe seguir estrictamente estos tres pasos:

### Paso 1: Extracción Analítica
Analizar la entrada para extraer:
- **Objetivo:** ¿Qué debe lograr exactamente el caso de uso?
- **Inputs:** Datos necesarios para iniciar la acción.
- **Outputs:** Resultados esperados y formatos (JSON, Status Codes, etc.).
- **Reglas de Negocio:** Todas las `RN-NNN` y `BR-NNN` asociadas.

### Paso 2: Transformación a Rol de Agente
Convertir la narrativa del FSD en instrucciones operativas:
- **Definición de Rol:** Asignar la identidad del experto (ej. "Experto en Backend FastAPI y Seguridad Biomédica").
- **Diseño del Flujo:** Traducir los pasos del UC en una secuencia de ejecución lógica y técnica.
- **Mapeo de Validaciones:** Convertir los criterios de aceptación en checks obligatorios dentro del prompt.

### Paso 3: Inyección de Invariantes
Inyectar las reglas críticas de `AGENTS.md` y el `DTI`:
- **RN-03:** Obligar a la anonimización CHN si hay datos PII o servicios cloud.
- **Semaforización:** Forzar la lógica de `score < 0.85` si el flujo implica validación.
- **Audit Trail:** Exigir el registro inalterable en la tabla `edits`.

## 4. Reglas de Oro (Restricciones)
- **PROHIBIDO simplificar:** No se deben omitir pasos del flujo ni resumir reglas de negocio para "hacer el prompt más corto".
- **PROHIBIDO omitir errores:** Todo prompt debe incluir el manejo de flujos alternativos y casos de falla.
- **SIN AMBIGÜEDAD:** Evitar palabras como "posiblemente", "si es necesario" o "aproximadamente". Usar lenguaje imperativo y cuantitativo.

## 5. Salida Esperada (Formato Markdown)

El output debe dividirse estrictamente en dos secciones:

### 🟦 SYSTEM PROMPT
*(Este es el contenido que el usuario copiará en el agente de codificación)*
- **Rol:** Definición experta del agente.
- **Contexto:** Descripción del UC y su impacto en el sistema.
- **Flujo paso a paso:** Instrucciones secuenciales de implementación.
- **Reglas y Restricciones:** Listado de RNs, ADRs y prohibiciones.
- **Output Esperado:** Formato exacto del código o respuesta.

### 🟨 METADATA (JSON)
```json
{
  "uc_id": "FSD-UC-NNN",
  "source": "FSD_vX.md",
  "constraints_applied": ["RN-03", "ADR-0001"],
  "risk_level": "high|medium|low"
}
```

## 6. Verificación y Calidad
- **Autonomía:** ¿El prompt es ejecutable por otra IA sin que el usuario tenga que dar más contexto?
- **Trazabilidad:** ¿Cada instrucción del prompt puede rastrearse hasta un punto del FSD?
- **Seguridad:** ¿Se ha incluido la prohibición de transmitir PII (RN-03) en caso de ser necesario?

## 7. Registro de cambios del Skill
| Versión | Fecha | Autor | Cambio |
| :--- | :--- | :--- | :--- |
| 0.1.0 | 27/05/2026 | Claude Code | Versión inicial |
| 1.0.0 | 27/05/2026 | Claude Code | Actualización a arquitectura de "Arquitecto de Prompts" con metadata y flujo de transformación |
