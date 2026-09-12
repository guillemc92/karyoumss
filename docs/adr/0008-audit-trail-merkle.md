---
id: ADR-0008
title: Audit Trail Inmutable con Hash Chain + Extensión Merkle para Pruebas de Inclusión
date: 2026-06-23
status: accepted
related: [RN-05, FSD §6.1, BRD §23]
---

# ADR 0008: Audit Trail Inmutable con Hash Chain + Extensión Merkle para Pruebas de Inclusión

> ⚠️ **Nota de revisión (2026-06-23):** Aclaración de alcance — este ADR **no reemplaza** el hash chain lineal definido en FSD §6.1 (`previous_hash` + `current_hash` SHA256). El árbol Merkle es una **extensión opcional** para pruebas de inclusión eficientes en auditorías forenses, manteniendo el chain lineal como fuente primaria de orden secuencial.

## Contexto

Para cumplir con 21 CFR Part 11 y garantizar trazabilidad clínica total, el sistema debe asegurar que toda edición a un cariotipo sea **detectable como alterada** si es modificada o eliminada fuera del flujo legítimo.

**Línea base (FSD §6.1):** Cada fila de `edits` incluye `previous_hash` + `current_hash = SHA256(row_contenido || previous_hash)`, formando una **cadena lineal** verificable en O(n).

**Limitación detectada:** La cadena lineal obliga a recorrer O(n) hashes para demostrar que un evento específico pertenece al histórico completo. En auditorías forenses con 10 años de datos (>50k eventos por caso activo), esto es costoso.

## Decisión

**Implementar dos niveles de integridad:**

1. **Nivel 1 (obligatorio, base):** Hash chain lineal SHA256 ya definido en FSD §6.1. Garantiza orden secuencial e inmutabilidad. Cobertura: 100% de las filas.

2. **Nivel 2 (opcional, extensión):** Árbol **Merkle** construido por **período de auditoría** (ej: mensual). Cada hoja = `current_hash` de un evento del período. La raíz Merkle del período se **ancla como evento sintético** en la cadena lineal del Nivel 1.

**Estructura resultante:**

```
edits (FSD §6.1 — Nivel 1, lineal)
├── prev_hash, current_hash = SHA256(row || prev_hash)
│
└── merkle_anchors (Nivel 2, extensión)
    ├── period_id (ej: "2026-06")
    ├── merkle_root
    └── anclado en edits como {action: "MERKLE_ANCHOR", previous_hash, current_hash}
```

**Verificación:**
- Verificación rápida (¿este evento existió?): prueba de inclusión Merkle O(log n).
- Verificación total (¿la cadena está intacta?): recorrido lineal del Nivel 1 O(n).

## Trade-offs

**A favor:**
- Cumplimiento total de RN-05 (append-only).
- Doble garantía: orden cronológico (lineal) + pertenencia (Merkle).
- Eficiencia en auditorías forenses大规模.
- Respaldo para 21 CFR Part 11 §11.10(e) (protección de registros).

**Costo:**
- Overhead de hash: ~0.5ms por evento (aceptable, ver NFR-001).
- Almacenamiento adicional: 1 fila `merkle_anchors` por período (mínimo, típicamente mensual).
- Complejidad de implementación: requiere un **scheduler** que reconstruya el árbol al cierre de cada período.

## Consecuencias

- La tabla `edits` permanece **estrictamente append-only** (RN-05).
- La tabla nueva `merkle_anchors` también es append-only.
- Cualquier intento de modificar la base de datos resultará en mismatch:
  - Modificar una fila de `edits` → invalida `current_hash` de esa fila Y de todas las posteriores (Nivel 1) Y la raíz Merkle que la incluye (Nivel 2).
- Se requiere **sincronización con FSD §6.1** para documentar la tabla `merkle_anchors` en el diagrama ER (acción: editar FSD tras aprobación).
- AGENTS.md §7 entidad `EditTrail` se mantiene: Merkle es **infraestructura subyacente**, no cambia el contrato del agregado.

## Referencias

- RN-05 (tabla `edits` inalterable)
- FSD §6.1 (Modelo de datos AUDIT_TRAIL)
- BRD §23 Retención de Datos (Bitácora forense 10 años)
- BRD NFR-05 (Audit Trail: cumplimiento 21 CFR Part 11)
- AGENTS.md §4 regla RN-05