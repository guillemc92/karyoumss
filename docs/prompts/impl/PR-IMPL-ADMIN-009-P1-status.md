---
name: p1-profile-estado-al-2026-07-08
description: Estado de P1 (Sección Perfil) en rama feature/django-admin-stack al 2026-07-08 — backend OK + tests 99% verde; frontend bloqueado por archivo corrupto
metadata:
  project
---

# Estado P1 (Perfil) al 2026-07-08

**Rama:** `feature/django-admin-stack`
**Bounded context:** admin (ADR-0011, ADR-0013)
**Documento drive:** DD-ADMIN-002 §2 + ADR-0014
**Plan PRs:** P0 cerrado (PR-IMPL-ADMIN-008), P1 = PR-IMPL-ADMIN-009

## ✅ Backend cerrado y verificado (commit-ready)

- `apps/config/models.py` — `AdminProfile` con `db_table` via `_admin_schema_table('admin_profiles')`
- `apps/config/serializers.py` — `AdminProfileSerializer` con validaciones `full_name` (3-80), email normalize, phone regex
- `apps/config/views.py` — `MeProfileView(RetrieveUpdateAPIView)` con `get_or_create` idempotente
- `apps/config/urls.py` — namespace `config`, ruta `me/profile/`
- `apps/config/permissions.py` — `IsOwnerOrAdmin` (ya existía del P0)
- `apps/config/apps.py` — `auditlog.register(AdminProfile, include_fields=[...])` en `ready()`
- `apps/config/migrations/0001_initial.py` — creada y aplicada (SQLite test + dev)
- `pytest.ini` — `apps/config` añadido a `[coverage:run] source`
- `apps/config/tests/test_health.py` — actualizado (sections=['profile'])
- `apps/config/tests/test_profile.py` — **42 tests verde, cobertura 99%** (RN-09 ≥90%)

## ⚠️ Frontend a medio construir (con un archivo corrupto)

Creado:
- `frontend-admin/src/admin/types/config.ts` — `profileSchema` (Zod 4) + `AdminProfile`, `AdminProfileUpdate`
- `frontend-admin/src/admin/api/adminConfigClient.ts` — `getProfile()`, `updateProfile()` con reuso del patrón de `adminClient.ts`
- `package.json` — `zod@^4.4.3` añadido
- `frontend-admin/src/admin/msw/handlers.ts` — handlers GET/PATCH para `/api/admin/me/profile/`, **PERO el archivo está corrupto**: línea 53 es `const initialAuditLog: Record<string, AuditLogEntry[]> = {` y línea 54 empieza huérfana con `    {` (le borré la clave '11111111-...' por error en un Edit). Falta declarar `mockProfiles` a scope de módulo.

Pendiente:
- `frontend-admin/src/admin/components/ConfigSection.tsx` — esqueleto loading/error/data
- `frontend-admin/src/admin/components/ConfigForm.tsx` — form genérico con Zod
- `frontend-admin/src/admin/components/ProfileSection.tsx` — usa ConfigSection + ConfigForm
- `frontend-admin/src/App.tsx` — reemplazar `<Placeholder/>` de 'profile' por `<ProfileSection/>`
- Tests Vitest+MSW de los componentes

## 🔧 Fix inmediato al retomar

`handlers.ts` tiene la estructura dañada. Restaurar la línea 53-54 a:
```
const initialAuditLog: Record<string, AuditLogEntry[]> = {
  '11111111-1111-1111-1111-111111111111': [
    {
```
Y declarar `mockProfiles` a scope de módulo (después de `let baseUsers = ...`, antes de `const initialAuditLog = {`):
```ts
const mockProfiles: Record<string, { id, full_name, email, specialty, professional_license, phone, location, avatar_url, updated_at }> = {
  '1': {
    id: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
    full_name: 'María García López',
    email: 'maria.garcia@biomed.umss.bo',
    specialty: 'Citogenética Clínica',
    professional_license: 'MED-4452-BO',
    phone: '+591 2 2154847',
    location: 'UMSS · Hospital del Norte',
    avatar_url: '',
    updated_at: '2026-06-15T10:00:00Z',
  },
};
```

## 📚 Trazabilidad documentos vivos

- `docs/adr/0014-configuracion-panel-react-real-backend.md` — ADR integral P0–P10
- `docs/design/DD-ADMIN-002.md` — diseño detallado (P0–P10)
- `docs/DTI.md` §21 — fila ADR-0014
- `AGENTS.md` §3 — apunte `apps/config`; §5 — fila ADR-0014
- `MEMORY.md` (este repo) — debe tener un puntero a este file

## 🧠 Decisiones de implementación

- Zod 4 instalado como única dep nueva del P1 (DD §2.6 lo aprueba; §11.3 solo difiere react-hook-form/TanStack Query)
- Test suite preexistente rota al añadir el modelo: ya arreglado (2 tests ajustados: `test_health` sections, `test_save_normalizes_email` formato email)
- No se introduce `adminConfigStore` aún (DD §11.3 lo difiere hasta P3)
- No se introduce `ConfigShell` ni `ConfigSectionRouter` (P7) — cableado temporal en `App.tsx`
- Naming del PR: `feat(admin): P1 sección Perfil — AdminProfile model + me/profile/ + ProfileSection`
