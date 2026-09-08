# DD-KARYO-002 — XAI + Resolución de naranjas + Gating + Audit Trail (P2)

| Campo | Valor |
|---|---|
| **ID** | DD-KARYO-002 |
| **ADR origen** | [ADR-0021](../adr/0021-visor-correccion-cariotipo.md) §D5 (P2) + [ADR-0022](../adr/0022-audit-trail-clinico-django.md) |
| **FSD** | FSD-UC-003 (XAI + corrección), FSD-UC-004 (bloqueo/validación) |
| **Reglas** | RN-01 (bloqueo), RN-02 (semaforización), RN-05 (audit append-only), BR-003/BR-004 |
| **Estado** | En implementación |
| **Fecha** | 2026-07-23 |

## 1. Alcance de P2

Sobre el visor read-only de P1, habilitar el **flujo de resolución de
cromosomas naranja**:
1. **XAI Grad-CAM**: ver la explicabilidad de un cromosoma → registra
   `XAI_VIEWED` (obligatorio antes de resolver, BR-004).
2. **Resolver (Aceptar)** un naranja → `RESOLVED`, exige XAI previo.
3. **Marcar anomalía (M)** estructural.
4. **Gating (RN-01)**: mientras haya ≥1 naranja sin resolver, el caso está
   bloqueado; no se puede "Pasar a Supervisor".
5. **Validar** (todos resueltos) → transición `ANALYST_VALIDATED`.
6. **Audit trail** append-only (ADR-0022) detrás de cada acción.

Fuera de P2: reclasificar/drag&drop, split/join/cross (P3); herramientas de
imagen (P4); firma MFA / ISCN / auditoría 5% del supervisor (fase futura).

## 2. Backend

### 2.1 Modelo `AuditEvent` (ADR-0022 D1/D2)
Ver ADR-0022 §D1. Append-only: `save()` bloquea UPDATE; hash chain SHA256
por-`Sample`. Servicio `emit_event(sample, actor, event_type, chromosome=None,
payload={})` con `select_for_update` sobre el último evento del caso.

### 2.2 Campo nuevo en `Chromosome`
`is_anomaly = BooleanField(default=False)` — marcador estructural (M).

### 2.3 Servicio de estado (FSD-UC-004)
`recompute_karyotype_gating(sample)`: deriva de los cromosomas si el caso está
bloqueado (`unresolved_orange > 0 or red > 0`). El estado explícito
`ANALYST_VALIDATED` se setea solo vía el endpoint de validación (no
automáticamente), emitiendo `ANALYST_VALIDATED`.

### 2.4 Endpoints (todos scope RN-06 owner/staff)

| Método | URL | Acción | Audit |
|---|---|---|---|
| POST | `/samples/{id}/chromosomes/{cid}/xai/` | Grad-CAM (mock heatmap) + set `xai_viewed=True` | `XAI_VIEWED` |
| POST | `/samples/{id}/chromosomes/{cid}/resolve/` | naranja→`RESOLVED`. **Rechaza 409 si `xai_viewed=False`** (BR-004) | `ACCEPT_CHROMOSOME` |
| POST | `/samples/{id}/chromosomes/{cid}/anomaly/` | `is_anomaly=True` | `MARK_ANOMALY` |
| POST | `/samples/{id}/validate/` | **Rechaza 409 si is_blocked** (RN-01), si no → `ANALYST_VALIDATED` | `ANALYST_VALIDATED` |
| GET | `/samples/{id}/audit/` | lista de eventos (read-only) | — |

- **XAI**: en este Django no corre el modelo (eso es el microservicio de
  inferencia, ADR-0007). El endpoint devuelve un heatmap **mock** (base64
  placeholder) + registra el evento y setea `xai_viewed`. La generación real
  del mapa es del ML service (fuera de alcance).
- Los eventos se emiten en la **misma transacción atómica** que la acción.

### 2.5 Errores
- `409 XAI_REQUIRED` al resolver sin XAI.
- `409 CASE_BLOCKED` al validar con naranjas pendientes.
- `400 NOT_ORANGE` al resolver un cromosoma que no es naranja.
- `404 NOT_FOUND` / `403 NOT_OWNER` (scope).

## 3. Frontend

- `karyotypeClient`: `viewXai(cid)`, `resolveChromosome(cid)`,
  `markAnomaly(cid)`, `validateCase()`, `getAudit()`.
- **XaiModal**: muestra el heatmap Grad-CAM + confianza; botón "Entendido"
  cierra. Al abrirlo se llama `viewXai` (registra el evento). Tras verlo, el
  botón "Aceptar" del cromosoma se habilita.
- **Panel de propiedades P2**: para un naranja seleccionado → botones
  "Ver explicabilidad (XAI)", "Aceptar" (deshabilitado hasta ver XAI),
  "Marcar anomalía (M)".
- **Gating UI**: botón "Pasar a Supervisor" deshabilitado mientras
  `summary.unresolved_orange > 0`; tooltip "Resuelva N cromosomas naranja".
  Al validar exitoso → banner de éxito + estado `ANALYST_VALIDATED`.
- **Audit log**: lista colapsable de eventos (tipo, cromosoma, hora).
- Refetch del cariotipo (react-query invalidation) tras cada mutación.

## 4. Tests (RN-09 ≥90%)

**Backend** (`test_karyotype_p2.py`):
- audit: hash chain encadena (`previous_hash` = `current_hash` anterior);
  `save()` sobre evento existente levanta error (append-only); verificación
  de cadena.
- XAI: setea `xai_viewed`, emite `XAI_VIEWED`.
- resolve: rechaza sin XAI (409); con XAI → RESOLVED + evento; rechaza no-naranja.
- validate: 409 si hay naranjas; éxito → ANALYST_VALIDATED + evento.
- gating derivado correcto; permisos (401/403).

**Frontend**: XaiModal (muestra heatmap, dispara viewXai), acciones (aceptar
gated por XAI), gating del botón validar, audit log, MSW.

## 5. MSW / seed
- Handlers de los 5 endpoints; XAI devuelve un heatmap base64 mock; estado
  mutable en memoria (xai_viewed/resolution_status por cromosoma) para que el
  flujo completo (ver XAI → aceptar → validar) funcione en el demo.
