---
id: ADR-0014
title: Port del panel "Configuración del Sistema" desde configuracion.html a React con backend Django real
date: 2026-07-08
status: proposed
supersedes: ninguno (convive con ADR-0013)
related: [ADR-0011, ADR-0013, FSD-UC-ADMIN-001, DD-ADMIN-001]
fase: desarrollo
autor: Ing. Guillermo Mamani Chambi
---

# ADR 0014: Port del panel "Configuración del Sistema" a React con backend real

## Contexto

El bounded context admin (ADR-0011, ADR-0013) ya tiene backend Django + DRF vivo
con el CRUD de `AdminUser` operativo y `frontend-admin` con shell React + Vite. Sin
embargo, la sección "Configuración del Sistema" del sidebar — que era la página
institucional rica original en `configuracion.html` (1667 líneas) — quedó reducida
a 6 `<Placeholder/>` simples en `App.tsx` (`renderSection`, líneas 41–76). El demo
actual muestra solo el shell + la pestaña Usuarios funcional; el resto del panel
que el equipo viene usando como referencia visual y funcional desde el MVP
(`PR-IMPL-ADMIN-001`) no está portado.

El gap concreto entre el HTML original y el React actual:

| Sección (HTML id) | configuracion.html (líneas aprox.) | App.tsx hoy | Backend hoy |
|:---|:---|:---|:---|
| `profile-tab` | 817–867 (foto + form-grid 6 campos + acciones) | `<Placeholder/>` "Perfil de Usuario" | ❌ no existe modelo de perfil |
| `security-tab` | 868–911 (cambio contraseña + 2FA toggle) | `<Placeholder/>` "Seguridad" | ❌ no existe endpoint PATCH password / 2FA |
| `modelos-tab` | 912–1076 (modelos IA, parámetros, métricas, rendimiento) | `<Placeholder/>` "Modelo IA" | ❌ no existe config de modelo |
| `notifications-tab` | 1077–1109 (preferencias email/in-app) | `<Placeholder/>` "Notificaciones" | ❌ no existe config de notificaciones |
| `integrations-tab` | 1110–1146 (HIS / LIS / API endpoints + test) | `<Placeholder/>` "Integraciones" | ❌ no existe config de integraciones |
| `appearance-tab` | 1147–1178 (tema, densidad, idioma) | `<Placeholder/>` "Visualización" | ❌ no existe config de apariencia |
| `users-tab` | 1180–1259 (CRUD completo con modal y confirm) | `AdminUsersPanel` real | ✅ `/api/admin/users/*` (F1–F7 cerrados) |

Decisión del arquitecto en sesión 2026-07-08: **el panel Configuración debe
portarse a React conectado a backend real, no a mocks**. Las 6 secciones nuevas
más la sección Usuarios (que ya funciona) deben convergir en un único bounded
context admin funcional antes de continuar con F8+.

## Decisión

Adoptar el siguiente plan de port incremental, anclado al stack de ADR-0013,
para que el panel "Configuración del Sistema" deje de ser demo y pase a ser
funcional contra el backend Django real, sección por sección, en este orden:

