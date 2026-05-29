---
name: skill-read-context
description: > 
  Extrae y estructura información técnica desde PRD, FSD, BRD y AGENTS.md para proporcionar un contexto preciso y trazable a los agentes de implementación, eliminando suposiciones y detectando inconsistencias documentales.
allowed-tools:
  - read
model-tier: sonnet
fsd-version-min: v1.0
status: stable
owner: Ing. Guillermo Mamani Chambi
---

# Skill: Intérprete de Contexto Funcional BIOMED

Este Skill actúa como un agente de análisis de documentación técnica especializado en sistemas biomédicos regulados. Su propósito es convertir la documentación narrativa en una estructura de datos JSON estricta que sirva de base para la generación de especificaciones y planes de tarea.

## 1. Cuándo activarlo (triggers)
- **DURANTE:** El inicio de una nueva tarea de desarrollo, refactorización de lógica de negocio o diseño de contratos de prompt.
- **ARRANCA cuando:** El usuario menciona un ID de caso de uso (ej. `FSD-UC-001`), solicita analizar la coherencia entre documentos o invoca explícitamente `@skill-read-context`.
- **NO ACTIVAR cuando:** Se estén realizando tareas puras de infraestructura o estilos visuales que no afecten el flujo de datos clínicos.

## 2. Entradas obligatorias (Inputs)
El usuario MUST proporcionar al menos una de:
- **ID del UC:** Referencia a `FSD-UC-NNN`.
- **Ruta al FSD:** `docs/FSD_v1.md` o similar.
- **Documentos fuente:** Acceso a los archivos `PRD`, `FSD`, `BRD` y `AGENTS.md`.

## 3. Proceso Obligatorio (Análisis)
El agente debe seguir estrictamente estos pasos:
1. **Identificación:** Extraer Actores del sistema, Casos de Uso (UC), Reglas de Negocio (RN), Entidades del dominio y Flujos críticos.
2. **Detección de Inconsistencias:** Comparar la información entre los diferentes documentos (ej. si el BRD pide X pero el FSD describe Y).
3. **Cero Inferencia:** No inventar requerimientos ni completar vacíos con supuestos. Si la información no está explícita $\to$ marcar como `"UNKNOWN"`.

## 4. Reglas de Operación
- **Prohibición de Alucinación:** Está estrictamente prohibido inventar requerimientos o funcionalidades.
- **Trazabilidad Total:** Todo elemento extraído debe ser justificable mediante una cita o referencia al documento fuente.
- **Rigidez de Datos:** Si no se puede justificar la procedencia de un dato, debe ser eliminado del output.

## 5. Salida Esperada (JSON ESTRICTO)
El resultado debe ser exclusivamente un objeto JSON con la siguiente estructura:

```json
{
  "actors": [
    { "id": "string", "role": "string", "description": "string" }
  ],
  "use_cases": [
    { "id": "FSD-UC-NNN", "name": "string", "flow": ["step 1", "step 2"], "expected_result": "string" }
  ],
  "business_rules": [
    { "id": "RN-NNN", "description": "string", "source": "document_id" }
  ],
  "entities": [
    { "name": "string", "attributes": ["attr1", "attr2"], "type": "Aggregate|Entity|ValueObject" }
  ],
  "critical_flows": [
    { "name": "string", "steps": ["step 1", "step 2"], "critical_point": "string" }
  ],
  "inconsistencies": [
    { "document_a": "string", "document_b": "string", "conflict": "string" }
  ],
  "unknowns": [
    { "item": "string", "context": "string", "impact": "high|medium|low" }
  ]
}
```

## 6. Verificación (Criterios de Calidad)
- **Justificación:** ¿Cada campo del JSON tiene un origen claro en los documentos?
- **Sinceridad:** ¿Se han marcado como `"UNKNOWN"` los vacíos en lugar de suponer soluciones?
- **Precisión:** ¿El JSON es válido y sigue la estructura definida?

## 7. Anti-patrones específicos
- **Resumen Narrativo:** Responder con párrafos explicativos en lugar del JSON estructurado.
- **Suponer Flujos:** "Probablemente el usuario haga clic aquí..." $\to$ Incorrecto. Solo reportar lo que dice el FSD.
- **Mezclar Capas:** Incluir decisiones técnicas de implementación (como el nombre de una variable) cuando el Skill debe extraer requerimientos funcionales.

## 8. Registro de cambios del Skill
| Versión | Fecha | Autor | Cambio |
| :--- | :--- | :--- | :--- |
| 0.1.0 | 22/05/2026 | Ing. Guillermo Mamani | Versión inicial |
| 1.0.0 | 27/05/2026 | Claude Code | Actualización a formato de Análisis Estructurado (JSON Estricto) |
