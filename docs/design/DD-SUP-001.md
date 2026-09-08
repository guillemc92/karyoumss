# DD-SUP-001 — Auditoría del 5% del Supervisor (S1)

| Campo | Valor |
|---|---|
| **ID** | DD-SUP-001 |
| **ADR origen** | [ADR-0023](../adr/0023-supervisor-auditoria-firma-iscn.md) §D2/§D5/§D6 (S1) + [ADR-0022](../adr/0022-audit-trail-clinico-django.md) |
| **FSD** | FSD-UC-005 (auditoría aleatoria del 5%) |
| **Reglas** | RN-08 (5% verdes), RN-06 (segregación), RN-05 (audit append-only) |
| **Estado** | En implementación |
| **Fecha** | 2026-07-24 |

## 1. Alcance de S1
Primera fase del flujo del Supervisor: sobre un caso `ANALYST_VALIDATED`, el
Supervisor revisa una **muestra aleatoria determinista del 5%** de los
cromosomas de alta confianza (control de calidad, RN-08) y decide
Confirmar/Rechazar cada uno. **Sin MFA ni ISCN** (S2/S3).

## 2. Backend

### 2.1 Modelo `AuditReview`
Un registro por cromosoma seleccionado para auditoría:
`sample` (FK), `chromosome` (FK), `decision` (`PENDING`/`CONFIRMED`/`REJECTED`,
default PENDING), `comment` (blank), `reviewer` (FK user null hasta decidir),
`decided_at` (null). `unique_together (sample, chromosome)`.

### 2.2 Selección determinista (RN-08, ADR-0023 D2)
`select_audit_sample(sample)`: pool = cromosomas **activos** con
`confidence_score > 0.86`; `rng = random.Random(str(sample.id))`; se eligen
`max(1, ceil(0.05 * len(pool)))` (si pool vacío, ninguno). Crea los `AuditReview`
PENDING si no existen (idempotente). **Reproducible**: mismo caso → mismos
cromosomas (criterio FSD-UC-005). La selección NO se persiste como flag en
`Chromosome`.

### 2.3 Decisión
`decide_audit(review, reviewer, decision, comment)`: setea decision/reviewer/
`decided_at`, emite `AUDIT_DECISION` (ADR-0022) con payload
`{chromosome, decision, comment}`. Solo sobre casos `ANALYST_VALIDATED`.

### 2.4 Estados nuevos
Se declaran `SIGNED` y `REPORTED` en `SampleStatus` (transiciones en S2/S3;
declarados ahora para no re-migrar — patrón ADR-0021 D3).

### 2.5 Endpoints (permiso `case.audit`, scope owner/staff)
| Método | URL | Acción |
|---|---|---|
| GET | `/samples/{id}/audit-review/` | lista el 5% (lo crea al primer acceso) + resumen `{total, pending, confirmed, rejected}` |
| POST | `/samples/{id}/audit-review/{cid}/decide/` (body `{decision, comment}`) | Confirmar/Rechazar → `AUDIT_DECISION` |

Errores: `409 NOT_AUDITABLE` (caso no ANALYST_VALIDATED), `400 INVALID_DECISION`,
`404`, `403 NOT_OWNER`.

### 2.6 RBAC (ADR-0019)
Nueva opción `case.audit` (Objeto "Auditoría") — migración de datos:
Supervisor **True**, Admin **True**, Analista **False** (segregación RN-06).

## 3. Frontend
- `karyotypeClient`: `getAuditReview(id)`, `decideAudit(id, cid, decision, comment)`.
- Panel de auditoría del Supervisor en la página de cariotipo cuando el caso
  está `ANALYST_VALIDATED` y el usuario tiene rol supervisor: lista de
  cromosomas auditados con badge púrpura, botones Confirmar/Rechazar + comentario,
  contador `pending`. Los cromosomas auditados se resaltan en el canvas (badge).
- MSW: handlers de los 2 endpoints con selección determinista espejo.

## 4. Tests (RN-09 ≥90%)
**Backend** (`test_supervisor_s1.py`): selección 5% determinista y reproducible,
mínimo 1, pool >0.86, idempotencia; decide emite AUDIT_DECISION; gate
NOT_AUDITABLE; permisos (analista sin `case.audit` → 403). **Frontend**:
selección puro + panel de auditoría + decisiones + MSW.