| # | Sección | Modelo backend nuevo | Endpoints nuevos | Componentes React nuevos | Esfuerzo |
|:-:|:---|:---|:---|:---|:---:|
| **P1** | `profile` | `AdminProfile` (1:1 con `User`, FK `user_id`) | `GET/PATCH /api/admin/me/profile/` | `ProfileSection.tsx` (form-grid + foto) | 6h |
| **P2** | `security` | extender `User` con `two_factor_enabled`, `password_changed_at`; nueva tabla `PasswordHistory` opcional | `POST /api/admin/me/password/`, `POST /api/admin/me/2fa/toggle/` | `SecuritySection.tsx` (form + 2FA toggle) | 8h |
| **P3** | `modelos` | `ModelConfig` (1 fila activa por institución, JSONField params), `ModelMetric` (snapshots append-only) | `GET /api/admin/models/active/`, `PATCH /api/admin/models/active/`, `GET /api/admin/models/metrics/?days=30` | `ModelsSection.tsx` (cards + sliders + métricas chart) | 10h |
| **P4** | `notifications` | `NotificationPreference` (1:1 con `User`) | `GET/PATCH /api/admin/me/notifications/` | `NotificationsSection.tsx` (toggles agrupados) | 5h |
| **P5** | `integrations` | `Integration` (rows por sistema: HIS/LIS/API) | `GET/POST /api/admin/integrations/`, `POST /api/admin/integrations/{id}/test/` | `IntegrationsSection.tsx` (cards + test button) | 8h |
| **P6** | `appearance` | `AppearancePreference` (1:1 con `User`) | `GET/PATCH /api/admin/me/appearance/` | `AppearanceSection.tsx` (theme picker + selects) | 4h |
| **P7** | shell | — | — | extraer `ConfigNav` y `ConfigContent` del HTML (sidebar interno de la pestaña Config) | 4h |
| **Total** | | | | | **45h** |

### Forma del port

1. **Catálogo de tipos compartido.** Crear `frontend-admin/src/admin/types/config.ts`
   con los shapes de las 6 secciones. El backend usa DRF serializers como fuente
   de verdad; el cliente genera tipos con `openapi-typescript` desde
   `http://127.0.0.1:8001/api/schema/`.
2. **Capa de fetch centralizada.** Extender `adminUsersStore` a un
   `adminConfigClient.ts` (un cliente por sección, no un monolito) que:
   - Envía `Authorization: Bearer <token>` (ya viene del `SessionProvider`).
   - Maneja 401 → fuerza re-exchange vía `POST /api/admin/auth/exchange`.
   - Maneja 403 → muestra mensaje "requiere rol administrador".
   - Usa `AbortController` para evitar state updates tras unmount.
3. **Patrón de sección.** Cada `XxxSection.tsx` sigue la misma anatomía:
   ```tsx
   <section className="config-content-body">
     <header><h3>{title}</h3><p>{subtitle}</p></header>
     {loading && <Skeleton/>}
     {error && <ErrorBanner onRetry={refetch}/>}
     {data && <ConfigForm schema={schema} initial={data} onSubmit={mutate}/>}
     {toast && <Toast kind={toast.kind} message={toast.msg}/>}
   </section>
   ```
   Así los 6 placeholders convergen en código predecible, testeable, y
   cubierto por RN-09 ≥90%.
4. **Sin librería de formularios nueva.** Se usa `react-hook-form` solo si
   el equipo lo aprueba en DD-ADMIN-002; mientras tanto, `useState` +
   `onSubmit` con validación manual por Zod schema. Justificación: el
   backend ya devuelve errores por campo (DRF `field_errors`), no queremos
   duplicar validación client-side sin necesidad.
5. **Tests.** Cobertura ≥90% (RN-09) por sección, con MSW para los nuevos
   endpoints. Se mantienen los tests E2E de auth_bridge del F7.
6. **Migración de datos del MVP localStorage.** El HTML original persiste
   cambios en `localStorage` (botones con `alert('Guardado')`). Como
   decisión de port: **se descarta el estado localStorage** y se rehidrata
   desde el backend. Si un usuario tenía prefs en localStorage, se le
   ofrece un banner one-shot "detectamos preferencias locales, ¿migrar?".
   Justificación: la fuente de verdad ahora es Django; el MVP local
   convivía porque no había backend. Razón documentada en
   `docs/design/DD-ADMIN-002.md` §3.

### Estructura nueva de archivos

