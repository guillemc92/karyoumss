---
id: ADR-0023
title: Flujo del Supervisor — auditoría 5%, firma MFA y generación ISCN
date: 2026-07-24
status: accepted
refines: [ADR-0019, ADR-0020, ADR-0021, ADR-0022]
---

# ADR-0023: Flujo del Supervisor (auditoría 5% + firma MFA + ISCN)

## Contexto

El núcleo clínico de corrección de cariotipo (ADR-0021, P1→P4) termina cuando el
Analista valida el caso (`ANALYST_VALIDATED`). El **flujo del Supervisor**
(FSD-UC-005, FSD-UC-006) es la etapa siguiente y cierra la cadena de valor:

1. **Auditoría del 5%** (RN-08): el Supervisor revisa una muestra aleatoria del
   5% de cromosomas de alta confianza (>86%) para control de calidad.
2. **Firma con MFA** (FSD-UC-005): firma digital con segundo factor obligatorio
   (21 CFR Part 11), con **segregación de funciones** (Analista ≠ Supervisor,
   RN-06).
3. **Generación ISCN** (FSD-UC-006, RN-04): nomenclatura determinística ISCN
   2024 con override manual validado, **read-only tras generarse**.

**Estado previo:** `Sample` ya tiene FK `supervisor`; `AuditEventType` ya declara
`AUDIT_DECISION`, `SIGN_REPORT`, `ISCN_OVERRIDE` (declarados en P2, inertes). No
existe: selección del 5%, MFA en el contexto clínico, ni motor ISCN.

**Restricción de arquitectura (ADR-0020):** el secreto TOTP vive **solo en
backend-admin** (`User.two_factor_secret`, Fernet). backend-clinic tiene su
propia DB y un usuario-sombra sincronizado del JWT; **no** tiene el secreto.

## Decisión

### D1 — Estados nuevos del `Sample` (FSD-UC-005/006)
Se extiende `SampleStatus`: `SIGNED` (firmado por Supervisor) y `REPORTED`
(ISCN generado). `ANALYST_VALIDATED` ya cumple el rol de "pendiente de
Supervisor". Transiciones: `ANALYST_VALIDATED → (firma) → SIGNED → (ISCN) →
REPORTED`. `VALIDATED` (legado) se mantiene como alias terminal.

### D2 — Auditoría 5% determinista y reproducible (RN-08)
Selección con RNG sembrado por `sample_id` (`random.Random(str(sample.id))`):
pool = cromosomas activos con `confidence_score > 0.86`; se eligen
`max(1, ceil(0.05 * len(pool)))`. **Reproducible**: mismo caso → mismos
cromosomas (criterio de aceptación FSD-UC-005). Se materializa un modelo
`AuditReview` (1 por cromosoma seleccionado): `decision` (PENDING/CONFIRMED/
REJECTED) + `comment`. Cada decisión emite `AUDIT_DECISION` (ADR-0022). La
selección NO se persiste como flag en `Chromosome` (deriva); se recomputa o se
crea al abrir el caso como Supervisor.

### D3 — Firma MFA delegada a backend-admin (FSD-UC-005, RN-06)
backend-clinic **no** duplica el secreto TOTP: **delega la verificación** a
backend-admin vía un endpoint interno `POST /api/internal/mfa/verify/`
(protegido por un secreto de servicio compartido `INTERNAL_SERVICE_SECRET` en
header, no el JWT de usuario), invocado con un `admin_client` con circuit
breaker (mismo patrón que `pipeline_client`, ADR-0015). Esto respeta ADR-0020
(backend-admin = autoridad única de identidad/credenciales).

- **Segregación (RN-06):** la firma se rechaza si `signer == sample.analyst`
  (409 `SEGREGATION_VIOLATION`).
- **Gate:** no se puede firmar con auditorías 5% en `PENDING` (409
  `AUDIT_INCOMPLETE`).
- **Lockout:** 3 fallos de MFA → bloqueo de firma 15 min + evento de seguridad.
- Éxito → `SIGN_REPORT` (registra el método) + estado `SIGNED`.

*Alternativa considerada y rechazada:* TOTP local en backend-clinic (un
`SupervisorCredential` con secreto Fernet propio). Rechazada: duplica el secreto,
divergencia con backend-admin, viola la autoridad única de ADR-0020. Se
documenta como fallback offline sólo si la integración inter-servicio se difiere.

### D4 — Motor ISCN determinístico + override validado (FSD-UC-006, RN-04)
Función **pura** `generate_iscn(chromosomes) -> str` (ISCN 2024): cuenta por
clase final (incluye correcciones P3), `<total>,<sexo>` + anomalías numéricas
en orden ascendente (`+18` antes de `+21`), estructurales por cromosoma. Ej:
`46,XX`, `47,XY,+21`. Override manual: el Supervisor edita el string; se valida
la **gramática ISCN** (parser/regex); inválido → 400 `INVALID_ISCN`. El override
emite `ISCN_OVERRIDE` con `original_iscn`/`final_iscn`/`justification`.
- **RN-04:** `Sample.iscn_nomenclature` es **read-only tras generarse** — NO hay
  endpoint PATCH; el override es un endpoint de generación con validación, no una
  edición libre. El caso pasa a `REPORTED`.
- **PDF:** el reporte se materializa como **payload/HTML estructurado** (con la
  nota al pie del override si aplica); la binarización PDF real se difiere
  (fuera de alcance de este ADR — depende de infra de render).

### D5 — RBAC del Supervisor (ADR-0019)
Se agregan opciones granulares: `case.audit`, `case.sign`, `case.override_iscn`
(mapeo del FSD actors table `case:audit/sign/override_iscn`). Se otorgan al grupo
Supervisor; el Analista NO las tiene (segregación reforzada por permiso además de
por identidad).

### D6 — Fases (una PR por fase, tests ≥90% RN-09, E2E por fase)

| Fase | Alcance | Depende |
|---|---|---|
| **S1** | Modelo `AuditReview` + selección 5% determinista + decisiones (Confirmar/Rechazar) + `AUDIT_DECISION` + bandeja/vista de auditoría | este ADR |
| **S2** | Firma MFA (delegación a backend-admin) + segregación RN-06 + gate 5% + lockout + `SIGN_REPORT` + estado `SIGNED` | S1 |
| **S3** | Motor ISCN + override validado + `ISCN_OVERRIDE` + `iscn_nomenclature` read-only + estado `REPORTED` + reporte HTML | S2 |

## Trade-offs
- **Pros:** cierra la cadena clínica con cumplimiento 21 CFR Part 11; MFA sin
  duplicar secretos; ISCN determinístico y testeable; auditoría reproducible.
- **Cons:** S2 introduce integración inter-servicio (backend-admin ↔ clinic) con
  su propia superficie de fallo (mitigada por circuit breaker); el PDF real queda
  fuera; la selección 5% con pools chicos casi siempre da el mínimo (1).

## Consecuencias
- Migraciones nuevas en `apps/samples` (`AuditReview`, campos de firma/ISCN en
  `Sample`, estados nuevos, opciones RBAC).
- Nuevo endpoint interno en **backend-admin** (`/api/internal/mfa/verify/`) +
  `INTERNAL_SERVICE_SECRET` compartido — primera dependencia clinic→admin.
- La generación de reporte real (PDF/timestamping 21 CFR) queda como épica
  posterior; este ADR deja el ISCN, la firma y la traza que la habilitan.
