# SPEC-007 — Fix bootstrap de MSW en demo dev (mock no intercepta)

> **Feature 11** del backlog del arquitecto. Bug operacional reportado el
> 2026-07-10 ("el panel admin no crea usuarios") y **confirmado** el
> 2026-07-11 con evidencia de logs de Vite.
>
> No reemplaza SPEC-006 ni FSD-UC-ADMIN-001. Es un **fix de infraestructura
> de desarrollo** que cierra la brecha entre los tests (que sí mockean con
> MSW + jsdom) y la demo (que debería mockear con MSW + service worker
> pero no lo hacía por un bug de bootstrap).

| Campo | Detalle |
|---|---|
| **Bounded context** | admin (ADR-0011, ADR-0013) |
| **Documento drive** | ADR-0014 §Plan P10, FSD-UC-ADMIN-001 §4.8 |
| **Stack** | React 18 + Vite 5 + MSW 2.3.5 (ADR-0013) |
| **Versión** | 0.1 (borrador inicial) |
| **Fecha** | 2026-07-11 |
| **Autor** | Ing. Guillermo Mamani Chambi |
| **Estado** | proposed |

---

## 0. Contexto del bug

### 0.1 Reporte original (2026-07-10)

> "el panel admin no está creando usuarios, el `configuracion.html` legacy
> está más funcional. Necesito pasar a la interfaz nueva ya."

### 0.2 Diagnóstico fase 0 (2026-07-11)

Se levantó `cd frontend-admin && npm run dev:msw` y se observó en la
consola del navegador que la tabla de usuarios **sí cargaba** (los 3
usuarios seed aparecían), pero al crear uno nuevo la request **fallaba
silenciosamente** y el user no aparecía en la lista.

Al revisar los logs del proceso Vite se encontró:

```
[vite] http proxy error: /api/admin/users/
AggregateError [ECONNREFUSED]:
    at internalConnectMultiple (node:net:1194:18)
```

### 0.3 Causa raíz (confirmada por código)

Dos bugs concurrentes:

**Bug A — `mockServiceWorker.js` ausente:**
- `App.tsx:90` registra el SW con `serviceWorker: { url: '/mockServiceWorker.js' }`
- `frontend-admin/public/mockServiceWorker.js` **no existe** (carpeta `public/` completa no existe)
- El `npx msw init` se ejecutó originalmente pero su output no se commiteó, o se borró en una limpieza posterior
- Resultado: el SW de MSW nunca se registra → las llamadas `/api/admin/*` no se mockean

**Bug B — Vite proxy fallback enmascara el problema:**
- `vite.config.ts:14-21` define un proxy que envía `/api/*` a `http://localhost:8001`
- Este proxy está activo **incluso cuando `VITE_USE_MSW=true`**
- Cuando MSW no intercepta (por Bug A), el fetch "escapa" al proxy → ECONNREFUSED (porque el backend Django no está corriendo en :8001)
- El desarrollador ve `[vite] http proxy error` en la consola del proceso Vite, pero el navegador solo ve un error genérico de fetch

### 0.4 Por qué los tests E2E pasaban

`tests/components/adminUsersPanel.spec.tsx` corre en **jsdom** sin SW
real. MSW en jsdom usa `setupServer` (Node), no `setupWorker` (browser).
El handler POST existe, el `resetMockData()` está correcto, y la
asercion `await screen.findByText('Test User')` funciona. **Los tests
no cubren el camino del SW en navegador**, porque no pueden (jsdom no
soporta SW de forma fiable).

Esto es un **gap de cobertura conocido** que se documenta y se cierra
en esta spec.

---

## 1. Caso de uso (Gherkin)

### UC-MSW-001 — Demo dev con MSW activo mockea todas las llamadas

```gherkin
Dado que el desarrollador ejecuta `npm run dev:msw` (VITE_USE_MSW=true)
Y que ningún backend está corriendo en localhost:8001
Cuando abre http://localhost:5173/ en Chrome
Entonces el service worker de MSW se registra (visible en DevTools → Application → Service Workers)
Y todas las requests a /api/admin/* son interceptadas por MSW (visible en Network tab con "from ServiceWorker")
Y ningún error "proxy error" o "ECONNREFUSED" aparece en la consola del proceso Vite
Y el panel de usuarios carga los 3 usuarios seed
Y al crear un nuevo usuario, este aparece en la tabla sin recargar
```

### UC-MSW-002 — Modo prod sin MSW usa el backend real

