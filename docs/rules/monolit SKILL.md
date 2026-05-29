---
name: biomed-monolith-decomposition-architect
description: > 
  Arquitecto especializado en evolución de sistemas clínicos de Inteligencia Aumentada. Analiza BIOMED UMSS y propone la estrategia óptima de descomposición (Monolito Modular, Microservicios o Híbrido), respetando estrictamente Human-in-the-Loop, RN-03 (Anonimización CHN), audit trail inmutable y regulaciones clínicas.
allowed-tools:
  - read
  - edit
model-tier: sonnet
fsd-version-min: v1.0
status: stable
owner: Ing. Guillermo Mamani Chambi
---

# Skill: BIOMED Monolith Decomposition Architect

Este skill está diseñado específicamente para el dominio **citogenético** y los principios no negociables de BIOMED UMSS.

## 1. Cuándo activarlo (Triggers)

- Al redactar la sección **§6 Arquitectura Distribuida** del DTI.
- Al preparar ADRs de evolución arquitectónica.
- Antes de la Defensa Final (para justificar la decisión actual).
- Cuando se evalúe escalabilidad o mantenimiento a largo plazo.

## 2. Bounded Contexts Identificados en BIOMED UMSS

| Bounded Context          | Responsabilidad Principal                          | Criticidad | Volumen de Cambio | Recomendación |
|--------------------------|----------------------------------------------------|------------|-------------------|-------------|
| **Sample Ingestion**     | Carga, validación y **CHN Anonymization**         | Alta       | Medio             | Monolito Modular |
| **AI Inference**         | Pipeline completo (Tiling, U-Net, EfficientNet)   | Muy Alta   | Alto              | Extraer como servicio (Fase 2) |
| **Karyotype Editing**    | Edición manual, semaforización y validación HITL   | Muy Alta   | Alto              | Mantener en core |
| **Report & Signing**     | Generación ISCN, firma digital y bloqueo          | Alta       | Medio             | Monolito Modular |
| **Audit & Compliance**   | Audit trail inmutable + logging clínico            | Crítica    | Bajo              | Centralizado |
| **Identity & Access**    | Autenticación, RBAC y segregación de roles        | Alta       | Bajo              | Monolito Modular |

## 3. Procedimiento de Análisis (Obligatorio)

1. **Evaluar Contexto Actual**
   - Tamaño del equipo
   - Madurez del dominio
   - Restricciones clínicas y regulatorias
   - Heat map de cambios (qué partes cambian más)

2. **Aplicar Scale Cube + DDD**
   - Eje X: Escalado horizontal
   - Eje Y: Descomposición por bounded context
   - Eje Z: Sharding por laboratorio / región

3. **Árbol de Decisión Específico BIOMED**

   - ¿El equipo tiene capacidad operativa para múltiples servicios?  
   - ¿Existen requerimientos de baja latencia en edición HITL?  
   - ¿Es aceptable tener consistencia eventual en audit trail?  
   - ¿El pipeline de IA es el principal bottleneck?

4. **Detectar Riesgos Clínicos**
   - No romper flujos donde se requiera transacción ACID (validación + bloqueo).
   - Mantener Audit Trail centralizado o con propagación garantizada.
   - Nunca comprometer RN-03 (CHN antes de cualquier llamada externa).

## 4. Recomendación Actual (Mayo 2026)

**Estrategia Recomendada: Monolito Modular + Satélites**

**Justificación:**
- Equipo aún pequeño.
- Alto riesgo clínico en flujos de validación HITL.
- Necesidad de consistencia fuerte en audit trail.
- El bottleneck principal (IA Inference) puede extraerse primero.

**Hoja de Ruta de Evolución:**

| Fase | Estrategia | Servicios | Justificación |
|------|----------|---------|-------------|
| Fase 1 (Actual) | Monolito Modular | 1 aplicación | Velocidad de desarrollo y consistencia |
| Fase 2 (2027) | Satélite | AI Inference Service | Alto consumo GPU y escalado independiente |
| Fase 3 (2028) | Microservicios selectivos | Report + Audit | Cuando haya múltiples laboratorios |

## 5. Salida Esperada del Skill

El skill debe entregar:

1. **Tabla de Bounded Contexts** (como la de arriba).
2. **Recomendación clara** con justificación.
3. **Esqueleto de ADR** listo para usar.
4. **Riesgos y mitigaciones** específicas del dominio clínico.

## 6. Reglas de Oro BIOMED

- **Nunca** proponer microservicios si compromete el Human-in-the-Loop.
- **Siempre** mantener la anonimización CHN en el borde.
- **Siempre** priorizar audit trail inmutable.
- Preferir **evolución incremental** sobre "big bang" de microservicios.

