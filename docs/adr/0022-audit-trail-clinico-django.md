---
id: ADR-0022
title: Audit Trail append-only del cariotipo en backend-clinic (Django) — materialización de ADR-0008
date: 2026-07-23
status: accepted
refines: [ADR-0008]
depends-on: [ADR-0015, ADR-0021]
related: [RN-04, RN-05, FSD-UC-003, FSD-UC-004, FSD-UC-005, FSD-UC-006]
---

# ADR-0022: Audit Trail append-only del cariotipo en backend-clinic (Django)

## Contexto

La corrección de cariotipo (ADR-0021) entra en su **fase P2** (XAI + resolver
naranjas + gating de bloqueo). Cada acción del analista sobre un cromosoma
(`XAI_VIEWED`, aceptar, reclasificar, marcar anomalía, corregir clase) y del
supervisor (auditoría 5%, override ISCN, firma) debe quedar registrada en un
**audit trail inmutable append-only** (RN-05, 21 CFR Part 11 §11.10(e)). El
prototipo ya lo anticipa con su `addHistoryLog`, y MetaClass lo hacía con sus
comentarios/observaciones.

**El gap arquitectónico:** ADR-0008 diseñó el audit trail (hash chain lineal
SHA256 + extensión Merkle opcional), pero **para la arquitectura FastAPI
previa**. ADR-0015 movió el bounded context clínico de FastAPI a **Django
(`backend-clinic`)**. Hoy el audit trail **no existe** en Django: el propio
`apps/samples/models.py` declara *"RN-05: edits NO vive acá — es tabla
append-only del FastAPI clínico"* — comentario **desactualizado** desde
ADR-0015. No hay ningún modelo de auditoría en `backend-clinic`.

Sin materializar el audit trail en Django, **P2 no puede cumplir RN-05** (ni
FSD-UC-003, que exige registrar `XAI_VIEWED` antes de resolver un naranja).

## Decisión

### D1 — Modelo `AuditEvent` append-only en `backend-clinic/apps/samples`

Se materializa el **Nivel 1 (hash chain lineal SHA256)** de ADR-0008 como un
modelo Django, fuente primaria y obligatoria del audit:

```python
class AuditEventType(models.TextChoices):
    XAI_VIEWED         = 'XAI_VIEWED'          # FSD-UC-003: vio la explicabilidad
    ACCEPT_CHROMOSOME  = 'ACCEPT_CHROMOSOME'   # analista acepta (verde/verificado)
    RECLASSIFY         = 'RECLASSIFY'          # solicita nueva predicción IA
    CORRECT_CLASS      = 'CORRECT_CLASS'       # CORREGIR_CLASE (drag&drop, P3)
    MARK_ANOMALY       = 'MARK_ANOMALY'        # marca anomalía estructural (M)
    SPLIT              = 'SPLIT'               # separar cromosomas pegados (P3)
    JOIN               = 'JOIN'                # unir fragmentos (P3)
    RESOLVE_CROSS      = 'RESOLVE_CROSS'       # resolver cruce (P3)
    ANALYST_VALIDATED  = 'ANALYST_VALIDATED'   # FSD-UC-004: todos resueltos
    AUDIT_DECISION     = 'AUDIT_DECISION'      # supervisor 5% (FSD-UC-005)
    ISCN_OVERRIDE      = 'ISCN_OVERRIDE'       # FSD-UC-006 (futuro)
    SIGN_REPORT        = 'SIGN_REPORT'         # firma MFA (futuro)

class AuditEvent(models.Model):
    id            = UUIDField(pk)
    sample        = ForeignKey(Sample, related_name='audit_events')  # cadena por-caso
    chromosome    = ForeignKey(Chromosome, null=True)   # null para eventos de caso
    event_type    = CharField(choices=AuditEventType)
    actor         = ForeignKey(AUTH_USER_MODEL)         # quién
    payload       = JSONField(default=dict)             # {original_class, new_class, confidence_pre_xai, ...}
    created_at    = DateTimeField(auto_now_add=True)
    previous_hash = CharField(max_length=64, blank=True)   # hash del evento anterior de la MISMA sample
    current_hash  = CharField(max_length=64)               # SHA256(canonical(row) || previous_hash)

    class Meta:
        db_table = 'clinic_audit_events'
        ordering = ['created_at']
```