```gherkin
Dado que el desarrollador ejecuta `npm run dev` (VITE_USE_MSW no definido)
Y que el backend Django está corriendo en localhost:8001
Cuando abre http://localhost:5173/ en Chrome
Entonces NO hay service worker de MSW registrado
Y las requests a /api/admin/* van al backend real vía proxy de Vite
Y no hay error de proxy
```

### UC-MSW-003 — Test E2E detecta el escenario "MSW no se cargó"

```gherkin
Dado un test que simula el escenario "MSW setupWorker.start() falla"
Cuando el componente AdminUsersPanel intenta hacer una request
Entonces el test falla con un mensaje claro "MSW no se cargó, no se puede testear"
Y el test NO pasa silenciosamente
```

---

## 2. Cambios técnicos

### 2.1 Regenerar `mockServiceWorker.js`

Ejecutar `npx msw init frontend-admin/public/ --save` para generar el
archivo canónico de MSW. Esto produce ~200 líneas de código que
implementan el shim del Service Worker.

**Archivo afectado:** `frontend-admin/public/mockServiceWorker.js` (nuevo)

**Por qué `--save`:** actualiza `package.json` con `"msw.workerDirectory"`
para que regeneraciones futuras apunten al lugar correcto.

### 2.2 Hacer el proxy de Vite condicional

`vite.config.ts:14-21` define un proxy hardcoded. Cambiarlo para que
solo aplique cuando **no estamos en modo MSW**.

```typescript
// Antes
proxy: {
  '/api': { target: 'http://localhost:8001', changeOrigin: true },
},

// Después
proxy: (VITE_USE_MSW === 'true' || process.env.VITE_USE_MSW === 'true')
  ? {}
  : { '/api': { target: 'http://localhost:8001', changeOrigin: true } },
```

**Por qué:** Vite config se ejecuta en Node, no en el browser. Hay que
leer `process.env.VITE_USE_MSW` además de `import.meta.env` para tener
disponible el valor al momento de definir la config.

**Archivo afectado:** `frontend-admin/vite.config.ts`

### 2.3 Banner de error si MSW no se carga (defensa en profundidad)

`App.tsx:96-103` actualmente loguea el error a consola pero deja la app
bloqueada en "Inicializando mock service worker…". El usuario no
desarrollador no ve este mensaje (está en `main`, no en `console`).

Mejora: si `worker.start()` falla, mostrar un banner rojo en la propia
UI con un botón "Reintentar" + un link a la doc de troubleshooting.

```tsx
catch (err) {
  console.error('[MSW] worker.start() falló:', err);
  if (!cancelled) setMswError(err);
}
```

Y en el render:

```tsx
if (mswError) {
  return <MswBootstrapError error={mswError} onRetry={() => location.reload()} />;
}
```

**Archivo afectado:** `frontend-admin/src/App.tsx` (mod) +
`frontend-admin/src/admin/components/MswBootstrapError.tsx` (nuevo, ~40 LOC)

**Por qué:** cumple el principio de "no silent failure" y reduce el
tiempo de diagnóstico cuando alguien más levante la demo.

### 2.4 Test E2E que cubre el escenario "MSW falla"

`frontend-admin/tests/mswBootstrap.spec.ts` (nuevo) — 3 tests:

1. **Test 1:** Mockear `setupWorker(...).start()` para que rechace.
   Verificar que el componente `App` renderiza el banner de error.

2. **Test 2:** Verificar que `mockServiceWorker.js` existe en `public/`
   (test de "infraestructura como código" — si el archivo se borra, el
   test falla con mensaje claro).

3. **Test 3:** Verificar que `vite.config.ts` no tiene el proxy
   hardcoded cuando `VITE_USE_MSW=true`. Esto se hace parseando el
   archivo como string y buscando el patrón.

**Archivos afectados:**
- `frontend-admin/tests/mswBootstrap.spec.ts` (nuevo, ~80 LOC)
- `frontend-admin/tests/setup.ts` (verificar que jsdom pueda testear
  el bootstrap, posiblemente no requiera cambio)

---

## 3. Criterios de aceptación

