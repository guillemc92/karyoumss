---
id: ADR-0021
title: Visor y Corrección de Cariotipo — modelo de datos y arquitectura del editor clínico
date: 2026-07-23
status: accepted
supersedes: []
refines: [ADR-0006, ADR-0008, ADR-0015, ADR-0016]
---

# ADR-0021: Visor y Corrección de Cariotipo

## Contexto

La corrección de cariotipo es el núcleo clínico del producto (FSD-UC-002
semaforización, FSD-UC-003 XAI + corrección manual, FSD-UC-004
bloqueo/validación). El mockup `correccion de cariotipo.html` (1206 líneas
vanilla JS) define la UI: visor de 3 columnas (thumbnails → grid de
cromosomas 1–22/X/Y → panel de propiedades), semaforización verde/naranja,
modal XAI Grad-CAM, drag & drop de reclasificación y herramientas de imagen.

**Estado previo (gap):** el bounded context clínico (`backend-clinic`,
`frontend-clinic`, ADR-0015/0016) tiene el modelo `Sample` con estados
básicos, pero **no existe ningún modelo de cromosomas ni de cariotipo**, ni
visor. `Konva.js` (stack canónico de CLAUDE.md) no está instalado.

## Decisión

### D1 — Modelo de datos: `Karyotype` (1:1 con `Sample`) + `Chromosome` (N)

Se crea en `backend-clinic/apps/samples`:

- **`Karyotype`** — resultado del pipeline IA para una `Sample` (OneToOne).
  Guarda `model_version`, `generated_at`, `image_path` (metafase fuente).
  El conteo esperado es 46 cromosomas (23 pares) pero el modelo no lo
  fuerza: aneuploidías reales (+21, monosomías) tienen ≠46.
- **`Chromosome`** — cada cromosoma segmentado y clasificado. Campos:
  `predicted_class` (slot destino `1`..`22`/`X`/`Y`), `confidence_score`
  (Decimal 0–1), `bbox` (JSON x/y/w/h del crop en la metafase, para el
  render futuro con Konva), `measures` (JSON longitud/índice
  centromérico/bandas/calidad, panel derecho del mockup), `resolution_status`
  (`AUTO`/`PENDING`/`RESOLVED`), `xai_viewed` (bool, gate de FSD-UC-003).

**Por qué modelos nuevos y no JSON en `Sample.metadata`:** cada cromosoma
es una entidad consultable, auditable y (desde P2) mutable individualmente;
las reglas RN-01/RN-02 operan por-cromosoma (contar naranjas sin resolver).
Un blob JSON haría inviable la auditoría append-only por cromosoma (RN-05).

### D2 — Semaforización DERIVADA, no persistida (RN-02, ADR-0006)

El color NO se guarda como campo: se deriva de `confidence_score` en tiempo
de lectura (`green` si ≥ 0.85, `orange` si < 0.85, `red` si la clasificación
falló/`confidence` es null). Umbral único `CONFIDENCE_THRESHOLD = 0.85`,
consistente con ADR-0006 y con `ModelConfig.confidence_threshold` del panel
admin (ADR-0014 P3). Persistir el color duplicaría la fuente de verdad y
abriría deriva si el umbral cambia.

### D3 — Estados clínicos del `Sample` extendidos (FSD-UC-004)

Se agregan al enum `SampleStatus` los estados que el FSD exige para el flujo
de validación: `BLOCKED_BY_CONFIDENCE` (hay naranjas sin resolver) y
`ANALYST_VALIDATED` (todos resueltos, listo para Supervisor). En **P1 no se
implementan las transiciones** — solo se declaran los valores del enum para
que P2 los use sin una segunda migración disruptiva.

### D4 — Render: SVG/CSS grid en P1, Konva.js cuando llegue el drag & drop

El visor read-only (P1) se construye con un **grid SVG/CSS**, no con canvas:
es read-only, mucho más simple, testeable en jsdom y sin dependencia nueva.
**Konva.js (`react-konva`) se incorpora en P3**, cuando el arrastre de crops
de cromosomas realmente lo necesita (YAGNI). Esto refina —no deroga— el
"Konva.js" de CLAUDE.md/ADR-0006: el stack canónico se mantiene como destino,
pero se difiere su adopción a la fase que lo justifica.

### D5 — Fases (una PR por fase, tests ≥90% RN-09, E2E por fase)

| Fase | Alcance | Estado |
|---|---|---|
| **P1** | Modelo `Karyotype`/`Chromosome` + `GET /samples/{id}/karyotype/` + visor read-only con semaforización + panel de propiedades | **este ADR** |
| **P2** | XAI Grad-CAM + `XAI_VIEWED` + resolver naranjas + gating de bloqueo (RN-01) + audit append-only (ADR-0008) | pendiente |
| **P3** | Corrección manual drag & drop (reclasificar entre slots, `CORREGIR_CLASE`) + dividir/unir, sobre Konva.js | pendiente |
| **P4** | Herramientas de imagen (zoom/pan/rotar/brillo) + modo manual/degradado (FSD-UC-007) | pendiente |

## Trade-offs

- **Pros:** modelo consultable y auditable por-cromosoma; semaforización sin
  deriva (una sola fuente de verdad); P1 entregable y verificable sin canvas;
  camino incremental de bajo riesgo hacia el editor completo.
- **Cons:** el grid SVG de P1 se reescribe parcialmente al migrar a Konva en
  P3 (costo acotado y consciente); agregar estados al enum ahora sin
  transiciones deja valores "declarados pero inertes" hasta P2 (documentado).

## Consecuencias

- Migración nueva en `apps/samples` (tablas `clinic_karyotypes`,
  `clinic_chromosomes`).
- La exportación de reporte (futuro) se bloquea si hay naranjas sin resolver
  (RN-01/RN-02) — la lógica de bloqueo se implementa en P2, este ADR solo
  deja el modelo y la semaforización derivada que la habilitan.
- El pipeline de inferencia real (ADR-0007) poblará `Chromosome`; en demo/MSW
  se siembran 46 cromosomas mock con confidences mixtas para ejercitar la
  semaforización.
