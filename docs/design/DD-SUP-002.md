# DD-SUP-002 — Firma MFA del Supervisor (S2)

| Campo | Valor |
|---|---|
| **ID** | DD-SUP-002 |
| **ADR origen** | [ADR-0023](../adr/0023-supervisor-auditoria-firma-iscn.md) §D3/§D6 (S2) + [ADR-0020](../adr/0020-sso-backend-admin-autoridad-jwt.md) + [ADR-0022](../adr/0022-audit-trail-clinico-django.md) |
| **FSD** | FSD-UC-005 (firma con MFA) |
| **Reglas** | RN-06 (segregación Analista≠Supervisor), RN-05 (audit), 21 CFR Part 11 |
| **Estado** | En implementación |
| **Fecha** | 2026-07-24 |

## 1. Alcance de S2
Sobre un caso `ANALYST_VALIDATED` con la auditoría del 5% completa (S1), el
Supervisor **firma el reporte con MFA** (segundo factor TOTP). Transición
`ANALYST_VALIDATED → SIGNED`. **Sin ISCN** (S3).

## 2. backend-admin — verificación MFA delegada (ADR-0023 D3)
El secreto TOTP vive solo acá (ADR-0020). Se expone un endpoint **interno**
service-to-service:
- `POST /api/internal/mfa/verify/` — body `{email, code}`; protegido por header
  `X-Internal-Secret == settings.INTERNAL_SERVICE_SECRET` (NO por JWT de usuario;
  es tráfico entre servicios). Reusa `_verify_totp_code`. Respuestas: `200
  {valid: bool, enrolled: bool}`; `403` si el secreto de servicio no coincide.
- `INTERNAL_SERVICE_SECRET` nuevo en settings de **ambos** backends (env).

## 3. backend-clinic — servicio de firma
### 3.1 `admin_client` (circuit breaker, espejo de `pipeline_client`)
`verify_mfa(email, code) -> dict {valid, enrolled}` llama al endpoint interno con
el header de servicio y timeout; falla → `MfaServiceError` (503).

### 3.2 Campos nuevos en `Sample`
`signed_by` (FK user, null), `signed_at` (datetime, null). Migración.

### 3.3 Modelo de lockout (FSD-UC-005 A2)
`SignLockout` (OneToOne user): `failed_attempts`, `locked_until`. 3 fallos de MFA
→ `locked_until = now + 15min` + reset del contador + evento de seguridad. Éxito
o expiración → reset.

### 3.4 Servicio `sign_report(sample, supervisor, mfa_code)`
Orden de validación:
1. `_assert_editable`-like: estado debe ser `ANALYST_VALIDATED` → `409 NOT_SIGNABLE`.
2. **Segregación (RN-06):** `supervisor.id == sample.analyst_id` → `403 SEGREGATION_VIOLATION`.
3. **Gate 5%:** `audit_summary(sample).pending > 0` → `409 AUDIT_INCOMPLETE`.
4. **Lockout:** `locked_until > now` → `423 MFA_LOCKED`.
5. **MFA:** `admin_client.verify_mfa`. `valid=False` → registra fallo (lockout++),
   `401 MFA_INVALID`. `enrolled=False` → `400 MFA_NOT_ENROLLED`.
6. Éxito → `status=SIGNED`, `signed_by/signed_at`, emite `SIGN_REPORT`
   (payload `{method:'TOTP'}`), resetea lockout.

### 3.5 Endpoint + RBAC
`POST /samples/{id}/sign/` body `{mfa_code}`, permiso `case.sign` (Supervisor/
Admin, NO Analista — migración de datos, segregación reforzada por permiso).

## 4. Frontend
- `karyotypeClient.signReport(id, code)`.
- En `SupervisorAuditPanel`: cuando `summary.pending === 0`, botón **"Firmar
  Reporte"** → `SignMfaModal` (input de 6 dígitos) → `sign`. Deshabilitado
  mientras haya auditorías pendientes (tooltip "Debe revisar N…").
- Éxito → banner "Reporte firmado" + estado `SIGNED`. Errores mapeados:
  409 AUDIT_INCOMPLETE, 403 SEGREGATION_VIOLATION, 401 MFA_INVALID,
  423 MFA_LOCKED, 400 MFA_NOT_ENROLLED.
- MSW: handler `/sign/` con MFA mock (código `123456` válido; otro → inválido;
  3 inválidos → 423). Endpoint interno de admin no se toca en el front.

## 5. Tests (RN-09 ≥90%)
**backend-admin** (`test_internal_mfa.py`): secreto de servicio ok/403, código
válido/ inválido, usuario sin 2FA (`enrolled=False`).
**backend-clinic** (`test_supervisor_s2.py`, `admin_client` mockeado): firma ok →
SIGNED + SIGN_REPORT; segregación 403; gate 5% 409; MFA inválido 401 + lockout a
los 3; lockout 423; estado no firmable 409; permisos (analista sin case.sign 403).
**frontend**: modal + gating + errores + MSW.