| # | Criterio | Verificación |
|---|---|---|
| CA-1 | `frontend-admin/public/mockServiceWorker.js` existe y está commiteado | `ls frontend-admin/public/mockServiceWorker.js` |
| CA-2 | `package.json` tiene `"msw.workerDirectory": "public"` | `grep msw.workerDirectory package.json` |
| CA-3 | Con `npm run dev:msw`, ningún `[vite] http proxy error` aparece en consola | Manual: levantar y verificar |
| CA-4 | Con `npm run dev:msw`, el SW de MSW aparece en DevTools → Application | Manual: verificar |
| CA-5 | Con `npm run dev:msw`, crear un usuario nuevo funciona end-to-end | Manual: feature 11 cerrado |
| CA-6 | Con `npm run dev` (sin MSW), el proxy a :8001 sigue activo (no se rompió) | Manual: backend levantado, llamada OK |
| CA-7 | Cobertura RN-09 sigue ≥90% (statements/lines/functions) y ≥88% branches | `npx vitest run --coverage` |
| CA-8 | Test E2E nuevo pasa | `npx vitest run tests/mswBootstrap.spec.ts` |
| CA-9 | Banner de error visible en UI si MSW no se carga | Test E2E con mock de start() fallando |

---

## 4. Lo que NO se hace (fuera de alcance)

- **No se reescribe `App.tsx`** más allá del catch de error. La lógica
  de bootstrap ya está bien; solo se agrega un fallback visual.
- **No se introduce TanStack Query ni SWR** para caché de las llamadas.
  Esto es F8+ (ADR-0013).
- **No se cambia el handler MSW**. Los handlers están bien, el bug es
  de bootstrap.
- **No se mueve el SW a un subdominio ni se hace cross-origin.** MSW
  v2 funciona en el mismo origin por default y es lo correcto para dev.
- **No se commitea `backend-admin/.venv/`** ni `node_modules/`. (Ya
  están en .gitignore según la memoria.)

---

## 5. Riesgos y mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|:---:|:---:|---|
| `npx msw init` modifica package.json de forma inesperada | Baja | Bajo | Revisar diff antes de commitear; usar `--save` solo si confirma el cambio |
| El proxy condicional rompe el flujo "demo sin MSW con backend real" | Media | Alto | Test E2E #3 cubre este caso (verifica que el patrón existe en vite.config.ts) |
| El banner de error introduce regresión visual | Baja | Bajo | Test E2E + revisión visual manual |
| Otros tests E2E empiezan a fallar por el cambio de import.meta.env | Baja | Medio | Correr suite completa antes de commitear |
| `mockServiceWorker.js` se borra en un `.git clean` futuro | Baja | Alto | Agregar al README de la carpeta public/ un comentario "NO BORRAR" |

---

## 6. Trazabilidad

- **Trazabilidad ascendente:** FSD-UC-ADMIN-001 (panel admin funcional
  requiere que el demo funcione) → DD-ADMIN-001 → ADR-0011 (rol
  Administrador) → BRD §3.2 (Personal TI Institucional)
- **Trazabilidad descendente:** Esta spec genera `PR-IMPL-ADMIN-010` →
  implementa 2 cambios de código (vite.config.ts, App.tsx) + 1 archivo
  regenerado (mockServiceWorker.js) + 2 archivos nuevos (banner + test)
  → actualiza `PROMPT_MAPPING.md` con PM-MSW-BOOTSTRAP-01 → impacta
  `vitest.config.ts` si el nuevo test cambia los thresholds

---

## 7. Decisión que requiere el arquitecto

**¿Aprobás la sección 2.3 (banner de error visible en UI)?**

- **Sí (recomendado):** 5 min extra de implementación, gran mejora DX
- **No:** fix mínimo sin banner, el desarrollador tiene que abrir DevTools para diagnosticar
- **Diferido:** implementar solo el fix de bootstrap, abrir ADR-0015-robustez-mock-dev para el banner como mejora futura

---

## 8. Plan de implementación (PR-IMPL-ADMIN-010)

| # | Tarea | Esfuerzo | Bloqueante |
|---|---|:---:|---|
| T1 | `npx msw init frontend-admin/public/ --save` | 2 min | sí |
| T2 | Editar `vite.config.ts` para hacer el proxy condicional | 5 min | T1 |
| T3 | Agregar `MswBootstrapError.tsx` con banner | 15 min | T1 |
| T4 | Modificar `App.tsx` para usar el banner en el catch | 10 min | T3 |
| T5 | Crear `tests/mswBootstrap.spec.ts` con 3 tests | 30 min | T1, T2 |
| T6 | Correr suite completa + coverage, ajustar thresholds si baja | 15 min | T1-T5 |
| T7 | Commit + push a `feature/django-admin-stack` | 5 min | T6 |
| **Total** | | **~1.5h** | |