```
backend-admin/
└── apps/
    ├── users/                       (existente, F1–F7)
    ├── audit/                       (existente)
    ├── config/                      (NUEVO)
    │   ├── models.py                (AdminProfile, ModelConfig, ModelMetric,
    │   │                             NotificationPreference, Integration,
    │   │                             AppearancePreference)
    │   ├── serializers.py
    │   ├── views.py
    │   ├── urls.py                  (router: /api/admin/me/* + /integrations/*
    │   │                             + /models/*)
    │   ├── permissions.py           (IsOwnerOrAdmin para /me/*)
    │   ├── services.py              (lógica de dominio: rotate_password,
    │   │                             test_integration_connection, etc.)
    │   ├── migrations/
    │   └── tests/                   (≥90% cobertura)

frontend-admin/
└── src/
    └── admin/
        ├── components/
        │   ├── ConfigShell.tsx      (NUEVO — sidebar interno de Config)
        │   ├── ConfigForm.tsx       (NUEVO — form genérico con Zod)
        │   ├── ConfigSection.tsx    (NUEVO — esqueleto loading/error/data)
        │   ├── ProfileSection.tsx   (NUEVO)
        │   ├── SecuritySection.tsx  (NUEVO)
        │   ├── ModelsSection.tsx    (NUEVO)
        │   ├── NotificationsSection.tsx (NUEVO)
        │   ├── IntegrationsSection.tsx  (NUEVO)
        │   ├── AppearanceSection.tsx    (NUEVO)
        │   ├── AdminUsersPanel.tsx  (existente, F4–F6)
        │   └── ... (existentes)
        ├── api/
        │   ├── adminUsersClient.ts  (existente)
        │   ├── adminConfigClient.ts (NUEVO — 6 clientes tipados)
        │   └── schema.ts            (NUEVO — tipos generados del openapi)
        ├── state/
        │   ├── useSession.tsx       (existente)
        │   ├── adminUsersStore.tsx  (existente)
        │   └── adminConfigStore.tsx (NUEVO — opcional, si crece la complejidad)
        └── types/
            └── config.ts            (NUEVO — types manuales fallback)
```

### Lo que **no cambia**

- Stack ADR-0013: Django + DRF + React 18 + Vite + TypeScript 5.
- `configuracion.html` permanece en repo (sin `git rm`) como **referencia
  histórica** del MVP, no se borra. Si en el futuro el bounded context
  clínico se migra, el patrón a seguir está aquí.
- Auth bridge F7 (FastAPI JWT ↔ Django Token) sigue siendo el camino de
  acceso; las secciones `/me/*` se benefician del `request.user` ya
  hidratado.
- `AGENTS.md` §3 stack clínico intacto.
- RN-09 (≥90% cobertura) sigue siendo invariante.

## Justificación

### Por qué **port conectado a backend real**, no mock estático

- Coherencia con la directriz del arquitecto de la sesión 2026-07-08 y con
  el §1 de `AGENTS.md` (SDD implica que el demo debe ser fiel a la
  especificación, no una maqueta).
- Mocks generarían deuda: al pasar a F8 habría que reescribir cada sección.
  Hacerlo bien ahora cuesta ~45h; hacerlo dos veces costaría ~70h.
- El bounded context admin ya tiene `User` y `AdminUser` modelados con
  cuidado (constraints, índices, audit). Crear `apps/config` con 6 modelos
  más livianos no introduce riesgo arquitectónico nuevo.

### Por qué **un solo ADR integral** y no seis micro-ADRs

- Las 6 secciones comparten patrón de fetch, layout, tests y shape de
  serialización. Atomizar en 6 ADRs crearía 6 documentos con 80% contenido
  repetido, violando el principio de documentación eficiente.
- F1–F7 ya se documentaron en un solo ADR-0013 con tabla de fases. Este
  ADR replica el mismo patrón.
- Si una sección requiere una decisión no obvia (p.ej. cifrado de
  credenciales HIS en P5), esa sub-decisión se documenta con un ADR
  dedicado (`ADR-0015-cifrado-credenciales-integraciones` o similar).

### Por qué **`apps/config` como nueva app Django**, no métodos en `apps/users`

- SRP: `users` ya tiene 3 archivos de tests + 4 servicios. Agregarle 6
  modelos + 6 viewsets lo convertiría en un god-module.
