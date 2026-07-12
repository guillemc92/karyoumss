---
id: ADR-0007
title: Plan de Extracción de AI Inference a Servicio Satélite (Fase 2 de ADR-0004)
date: 2026-06-23
status: accepted
supersedes: 2026-06-10 version (extracción inmediata — contradictoria con ADR-0004)
related: [ADR-0004, ADR-0002]
---

# ADR 0007: Plan de Extracción de AI Inference a Servicio Satélite (Fase 2 de ADR-0004)

> ⚠️ **Nota de revisión (2026-06-23):** Este documento reemplaza la versión inicial del 2026-06-10 que proponía la separación inmediata del servicio de inferencia. Esa versión **contradecía ADR-0004** (estrategia arquitectónica aprobada el 2026-05-29), por lo que se reescribe como **plan explícito de Fase 2** sin adelantar la decisión de extracción. Cuando se cumplan los triggers documentados, se creará **ADR-0012** con la decisión operativa y el plan de migración (Strangler Fig).

## Contexto

El pipeline de IA (U-Net + EfficientNet-B3) es **GPU-bound** y consume recursos significativos. ADR-0004 §Decisión establece:

> *"Fase 1 (Actual - Q3 2026): Monolito Modular bien definido (Hexagonal + Clean Architecture)."*
> *"Fase 2 (Q1-Q2 2027): Extraer AI Inference como servicio satélite (independiente por consumo intensivo de GPU)."*
> *"No se recomienda microservicios completos en esta etapa."*

Esta ADR documenta **cómo se ejecutará** la Fase 2 cuando llegue el momento, sin implementarla prematuramente en Fase 1.

## Decisión

**Hoy (Fase 1, Q3 2026):** Mantener AI Inference **dentro del monolito FastAPI** como bounded context `ai_engine/` con adaptadores hexagonales, ejecutado por **Celery workers** que comparten el mismo Docker image pero consumen GPU dedicada.

**Cuando se active Fase 2 (Q1-Q2 2027):** Extraer `ai_engine/` como **servicio satélite independiente** usando:
- **Serving:** TorchServe 0.12+ (primera opción) o NVIDIA Triton (si se requiere batching multi-modelo)
- **Transporte:** gRPC interno (latencia <50ms) sobre HTTP/2, contrato IDL versionado
- **Cola:** El mismo Redis 7 del monolito como broker de tareas
- **Aislamiento:** Red privada, mTLS servicio-a-servicio, RBAC dedicado

**Trigger documentado para activar la extracción:**
1. Throughput del laboratorio >500 muestras/mes por nodo sostenido durante 2 meses.
2. Saturación de GPU >70% en horario pico.
3. Al menos 2 laboratorios en producción simultáneos (justifica costo operativo del split).
4. Equipo con capacidad DevOps para operar el satélite (observabilidad, deploys, oncall).

Mientras ninguno de estos triggers se cumpla, **se mantiene Fase 1** (monolito modular).

## Trade-offs

**A favor de esperar (Fase 1):**
- Velocidad de desarrollo alta en el monolito.
- Audit trail y consistencia transaccional centralizados (críticos para 21 CFR Part 11).
- Sin latencia de red entre FastAPI ↔ AI engine.
- Menor carga operativa DevOps (un solo deploy).

**A favor de extraer (cuando se active Fase 2):**
- Escalado independiente de GPU sin tocar el core clínico.
- Aislar fallos de IA: el core clínico sigue sirviendo modo degradado sin AI engine.
- Permite colocar el satélite en nodos GPU-enabled separados geográficamente.

**Costo del split:**
- Latencia de red añadida (~5-15ms hop gRPC).
- Doble pipeline de CI/CD.
- Necesidad de versionado de contrato API entre monolito y satélite.
- Observabilidad distribuida obligatoria (OpenTelemetry, tracing correlacionado).

## Consecuencias

- **Fase 1 (actual):** El bounded context `ai_engine/` se diseña **desde el día 1** con puertos hexagonales (`InferencePort`, `ModelLoaderPort`) para que la extracción sea **mecánica** y no un rewrite.
- **Fase 2 (futuro):** Se requerirá una **nueva ADR (ADR-0012)** que firme el split cuando se activen los triggers, apruebe presupuesto operativo, y documente el plan de migración (Strangler Fig Pattern: enrutamiento gradual por porcentaje de tráfico).
- AGENTS.md §3 stack mantiene `serving: TorchServe 0.12+ / NVIDIA Triton` como capacidad disponible, no como topología desplegada.

## Referencias

- ADR-0004 §Decisión (Estrategia de Evolución Arquitectónica)
- ADR-0002 §Decision punto 4 (Async Pipeline)
- FSD §2.4 Plan técnico (Hexagonal + Clean Architecture)
- FSD §8 Integraciones externas (GPU Cluster: HTTPS + API Key + JWT)
- BRD §22 SLA Modo Degradado (justifica que AI engine debe poder caerse sin tumbar el core)