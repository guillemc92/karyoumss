# Prompt de Implementación — PR-IMPL-ADMIN-001

| Campo | Valor |
| :--- | :--- |
| ID del prompt | `PR-IMPL-ADMIN-001` |
| Título | Implementación de pestaña "Usuarios" en configuracion.html con CRUD + persistencia localStorage |
| Artefacto origen | FSD + DD |
| ID origen | `FSD-UC-ADMIN-001` (§4.8 FSD_vFinal.md v1.1) · `DD-ADMIN-001` · `ADR-0011` |
| Tipo de prompt | generación (código + tests) |
| Modelo recomendado | Sonnet |
| Temperatura | 0.2 |
| Versión | v0.1 |
| Fecha | 27/06/2026 |
| Autor(es) | Ing. Guillermo Mamani Chambi |
| Estado | Aprobado |

---

## 1. Anatomía del prompt

### 1.1 Role

Eres un **desarrollador frontend senior** especializado en HTML/CSS/JS vanilla con criterio de **minimalismo y reutilización estricta**. Conoces a fondo el módulo de configuración existente en `configuracion.html` (sidebar con `data-tab`, paneles `.config-content-body`, paleta CSS vars, FontAwesome 6.4, sin framework). Tu prioridad es **reutilizar 100% de los estilos y componentes existentes** — cero CSS nuevo salvo overrides inevitables.

### 1.2 Task

Generar el código completo (HTML + CSS mínimo + JS) de la **pestaña "Usuarios"** dentro de `configuracion.html`, implementando CRUD con persistencia en `localStorage`, gating por rol `admin`, y tests unitarios Vitest del módulo `UserStore` con cobertura ≥90% (RN-09).

### 1.3 Context

- **Documento fuente principal**: `docs/design/DD-ADMIN-001.md` (diseño detallado del feature).
- **Especificación**: `docs/fsd/FSD_vFinal.md` §4.8 FSD-UC-ADMIN-001.
- **Código existente**: `configuracion.html` (1261 líneas, sidebar con 6 tabs actuales, paleta CSS vars en `:root`, FontAwesome 6.4 ya cargado).
- **Entradas esperadas**:
  - Ninguna entrada externa (feature offline-first).
  - Estado actual de `localStorage['biomed:auth:role']` (string: `'admin' | 'analista' | 'supervisor'`).
  - Estado actual de `localStorage['biomed:admin:users']` (JSON array de `User` o `null`).
- **Restricciones de dominio**:
  - **ADR-0011**: Administrador TI NO accede a datos clínicos. El CRUD es solo de cuentas (no de casos ni muestras).
  - **RN-09**: Cobertura de tests ≥90% en módulo `UserStore` (lines/funcs/branches/statements).
  - **Sin PII real** en datos de prueba (usar emails `*.test@biomed.local`).
  - **Gating de visibilidad doble**: sidebar oculta + validación en handler `showTab()`.
- **Restricciones técnicas**:
  - Stack: HTML5 + CSS3 + JS ES2020 vanilla. Sin frameworks (no React, no Vue).
  - Persistencia: solo `localStorage` (clave namespace `biomed:admin:*`).
  - Sin nuevas dependencias externas (FontAwesome ya está cargado por CDN).
  - Compatible Chrome 120+, Edge 120+, Firefox 120+.
- **Ejemplos relevantes** (de `configuracion.html`):
  - Sidebar item existente (líneas 747-787): `<div class="config-nav-item" data-tab="X">...`
  - Panel existente (líneas 809-): `<div class="config-content-body" id="X-tab">`
  - Clases CSS reutilizables: `.card`, `.form-grid`, `.form-group`, `.btn-primary`, `.btn-outline`, `.btn-danger`, `.metrics-table`.

### 1.4 Reasoning (chain-of-thought estructurado)

Sigue estos pasos en orden:

1. **Verificar gating**: lee `localStorage['biomed:auth:role']`. Si `!== 'admin'`, ocultar el sidebar item `data-tab="users"` con `display: none` (inyectado desde script, no en HTML estático).
2. **Inyectar sidebar item**: añadir al `<div class="config-nav">` (después del último item existente, antes del cierre) un nuevo `<div class="config-nav-item" data-tab="users">` con icono `purple` (`<i class="fas fa-users-cog"></i>`), label "Usuarios", sublabel "Gestión institucional".
3. **Crear panel `#users-tab`**: nuevo `<div class="config-content-body" id="users-tab" style="display: none;">` siguiendo layout de paneles existentes. Estructura interna:
   - Header con título "Gestión de Usuarios Institucionales" + botón "Agregar usuario" (clase `.btn .btn-primary`).
   - `<table class="users-table metrics-table">` con columnas: Nombre, Email, Rol (badge), Estado (toggle), Alta, Acciones (iconos editar/eliminar).
   - Modal de edición (oculto por defecto) con `.form-grid` de 4 campos.
   - Modal de confirmación de baja.
4. **Implementar `UserStore`** (en `<script>` al final del `<body>`, namespace `window.biomed.admin`):
   - `UserStore.list()` → `Array<User>` (parsea JSON, fallback `[]` si corrupto).
   - `UserStore.save(user)` → genera `id` con `crypto.randomUUID()`, `created_at` y `updated_at` ISO 8601, push al array, persiste.
   - `UserStore.update(id, patch)` → merge shallow, actualiza `updated_at`, persiste.
   - `UserStore.remove(id)` → filtra, persiste.
   - `UserStore.validateEmail(email, excludeId?)` → regex RFC 5322 simplificado + check unicidad.
   - `UserStore.canDelete(id)` → `id !== currentUserId`.
5. **Implementar renderizado y handlers**:
   - `renderUserTable()` re-pinta la tabla desde `UserStore.list()`.
   - `openAddModal()` / `openEditModal(id)` / `closeModal()`.
   - `handleSave()` con validación inline (mensajes de error bajo cada campo).
   - `handleDelete(id)` con `confirm()` modal.
6. **Wirear el switch de tabs**: actualizar el handler existente `showTab(tabName)` para incluir `users` y re-validar rol antes de mostrar.
7. **Tests Vitest** (archivo separado `frontend/tests/userStore.spec.ts`):
   - Mockear `window.localStorage` y `window.crypto.randomUUID`.
   - Tests: list vacío, save genera id+fechas, update preserva id+created_at, remove filtra correctamente, validateEmail detecta duplicados case-insensitive, canDelete bloquea auto-eliminación, JSON corrupto → fallback `[]`.
   - Cobertura ≥90% (medir con `@vitest/coverage-v8`).
8. **Smoke test manual** (no automatizado, documentar en PR):
   - Set `localStorage['biomed:auth:role']='admin'`, recargar, ver pestaña.
   - Set `'analista'`, recargar, comprobar que no aparece.
   - Alta + recarga: el usuario persiste.

No expongas el razonamiento interno en el output final.

### 1.5 Stop condition

Detente cuando:
- El sidebar item `data-tab="users"` aparece solo si rol=admin.
- El panel `#users-tab` muestra tabla con CRUD funcional sobre `localStorage`.
- Los 4 flujos Gherkin de FSD-UC-ADMIN-001 pasan en smoke test manual.
- Los tests Vitest del `UserStore` pasan con cobertura ≥90% (lines/funcs/branches/statements).
- No se introducen archivos nuevos fuera de: `configuracion.html` (edición), `frontend/tests/userStore.spec.ts` (nuevo), `frontend/src/types/user.ts` (nuevo si se requiere TS).

No continues produciendo contenido más allá de estas condiciones.

### 1.6 Output

Formato: **bloque de código por archivo modificado/creado**, en este orden:

1. `configuracion.html` — diff conceptual con:
   - Inserción del sidebar item `data-tab="users"` (snippet HTML exacto).
   - Inserción del panel `#users-tab` completo (HTML).
   - Script `window.biomed.admin = (() => { ... })()` (IIFE con UserStore + handlers).
2. `frontend/tests/userStore.spec.ts` — código completo del archivo.
3. `frontend/src/types/user.ts` — solo si se introduce TypeScript (si no, omitir).
4. **Reporte de cobertura** esperado (formato tabla `file | % lines | % branches | % funcs | % statements`).