- ADR-0004 (hexagonal) recomienda un bounded context por app Django.
- Migraciones más limpias: si revertimos P5, se revierte solo
  `apps/config/migrations/0020_integration*.py`, no media app de users.
- Permite borrado físico futuro: si el bounded context se reescribe,
  `python manage.py migrate config zero` es atómico.

### Por qué **no** `react-hook-form` ni TanStack Query por ahora

- Las 6 secciones tienen 3–8 campos cada una. `useState` + `onSubmit`
  con Zod resuelve en <50 LOC por sección. Adoptar una librería añade
  curva de aprendizaje + 1 dependencia + tests más complejos, sin
  beneficio proporcional.
- TanStack Query se considerará en F8+ si se introduce caché de
  notificaciones en tiempo real. Hoy todas las secciones son
  fetch-on-mount + mutate-on-submit, lo que no requiere caché.
- Revisable en retrospectiva: si tras P3 (la sección más compleja)
  la deuda se vuelve obvia, se reabre la decisión con datos.

### Por qué **descartar localStorage del MVP**

- El MVP convivía con el backend ausente. Ahora hay backend. Mantener
  ambos introduce source-of-truth split, race conditions y bugs de
  sincronización.
- El banner one-shot de migración cubre el caso del usuario que tenía
  prefs en localStorage: se leen, se validan, se `POST`ean al backend
  en bloque, y se purgan del storage. Si falla, se conserva local
  como fallback de solo-lectura (graceful degradation, RN-07).

## Consecuencias

### Positivas

- El panel "Configuración del Sistema" pasa de demo a funcional. El
  bounded context admin entrega valor de release, no solo de andamiaje.
- Patrón de sección repetible: P1–P6 comparten la misma forma, lo que
  reduce el coste de agregar P7+ si aparecen nuevas secciones.
- `apps/config` queda modelada y testeada, lista para que el módulo
  clínico (FastAPI) la consuma vía API unificada en fases futuras
  (p.ej. `ModelConfig.active` consumido por el microservicio de
  inferencia, ADR-0007).
- Cobertura RN-09 sigue subiendo porque cada sección es testeable
  de forma aislada (cliente + componente + serializer + service).

### Negativas

- **45h de trabajo adicional** antes de F8. Sumado a las ~50h de F1–F7
  (ADR-0013), el stack admin llega a ~95h ≈ 12 sprints de 8h.
  Mitigación: P1–P6 se pueden paralelizar entre 2 desarrolladores si
  el equipo lo aprueba; los bloqueantes entre P son pocos (P1 y P2
  comparten migración de `User`).
- **6 nuevos modelos Django** aumentan la superficie de ataque y de
  mantenimiento. Mitigación: revisar todos con `django-auditlog`
  excepto métricas de modelo (que son append-only por diseño).
- **`configuracion.html` queda como deuda visible** en el repo. Si en
  CODEOWNERS se exige borrar el HTML al cerrar P6, se borra con
  `git rm` y commit `chore(admin): remove MVP HTML after P6`.
- Si en el futuro el bounded context clínico quiere leer `ModelConfig`
  (p.ej. umbral de confianza), Django y FastAPI deben acoplarse. Hoy
  no se acoplan (limpio), pero **se documenta como tensión abierta**
  en §Tensión con reglas del proyecto.

### Neutras

- El shell `BiomedShell.tsx` no cambia. Las secciones viven dentro
  de `renderSection(active)`.
- El `SessionProvider` no cambia. Las nuevas secciones usan el mismo
  `useSession()` para token y rol.
- Las reglas RN-01/02/04/05/06/07/08 clínicas no se ven afectadas
  (siguen siendo del bounded context clínico).

## Plan de implementación

