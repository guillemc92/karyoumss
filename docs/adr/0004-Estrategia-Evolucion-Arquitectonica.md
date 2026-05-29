---
id: ADR-0004
title: Estrategia de Evolución Arquitectónica (Monolito Modular + Satélites)
date: 2026-05-29
status: proposed
---

# ADR 0004: Estrategia de Evolución Arquitectónica (Monolito Modular + Satélites)

**Status:** Proposed  
**Date:** 29 de Mayo de 2026  
**Responsable:** Ing. Guillermo Mamani Chambi  
**Stakeholders:** Equipo de Desarrollo, Responsable Clínico (IIBISMED), Arquitecto  

## Contexto

BIOMED UMSS es actualmente un **monolito** bien estructurado con arquitectura hexagonal. Hemos identificado bounded contexts claros, pero el equipo es pequeño (~3-4 personas) y el dominio clínico impone restricciones fuertes:

- Human-in-the-Loop debe ser garantizado en todo momento.
- RN-03 (Anonimización CHN) debe ejecutarse en el borde.
- El Audit Trail debe ser inmutable y centralizado.
- La validación HITL requiere consistencia fuerte.
- El pipeline de IA es el principal bottleneck de recursos (GPU).

Se necesita definir la estrategia de evolución a mediano plazo sin comprometer la seguridad clínica ni la velocidad de desarrollo actual.

## Decisión

**Adoptar la estrategia "Monolito Modular + Satélites" como dirección arquitectónica principal.**

### Detalle de la Estrategia

- **Fase 1 (Actual - Q3 2026):** Monolito Modular bien definido (Hexagonal + Clean Architecture).
- **Fase 2 (Q1-Q2 2027):** Extraer **AI Inference** como servicio satélite (independiente por consumo intensivo de GPU).
- **Fase 3 (2028+):** Evaluar extracción selectiva de Report Generation y Audit Service solo si hay múltiples laboratorios.

**No se recomienda microservicios completos en esta etapa.**

## Alternativas Consideradas

| Opción | Descripción | Pros | Contras | Decisión |
|--------|-------------|------|---------|----------|
| **A. Microservicios Completos** | Descomponer todos los bounded contexts | Escalado independiente, equipos autónomos | Alta complejidad operativa, latencia agregada, alto riesgo clínico por consistencia eventual | Rechazada |
| **B. Monolito Clásico** | Mantener todo en un solo deploy | Simplicidad máxima | Escalado uniforme, bottleneck de IA afecta todo el sistema | Rechazada |
| **C. Monolito Modular + Satélites** (Elegida) | Monolito principal + servicios independientes para partes pesadas | Balance óptimo: simplicidad + escalabilidad selectiva | Requiere buena gobernanza de interfaces | **Aceptada** |
| **D. Serverless Total** | Todo en funciones Lambda/Fargate | Costo por uso | Cold starts, debugging difícil, vendor lock-in | Rechazada |

## Consecuencias

**Positivas:**
- Mantiene velocidad de desarrollo alta en la fase actual.
- Permite escalar independientemente el componente más demandante (IA Inference).
- Reduce riesgo clínico al mantener flujos críticos (HITL, firma) dentro del monolito.
- Facilita la trazabilidad y el audit trail centralizado.
- Evolución incremental y de bajo riesgo.

**Negativas:**
- El monolito seguirá creciendo hasta la Fase 2.
- Se requiere disciplina para mantener fronteras claras entre módulos.
- La extracción del servicio de IA requerirá inversión en observabilidad y contratos API sólidos.

## Referencias

- BRD v3.5 §5 (Métricas de Éxito) y §8 (Riesgos)
- PRD v2 - Constitution (Human-in-the-Loop)
- AGENTS.md (Reglas RN-01 a RN-08)
- DTI §4 (Bounded Contexts)
- POC-01 (Pipeline Asíncrono)
- POC-03 (Anonimización CHN)

**Estado final:** Proposed → Aceptado el [29/05/2026] por el arquitecto y responsable clínico.