Al final, incluye:
- Lista de archivos modificados vs creados.
- Lista de archivos NO tocados (para auditoría rápida).
- Snippet de comandos para correr tests localmente.

Ejemplo de output (estructura):

```text
=== ARCHIVO MODIFICADO: configuracion.html ===
[snippet HTML del sidebar item]

[snippet HTML del panel #users-tab]

[snippet JS del UserStore + handlers]

=== ARCHIVO NUEVO: frontend/tests/userStore.spec.ts ===
[código completo]

=== REPORTE DE COBERTURA ESPERADO ===
| file                  | lines | branches | funcs | statements |
|-----------------------|-------|----------|-------|------------|
| userStore.ts          | 95%   | 92%      | 100%  | 95%        |
```

---

## 2. Invariantes del prompt

- La salida **debe** reutilizar las clases CSS existentes en `configuracion.html` (`.config-nav-item`, `.config-content-body`, `.card`, `.form-grid`, `.btn-*`, `.metrics-table`).
- La salida **no debe** añadir CDN ni dependencias npm nuevas.
- La salida **no debe** contener PII real en datos de prueba.
- La salida **debe** citar los IDs `FSD-UC-ADMIN-001`, `DD-ADMIN-001`, `ADR-0011` en comentarios del código.
- La salida **debe** alcanzar cobertura ≥90% (RN-09) en `UserStore` (verificable con `vitest --coverage`).
- La salida **debe** implementar gating doble (sidebar oculta + handler `showTab` re-valida).
- La salida **no debe** incluir endpoints backend ni llamadas `fetch` (alcance MVP localStorage).

## 3. Failure modes declarados

| Código | Descripción | Acción del consumidor |
| :--- | :--- | :--- |
| `E_MISSING_CONTEXT` | no se proporcionó `DD-ADMIN-001.md` o `configuracion.html` | abortar con error y solicitar archivos |
| `E_POLICY_CDUP` | output introduce CSS nuevo en vez de reutilizar | rechazar y regenerar con constraint reforzado |
| `E_POLICY_PII` | datos de prueba contienen emails reales o nombres personales | sanitizar antes de commit |
| `E_POLICY_COVERAGE` | cobertura <90% detectada en CI | añadir tests hasta cumplir RN-09 |
| `E_AMBIGUOUS_ROLE` | `biomed:auth:role` no está seteado al cargar | mostrar fallback "Sesión no iniciada, contacte al Admin" |

## 4. Guardrails

- **MUST**: ejecutar `vitest --coverage` antes de declarar Done; adjuntar reporte al PR.
- **MUST**: verificar visualmente con rol `admin` Y con rol `analista` (gating doble).
- **MUST**: incluir en el PR los 3 navegadores probados (Chrome, Edge, Firefox).
- **MUST NOT**: commitear archivos `storage_state.json` o `.notebooklm/` (no aplica aquí, pero documentar en `.gitignore` global del dev).
- **MUST NOT**: usar `localStorage` para datos clínicos — solo metadatos de usuarios (no rompe RN-03 pero documentar).
- **MUST**: registrar el prompt en `docs/PROMPT_MAPPING.md` con su salida.

## 5. Trazabilidad

| Origen | ID origen | Este prompt | Consumidor(es) | Artefacto generado |
| :--- | :--- | :--- | :--- | :--- |
| FSD + DD + ADR | `FSD-UC-ADMIN-001` · `DD-ADMIN-001` · `ADR-0011` | `PR-IMPL-ADMIN-001` | `dev-agent` (Claude Sonnet) | `configuracion.html` (edit) · `frontend/tests/userStore.spec.ts` (new) |

## 6. Pruebas del prompt (prompt tests)

### 6.1 Caso feliz

- **Input**: `biomed:auth:role='admin'` seteado; `biomed:admin:users=[]`.
- **Output esperado**: Admin abre `configuracion.html` → ve pestaña Usuarios → click → ve tabla vacía con botón "Agregar" → completa form → submit → usuario aparece en tabla → recarga página → usuario persiste.

### 6.2 Caso borde

- **Input**: `biomed:admin:users` contiene JSON corrupto (`'{not valid json'`).
- **Output esperado**: `UserStore.list()` retorna `[]`, registra warning en consola `"UserStore: storage corrupto, fallback a []"`, UI muestra tabla vacía.

