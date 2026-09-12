---
id: ADR-0025
title: El motor ISCN vive en el Django clínico (deroga parcialmente ADR-0015)
date: 2026-07-28
status: accepted
supersedes: ADR-0015 §Consecuencias "el Django clínico NO los escribe, solo delega al FastAPI" (parcialmente, solo para `iscn_nomenclature`)
refines: [ADR-0022, ADR-0023]
---

# ADR-0025: El motor ISCN vive en el Django clínico

## Contexto

La fase **S3 de ADR-0023** (motor ISCN + override validado + estado `REPORTED`)
es lo único que falta para cerrar la cadena clínica: hoy el caso llega a `SIGNED`
y ahí se detiene. Al ir a implementarla aparece una **contradicción entre dos ADRs
firmados**:

- **ADR-0023 D4** decide que `Sample.iscn_nomenclature` es un campo del modelo
  Django, read-only tras generarse, y que el caso pasa a `REPORTED`.
- **ADR-0015 §Consecuencias** dice lo opuesto: *«`iscn_nomenclature` y `edits`
  siguen siendo read-only/append-only; el Django clínico **NO los escribe**, solo
  delega al FastAPI»*. El comentario en `apps/samples/models.py` lo repite.

**Hallazgo que desempata (verificado 2026-07-28):** el FastAPI clínico al que
habría que delegar **no existe en el repositorio**. El propio ADR-0015 §Contexto
punto 4 ya lo había constatado para Muestras; hoy sigue siendo cierto para el
ISCN. `backend-ml` es el motor de inferencia (segmentación + clasificación,
ADR-0007) y no tiene noción de muestras, casos ni nomenclatura.

Es decir: seguir ADR-0015 al pie de la letra hace que **S3 sea inimplementable**.

## Decisión

### D1 — `generate_iscn()` y `Sample.iscn_nomenclature` viven en el Django clínico

Se **deroga parcialmente ADR-0015**, solo en lo relativo a `iscn_nomenclature`.
El resto de ADR-0015 sigue vigente sin cambios: el pipeline de inferencia (U-Net +
EfficientNet-B3 + Grad-CAM) permanece fuera de Django, consumido vía
`pipeline_client` con circuit breaker.

**`edits` no se toca por este ADR** — sigue como lo dejó ADR-0015.

### D2 — Razón: no partir el hash chain de auditoría

El motivo determinante no es la comodidad, es **integridad de la traza**.

Generar el ISCN emite `ISCN_OVERRIDE`, que por ADR-0022 debe encadenarse por SHA256
contra el evento anterior **del mismo caso**. Esa cadena ya contiene `XAI_VIEWED`,
`ANALYST_VALIDATED`, `AUDIT_DECISION`, `SIGN_REPORT` y `NARRATIVE_GENERATED`, todos
en la base de Django.

Poner el motor ISCN en otro servicio con su propia base **partiría la cadena en
dos**: el eslabón del ISCN no podría encadenarse contra la firma que lo precede, y
la verificación de integridad append-only (RN-05) dejaría de ser comprobable
extremo a extremo sobre un caso. Ese es exactamente el fallo que ADR-0022 existe
para evitar.

El flujo completo del Supervisor (auditoría 5% → firma MFA → ISCN) ya vive en
Django; el ISCN es su último eslabón, no una pieza aparte.

### D3 — RN-04 se sigue cumpliendo, solo cambia quién lo hace cumplir

RN-04 exige que `iscn_nomenclature` sea read-only tras generarse. Se mantiene:

- **No hay endpoint PATCH** sobre el campo (prohibición explícita de CLAUDE.md).
- El campo se escribe **una sola vez** en la generación; un segundo intento sin
  justificación es rechazado (409 `ISCN_ALREADY_GENERATED`).
- El **override** no es una edición libre: es un endpoint de generación con
  validación de gramática ISCN + justificación obligatoria, que emite
  `ISCN_OVERRIDE` con `original_iscn` / `final_iscn` / `justification`.
- El modelo bloquea la mutación silenciosa: `save()` rechaza cambiar un
  `iscn_nomenclature` ya poblado si no viene del servicio de override.

### D4 — El motor es una función pura, testeable sin base de datos

`generate_iscn(counts: dict[str, int]) -> str` recibe el conteo por clase y
devuelve el string. Sin ORM, sin I/O, sin estado. Determinística por
construcción: mismo input, mismo output.

Esto es lo que hace **auditable** el dato clínico, y es la razón por la que
ADR-0024 D1 prohíbe que lo produzca el LLM: `47,XY,+21` es un diagnóstico de
síndrome de Down; un modelo generativo puede alucinar una trisomía, una función
pura no.

Gramática soportada (ISCN 2024, subconjunto):
`<total>,<sexo>[,<anomalías numéricas ascendentes>]` — p. ej. `46,XX`, `47,XY,+21`,
`45,X` (Turner), `48,XXY,+21`. Las anomalías estructurales quedan **fuera de
alcance** de este ADR (requieren bandeo y marcado por cromosoma, no solo conteo);
el override manual las cubre mientras tanto.

### D5 — Gate de estado y RBAC

- Solo se genera desde `SIGNED` (409 `NOT_REPORTABLE` en cualquier otro estado):
  el ISCN es lo que se reporta **después** de la firma del Supervisor.
- Éxito → estado `REPORTED`, terminal del flujo clínico.
- Permiso `case.override_iscn` (ADR-0023 D5) para el override; la generación
  normal usa `case.sign`, ya sembrado.

## Trade-offs

- **Pros:** desbloquea S3; la cadena de auditoría queda íntegra y verificable
  extremo a extremo; función pura testeable; sin una nueva superficie de fallo
  inter-servicio; RN-04 y RN-05 intactas.
- **Cons:** aumenta la responsabilidad del Django clínico, que ADR-0013/0015
  querían acotada. Se acepta porque la alternativa —un servicio nuevo para una
  función pura de ~100 líneas— cuesta más de lo que protege, y **rompería** la
  garantía de ADR-0022. Las anomalías estructurales quedan diferidas.

## Consecuencias

- Migración en `apps/samples`: `Sample.iscn_nomenclature`, `iscn_generated_at`,
  `iscn_is_override`; seed de la opción RBAC `case.override_iscn`.
- El comentario de `models.py` («`iscn_nomenclature` NO vive acá») queda obsoleto
  y se corrige apuntando a este ADR.
- Si en el futuro se construye el FastAPI clínico completo, mover el motor allí
  requiere un ADR nuevo **y** una estrategia para no partir el hash chain.
- Habilita el informe final: con `REPORTED` alcanzable, la narrativa de ADR-0024
  ya tiene un ISCN real que narrar.