- **Cadena por-`Sample`** (por-caso), consistente con ADR-0008 §Nivel 1. El
  `previous_hash` es el `current_hash` del último `AuditEvent` de esa misma
  sample; el primero encadena contra `''`.
- `current_hash = SHA256(canonical_json(event_sin_hashes) || previous_hash)`
  con serialización canónica determinística (claves ordenadas, UTC ISO-8601).

### D2 — Enforcement append-only (RN-04/RN-05)

Inmutabilidad garantizada en 3 capas, mismo patrón que ya usa el proyecto
para `iscn_nomenclature`/`edits` (RN-04):

1. **ORM:** `AuditEvent.save()` levanta `ValueError` si el objeto ya tiene pk
   (bloquea UPDATE); no se expone `delete()` en el flujo. El `current_hash`
   se calcula en el `save()` de creación y nunca se recomputa.
2. **API:** ningún endpoint `PATCH`/`DELETE` sobre audit. Solo lectura
   (`GET /samples/{id}/audit/`) y escritura implícita vía los servicios de
   corrección (el cliente NO postea audit directamente: lo emite el servicio
   de dominio al ejecutar la acción, atómicamente en la misma transacción).
3. **Integridad:** cualquier modificación fuera de flujo rompe la cadena
   (el `current_hash` recomputado no coincide) — detectable por un endpoint
   de verificación `GET /samples/{id}/audit/verify/` (recorrido O(n)).

### D3 — Merkle (Nivel 2) DIFERIDO

La extensión Merkle de ADR-0008 (pruebas de inclusión O(log n) para
auditorías forenses de 10 años) **no se implementa en P2**. La cadena lineal
es suficiente para el volumen del MVP y para RN-05. Merkle queda como
extensión futura documentada (requiere un scheduler de cierre de período),
sin cambiar el contrato de `AuditEvent`.

### D4 — Gate de XAI obligatorio (FSD-UC-003, RN)

El servicio que resuelve/acepta un cromosoma naranja **exige** que exista un
`AuditEvent(XAI_VIEWED)` previo para ese `chromosome` (y setea
`Chromosome.xai_viewed=True`). Sin él, rechaza con error de negocio
("Debe consultar la explicabilidad (XAI) antes de resolver"). Este es el
enforcement de BR-004 a nivel de servicio, no solo de UI.

### D5 — Decisión relacionada: cardinalidad de metafases (1 primario)

MetaClass contaba **N metafases** por muestra (`SCAContador`). Para el MVP,
**1 `Karyotype` primario por `Sample`** (la IA elige la mejor metafase) — ya
es la cardinalidad de ADR-0021 (`OneToOne`). El conteo de N células es una
extensión futura (no requerida por el flujo de validación FSD-UC-002/003/004).
Se documenta aquí para cerrar la duda abierta del análisis de dominio; no
cambia el modelo de P1.

## Trade-offs

- **Pros:** RN-05 cumplible en Django desde P2; audit atómico con la acción
  (misma transacción, no puede desincronizarse); verificación de integridad
  O(n); reutiliza el patrón append-only ya conocido del proyecto.
- **Cons:** el hash chain acopla el orden de escritura (dos acciones
  concurrentes sobre la misma sample deben serializarse — se resuelve con
  `select_for_update` sobre el último evento del caso, costo acotado);
  Merkle diferido significa que auditorías forenses masivas serán O(n) hasta
  que se implemente el Nivel 2 (aceptable en el MVP).

## Consecuencias

- Migración nueva en `apps/samples` (tabla `clinic_audit_events`).
- Se **actualiza el comentario desactualizado** de `models.py` ("edits NO
  vive acá — FastAPI") al implementar P2: el audit trail ahora SÍ vive en
  Django backend-clinic.
- P2 emite audit desde los servicios de dominio (resolver/aceptar/reclasificar
  /marcar), no desde las vistas ni el cliente.
- FSD §6.1 (modelo AUDIT_TRAIL) y AGENTS.md §7 (`EditTrail`) siguen siendo el
  contrato conceptual; este ADR es su materialización concreta en Django
  (refina ADR-0008, no lo deroga).
- El endpoint de verificación de integridad y la extensión Merkle quedan como
  trabajo futuro documentado.