### 6.3 Caso adversarial

- **Input**: Admin intenta eliminarse a sí mismo (`id === currentUserId`).
- **Output esperado**: `canDelete()` retorna `false`, UI bloquea botón eliminar y muestra mensaje "No puede eliminarse a sí mismo".

### 6.4 Caso adversarial (gating)

- **Input**: Usuario con rol `analista` manipula DOM para forzar `showTab('users')`.
- **Output esperado**: Handler `showTab` re-valida rol y rechaza, mostrando `#profile-tab` en su lugar. Log en consola: `"Admin tab access denied for role=analista"`.

## 7. Instrumentación

- **Tests**: `vitest@1.x` + `@vitest/coverage-v8`.
- **Métricas**:
  - `coverage.lines ≥ 90%`, `coverage.branches ≥ 90%`, `coverage.funcs ≥ 90%`, `coverage.statements ≥ 90%` (RN-09).
  - `test_count ≥ 7` (los 7 escenarios listados en §1.4 paso 7).
  - `manual_smoke_passed = true` (Chrome + Edge + Firefox).
- **Lint**: no se introduce (HTML/JS plano).

## 8. Versionado

| Versión | Fecha | Autor | Cambio | Modelo validado |
| :--- | :--- | :--- | :--- | :--- |
| v0.1 | 27/06/2026 | G. Mamani | creación inicial | Sonnet |

## 9. Revisión humana

| Revisor | Fecha | Veredicto | Notas |
| :--- | :--- | :--- | :--- |
| G. Mamani | 27/06/2026 | aprobado | DD-ADMIN-001 + FSD-UC-ADMIN-001 v1.1 consistentes |

---

## Plantilla express (copiar y pegar)

```
# Role
Desarrollador frontend senior vanilla (HTML/CSS/JS) con criterio de reutilización estricta.

# Task
Implementar pestaña "Usuarios" en configuracion.html con CRUD + localStorage + tests Vitest ≥90% (RN-09).

# Context
- DD: docs/design/DD-ADMIN-001.md
- FSD: docs/fsd/FSD_vFinal.md §4.8 FSD-UC-ADMIN-001
- ADR-0011: Administrador TI sin acceso a datos clínicos
- Código: configuracion.html (1261 líneas, paleta CSS vars, FontAwesome 6.4)
- Stack: HTML5 + CSS3 + JS ES2020 vanilla. Sin frameworks.
- Persistencia: localStorage namespace 'biomed:admin:*'
- Gating: solo rol='admin' ve la pestaña

# Reasoning
1. Verificar gating por biomed:auth:role
2. Inyectar sidebar item data-tab="users" (icono purple fa-users-cog)
3. Crear panel #users-tab con tabla + modales (reutilizar .card, .form-grid, .metrics-table)
4. Implementar UserStore (list/save/update/remove/validateEmail/canDelete)
5. Wirear handlers (renderUserTable, openAddModal, openEditModal, handleSave, handleDelete)
6. Actualizar showTab() para incluir 'users' con re-validación de rol
7. Tests Vitest del UserStore con cobertura ≥90%

# Stop condition
Detente cuando: gating funcional + CRUD operativo + 7 tests pasan + cobertura ≥90% + sin archivos nuevos fuera de scope.

# Output
Bloques de código por archivo:
1. configuracion.html (sidebar item + panel #users-tab + script UserStore)
2. frontend/tests/userStore.spec.ts (7 tests)
3. Reporte de cobertura esperado (tabla)

# Invariants
- Reutilizar CSS existente (no añadir clases nuevas salvo inevitables)
- Sin CDN ni npm nuevos
- Sin PII real en fixtures
- Citar FSD-UC-ADMIN-001, DD-ADMIN-001, ADR-0011 en comentarios
- Cobertura ≥90% RN-09
- Gating doble (sidebar oculta + showTab re-valida)
- Sin endpoints backend (alcance MVP)

# Failure modes
- E_MISSING_CONTEXT: abortar
- E_POLICY_CDUP: rechazar output con CSS nuevo
- E_POLICY_PII: sanitizar
- E_POLICY_COVERAGE: añadir tests
```