| Fase | Alcance | Esfuerzo | Bloqueante |
|:-:|:---|:---|:---|
| **P0** | Crear `apps/config` skeleton + URL routing registrado en `admin_backend/urls.py` | 2h | sí (todo lo demás) |
| **P1** | `AdminProfile` + sección Perfil | 6h | P0 |
| **P2** | Campos `two_factor_enabled`/`password_changed_at` en `User` + endpoints + sección Seguridad | 8h | P0 |
| **P3** | `ModelConfig` + `ModelMetric` + sección Modelos | 10h | P0 |
| **P4** | `NotificationPreference` + sección Notificaciones | 5h | P0 |
| **P5** | `Integration` + sección Integraciones (cifrado de credenciales cubierto por ADR-0015 si aplica) | 8h | P0 |
| **P6** | `AppearancePreference` + sección Apariencia | 4h | P0 |
| **P7** | Extraer `ConfigShell` y `ConfigContent` como layout interno reutilizable | 4h | P1–P6 |
| **P8** | Banner de migración `localStorage` → backend (one-shot) | 2h | P1, P4, P6 |
| **P9** | Validación E2E manual de las 7 secciones con la demo corriendo | 2h | P1–P8 |
| **P10** | Documentación: DD-ADMIN-002, AGENTS §11 (rama), CHANGELOG | 2h | P9 |
| **Total** | | **53h** (incluye P0 + P7–P10 no listados en tabla de §Decisión) | |

### Riesgos y mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|:---|:---:|:---:|:---|
| 6 nuevos modelos rompen migraciones SQLite↔Postgres | Media | Alto | Usar `_admin_schema_table` ya validado en `apps/users`; tests con ambos vendors |
| Cobertura RN-09 cae al portar 6 secciones a la vez | Alta | Medio | Gate por fase: P1 no mergea si coverage <90% en `apps/config` |
| Sección Modelos requiere chart lib (recharts/chart.js) | Media | Bajo | Evaluar al llegar a P3; mientras, renderizar métricas como tabla (sin gráfico) |
| localStorage de MVP contiene datos inválidos | Alta | Bajo | Banner muestra "X prefs detectadas, ¿migrar?" con preview; usuario decide |
| Auth bridge se rompe al agregar `/me/*` | Baja | Crítico | Tests E2E existentes (F7) deben seguir verdes; agregar test de `/me/profile` con token fresco |
| Rendimiento: 6 fetches simultáneos al cargar Config | Media | Bajo | Stale-while-revalidate con `useSWR` si se observa lentitud; por ahora, secuencial con skeleton |

## Tensión con reglas del proyecto y cómo se resuelve

| Regla | Tensión | Resolución |
|:---|:---|:---|
| **AGENTS §3 stack clínico** | Sección Modelos toca U-Net + EfficientNet-B3 | El panel **configura** parámetros (`umbral_confianza`, `modo_analisis`); no reemplaza el modelo. ADR-0007 sigue rigiendo la inferencia. Los parámetros son consumidos por el microservicio vía API, no embebidos. |
| **ADR-0011 (rol Administrador TI)** | ¿Las 6 secciones son solo para `admin`? | `/me/*` es accesible para cualquier usuario autenticado (perfil propio, seguridad propia, apariencia propia). `/models/*` y `/integrations/*` requieren `IsAdminRole` (mismo mixin que `users`). |
| **ADR-0012 (PostgreSQL schema admin)** | 6 modelos nuevos → schema admin | Sí, todos van al schema `admin` vía `_admin_schema_table` ya establecido. |
| **RN-04/05 (iscn_readonly / edits_append)** | No aplica (b.c. admin) | El b.c. admin no toca `iscn_nomenclature` ni `edits`. |
| **RN-06 (segregación analista ≠ supervisor)** | ¿Cambiar rol propio? | El `User.role` es editable solo por admin. El usuario normal no puede cambiar su rol. Cubierto por `IsAdminRole` en `PATCH /api/admin/users/{id}/`. |
| **RN-07 (graceful degradation)** | Si backend cae, ¿qué ve el usuario? | `ErrorBanner` con `onRetry`. La UI no se rompe. |
| **RN-09 (cobertura ≥90%)** | 6 secciones × 2 stacks = 12 suites | Cada suite mide su propio coverage. Gate en CI por carpeta: `apps/config` y `frontend-admin/src/admin/components/*Section.tsx`. |
| **AGENTS §11 (PR a release/2.0.0)** | Cambio grande | Una PR por fase P1–P6 (no una PR monolítica). Cada PR revisa migraciones + serializers + tests. |

