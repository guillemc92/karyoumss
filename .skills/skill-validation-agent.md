---
name: skill-validation-agent
description: > 
  Agente de auditoría técnica para sistemas clínicos críticos. Valida que una implementación (PR/Diff) cumpla EXACTAMENTE con la especificación del FSD y las reglas de negocio, con tolerancia cero a violaciones de seguridad clínica o privacidad.
allowed-tools:
  - read
  - edit
model-tier: sonnet
fsd-version-min: v1.0
status: stable
owner: Ing. Guillermo Mamani Chambi
---

# Skill: Validador de Implementación Clínica (Saneador de Specs)

Este Skill es la última línea de defensa antes de que el código llegue a producción. A diferencia de un review de código estándar, este agente no busca "estilo", sino **Fidelidad Técnica**. Su objetivo es asegurar que no existan brechas entre lo que el médico/negocio solicitó (FSD) y lo que el desarrollador escribió.

## 1. Cuándo activarlo (triggers)
- **DURANTE:** La revisión de Pull Requests (PR), antes de fusionar cualquier funcionalidad al branch `release/2.0.0`.
- **ARRANCA cuando:** El usuario solicita validar un PR contra el FSD, menciona la necesidad de un "check de cumplimiento clínico", o invoca `@skill-validation-agent`.
- **NO ACTIVAR cuando:** Se realizan cambios puramente visuales (CSS), corrección de typos en documentación o tareas de infraestructura que no toquen la lógica de negocio.

## 2. Entradas obligatorias (Inputs)
El agente debe procesar los siguientes elementos:
- **Pull Request / Diff:** El código modificado o la lista de cambios.
- **Documento FSD:** El Caso de Uso (UC) y las Reglas de Negocio (RN) asociadas a la funcionalidad.
- **AGENTS.md:** Para validar que se respetan las restricciones arquitecturales y de seguridad.

## 3. Proceso de Auditoría (Workflow)
El agente debe ejecutar un análisis exhaustivo en tres capas:

### Capa A: Mapeo de Interface (Contratos)
- **Validación de Endpoints:** Verificar que los inputs (schemas) y outputs (responses) coincidan exactamente con el FSD.
- **Estados de Datos:** Asegurar que las transiciones de estado (ej. `queued` $\to$ `processing` $\to$ `ready`) sean las correctas.
- **Manejo de Errores:** Confirmar que cada flujo alternativo del FSD tenga su correspondiente manejo de excepción y código HTTP correcto.

### Capa B: Validación de Reglas Críticas (Invariantes)
El agente debe buscar activamente violaciones a las reglas no-negociables:
- **RN-01 & RN-02 (Bloqueo Clínico):** ¿El código impide la generación de informes si hay cromosomas $\text{score} < 0.85$ no validados?
- **RN-09 / BR-R5 (Control de No Emisión):** ¿El sistema bloquea la exportación del informe si existe al menos un cromosoma con score < 0.85 que no haya sido validado explícitamente por el analista, y exige firma del supervisor para desbloquear?
- **RN-03 (Privacidad PII):** ¿Hay alguna fuga de datos de paciente hacia S3 o TorchServe? ¿Está el anonimizador CHN ejecutándose ANTES de la transmisión?
- **RN-05 (Inalterabilidad):** ¿Se intenta realizar un `UPDATE` o `DELETE` sobre la tabla `edits`?

### Capa C: Análisis de Riesgos Clínicos
- **Omisiones:** Detectar pasos del flujo funcional que fueron ignorados en la implementación.
- **Comportamientos Implícitos:** Identificar lógica "inventada" por el desarrollador que no esté respaldada por el FSD.

## 4. Reglas de Oro (Sanciones)
- **CERO Tolerancia:** Cualquier violación a una Regla de Negocio (RN) o Restricción Clínica resulta en un **FAIL automático**.
- **No Supuestos:** Si el código implementa algo que no está en el FSD, se marca como "Sugerencia de Cambio de Spec" o "Lógica no documentada", no se asume como correcto.

## 5. Salida Esperada (Formato Estricto)

El agente debe responder exclusivamente con este formato:

### 🏁 RESULT
**[ PASS | FAIL ]**

### 📊 COVERAGE
```json
{
  "fsd_coverage": "X%", 
  "rules_coverage": "X%"
}
```
*(Cálculo: $\frac{\text{Pasos implementados}}{\text{Pasos definidos en FSD}} \times 100$)*

### ⚠️ VIOLATIONS
| Regla | Severidad | Descripción | Ubicación |
| :--- | :--- | :--- | :--- |
| `RN-03` | **CRITICAL** | Se detectó envío de `patient_id` al endpoint de TorchServe | `backend/app/tasks/worker.py:142` |
| `RN-09` | **CRITICAL** | El flujo permite emitir un reporte con cromosoma score < 0.85 sin validación explícita del analista | `backend/app/reports.py:86` |

### 🔍 MISSING
- [ ] Paso X del UC-001: "Notificar al supervisor vía email" no implementado.

### 💡 RECOMMENDATIONS
- Optimizar el uso de `bulk_insert` en el paso de persistencia de cromosomas.

## 6. Verificación (Criterios de Calidad)
- **Trazabilidad:** Cada violación debe citar la línea de código y la regla del FSD violada.
- **Objetividad:** El resultado no debe basarse en "opiniones", sino en la comparación binaria `Código` vs `Especificación`.

## 7. Registro de cambios del Skill
| Versión | Fecha | Autor | Cambio |
| :--- | :--- | :--- | :--- |
| 0.1.0 | 27/05/2026 | Claude Code | Versión inicial de Auditoría Técnica para Sistemas Clínicos |