## Alternativas evaluadas

### A1. Mantener `<Placeholder/>` simples y avanzar a F8 (status quo)
- **Pro:** No esfuerzo, foco en F8.
- **Contra:** La demo del admin queda "interfaz pero no completo", que
  es exactamente el dolor que el arquitecto señaló en sesión
  2026-07-08. El bounded context admin se entrega a medias.
- **Rechazado** por decisión explícita del arquitecto.

### A2. Port con MSW (mocks), no backend real
- **Pro:** Más rápido, sin tocar migraciones Django.
- **Contra:** Crea código que se reescribe al pasar a F8. El cliente
  no aprende los shapes reales. No hay progreso de cobertura backend.
- **Rechazado** por la misma razón que A1: el demo debe ser fiel a la
  spec.

### A3. Reescribir `configuracion.html` a HTML+JS vanilla moderno y mantenerlo como estático
- **Pro:** Sin React, sin Vite, sin TS.
- **Contra:** Rompe ADR-0013 (React es el stack declarado). Genera
  dos frontends (vanilla + React) sin justificación. Imposibilita
  compartir componentes como `BiomedShell`.
- **Rechazado** por violación de ADR-0013.

### A4. (Propuesta) Port incremental por fase P1–P10, conectado a backend real
- Ya descrita en §Decisión.

### A5. Port monolítico en un solo PR
- **Pro:** Una sola PR, una sola revisión.
- **Contra:** Migraciones de 6 modelos en un commit son imposibles
  de revisar bien. Si P3 falla, se revierte todo. La cobertura
  RN-09 no se puede medir por fase.
- **Rechazado** por violaciones a RN-09 y revisión sana.

## Trazabilidad

- **Sube a:** BRD §3.2 (Personal TI Institucional) → MRD-13
  (multi-institución) → FSD §4.8 (FSD-UC-ADMIN-001) → DD-ADMIN-001 →
  ADR-0011 (rol admin) → ADR-0013 (stack) → **este ADR-0014**.
- **Genera:** `DD-ADMIN-002` (diseño detallado de las 6 secciones),
  `PR-IMPL-ADMIN-004` a `PR-IMPL-ADMIN-009` (uno por fase P1–P6),
  rama `feature/admin-config-panel`.
- **Impacta:**
  - AGENTS §3 (no cambia el stack, sí enumera las nuevas apps
    `apps/config` y los nuevos componentes).
  - FSD-UC-ADMIN-001 §5 (nuevos casos de uso UC-CONF-001 a UC-CONF-006).
  - DD-ADMIN-001 §5 (sección nueva: configuración personal e
    institucional).
  - DTI §21 (este ADR entra como ADR-0014).
  - CHANGELOG (nuevas features, una entrada por fase P1–P6).

## Notas

- El esfuerzo total (45–53h) se comerá ~1.5 sprints del equipo.
  Si se quiere acelerar, P3 (Modelos) y P5 (Integraciones) son
  candidatos a diferir — la sección Modelos no bloquea uso clínico
  (la config por defecto es segura), y P5 puede esperar a que
  aparezca la primera integración real.
- La rama de trabajo es `feature/admin-config-panel`, que se mergea
  a `release/2.0.0` siguiendo AGENTS §11. PRs pequeños por fase
  (P1, P2, …, P6) para revisión sana.
- Si al llegar a P3 (sección Modelos) surge la necesidad de leer
  parámetros en el microservicio de inferencia (ADR-0007), se
  abrirá un **ADR-0015-acoplamiento-config-inferencia** dedicado
  para no inflar este documento.
- Este ADR **no reemplaza** ADR-0013; lo complementa con el alcance
  funcional del panel Configuración. ADR-0013 sigue rigiendo el
  stack; este ADR rige el **qué** se entrega en ese stack.
