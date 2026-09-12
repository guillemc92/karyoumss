# Entregable M8 — Suite E2E con localizadores robustos, generada y auditada

| | |
|---|---|
| **Equipo** | **BIOMED UMSS** — Ing. Guillermo Mamani Chambi (individual, G04) |
| **Producto** | Plataforma de Cariotipado Asistido por IA — `frontend-clinic` (núcleo clínico) |
| **Agente / IDE** | Claude Code (Opus 5) como IDE; **Planner y Generator como guiones con SDK** sobre `llama3.2:3b` local, para que los tokens sean exactos y no leídos de un panel |
| **Repositorio** | `github.com/guillemc92/karyoumss`, rama `feature/clinic-django-stack`, commit `38cb0bf` |
| **Carpetas** | `frontend-clinic/tests/` (auditado, agente, fixtures) · `frontend-clinic/specs/` |
| **Fecha** | 11 de septiembre de 2026 |

**Punto de partida:** el repositorio tenía **cero E2E**. Ni Playwright, ni configuración, ni specs. Las menciones a «E2E» de módulos anteriores eran verificaciones ad-hoc con un navegador, no una suite.

---

## 1 · Inventario de flujos — OBLIGATORIO

Las 10 rutas de `frontend-clinic/src/routes.tsx` cruzadas con los 7 casos de uso del FSD.

| # | Flujo | Ruta | Caso de uso | Test que lo cubre | Estado |
|---|---|---|---|---|---|
| 1 | Listado de muestras | `/clinic/samples` | UC-001 | `auditado/listado-muestras.spec.ts` | ✅ |
| 2 | Registro con metafases | `/clinic/samples/register` | UC-001 | — | ⚠ evals (§7) |
| 3 | Detalle de muestra | `/clinic/samples/:id` | UC-001 | `auditado/modo-degradado.spec.ts` | ✅ |
| 4 | Visor de cariotipo | `/clinic/samples/:id/karyotype` | UC-002 | `auditado/segregacion-analista-ajeno`, `modo-degradado` | ✅ |
| 5 | Semaforización por confianza | visor | UC-002 / RN-02 | — | ⚠ evals |
| 6 | XAI y corrección manual | visor | UC-003 | — | ⚠ evals |
| 7 | Bloqueo de validación por naranjas | visor | UC-004 / RN-01 | — | ⚠ evals |
| 8 | Segregación: analista ajeno → 403 | visor | UC-004 / RN-06 | `auditado/segregacion-analista-ajeno.spec.ts` | ✅ |
| 9 | Bandeja del supervisor | `/clinic/supervisor` | UC-005 / RN-08 | — | ⚠ evals |
| 10 | Modo degradado | registro + detalle | UC-007 / RN-07 | `auditado/modo-degradado.spec.ts` | ✅ |
| 11 | Consultas en lenguaje natural | `/clinic/consultas` | tool calling (M6) | `auditado/consulta-procedencia.spec.ts` | ✅ |
| 12 | Sesión sin token | `/clinic/samples` | transversal / RN-03 | `auditado/sesion-sin-token.spec.ts` | ✅ |
| 13 | Edición de muestra | `/clinic/samples/:id/edit` | UC-001 | — | ⚠ mismo formulario que 2 |
| 14 | Página de modo degradado | `/clinic/degraded` | UC-007 | — | informativa, sin regla detrás |

**8 de 14 flujos en verde.** Los 6 restantes van a evals con su motivo en §7.

---

## 2 · Que corra

```
npx playwright test --reporter=list
```

```
Running 5 tests using 1 worker
  ok 1 [chromium] › tests\auditado\consulta-procedencia.spec.ts:27:1 › una consulta declara por qué camino salió y de qué tabla viene (5.0s)
  ok 2 [chromium] › tests\auditado\listado-muestras.spec.ts:20:1 › el analista abre el listado y no recibe un aviso de acceso denegado (5.9s)
  ok 3 [chromium] › tests\auditado\modo-degradado.spec.ts:48:1 › con el pipeline de IA caído la muestra queda registrada y el visor lo dice sin fingir un cariotipo (8.5s)
  ok 4 [chromium] › tests\auditado\segregacion-analista-ajeno.spec.ts:50:1 › un analista que no es dueño del caso recibe el aviso de segregación, no un error genérico (5.7s)
  ok 5 [chromium] › tests\auditado\sesion-sin-token.spec.ts:24:1 › sin token en localStorage la aplicación no muestra datos de pacientes (1.8s)
  5 passed (30.0s)
```

**Tiempo total: 30,0 s.** Tres tests superan 3 s, y el motivo es el mismo: **corren contra el stack real**, no contra un mock. `modo-degradado` (8,5 s) registra una muestra por API contra backend-clinic y después abre dos pantallas; `listado` y `segregación` piden un JWT real a backend-admin antes de navegar. Es el precio de que el oráculo sea el sistema y no mi doble de él.

**Rojo controlado — los generados, tal como salieron:**

```
npx playwright test --config playwright.agente.config.ts
```

```
Error: Cannot find module '...\tests\fixtures\credenciales' imported from tests\agente\E2E-02.spec.ts
Error: Cannot find module '...\tests\fixtures\credenciales' imported from tests\agente\E2E-03.spec.ts
Error: Cannot find module '...\tests\fixtures\credenciales' imported from tests\agente\E2E-06.spec.ts
Error: Cannot find module '...\tests\fixtures\credenciales' imported from tests\agente\E2E-07.spec.ts
Error: Cannot find module '...\tests\fixtures\credenciales' imported from tests\agente\E2E-08.spec.ts
EXIT=1
```

**5 de los 9 generados ni cargan.** Importan un módulo que no existe, y Playwright los rechaza antes de ejecutar. Se corren aparte porque un fichero que no carga aborta la corrida completa — incluidos los cinco verdes.

> **Capturas:** ver §8. Terminal completa de las dos corridas y reporte HTML de Playwright, anotadas sobre la imagen.

---

## 3 · Que esté auditado

### Las cinco preguntas (textuales, del laboratorio)

| # | Pregunta | Si «no»… |
|---|---|---|
| 1 | ¿El localizador es **lo que ve una persona**? `getByRole`, `getByLabel`, `getByText`, `data-testid` a propósito. | Se reescribe. |
| 2 | ¿Hay alguna **espera fija**? | Se quita: `expect` ya espera. |
| 3 | ¿Verifica **lo que la interfaz promete**, o la redacción del modelo? | Se cambia por fuente/estado. |
| 4 | ¿Es **pequeño e independiente**? | Se parte. |
| 5 | ¿Los **datos son propios** del test? | Se aísla. |

### Tabla de auditoría — OBLIGATORIA

| Caso del plan | Archivo | Veredicto | Pregunta que falló | Qué se cambió |
|---|---|---|---|---|
| E2E-01 Registro | `tests/agente/E2E-01.spec.ts` | **descartado** | 1, 2, 4, 5 | Recorre 4 pantallas. `input[name="chn"]` es CSS. Cuatro `waitForSelector`. Usa el CHN como id de muestra. |
| E2E-02 Semaforización | `tests/agente/E2E-02.spec.ts` | **descartado** | 1, 3, 4, 5 | `locator('data-testid="x"')` sin corchetes. `locator().expect('color')` no existe. **Asegura que la UI muestra el texto de mi prompt**: `toContain('Confianza < 0,85')`. |
| E2E-03 Bloqueo naranjas | `tests/agente/E2E-03.spec.ts` | **descartado** | 1, 2, 5 | Importa `fixtures/credenciales`, inexistente. `chnUnico().id` sobre un string → `/samples/undefined/`. |
| E2E-04 Analista ajeno | `tests/agente/E2E-04.spec.ts` → `tests/auditado/segregacion-analista-ajeno.spec.ts` | **corregido** | 1, 3, 5 | Único con la intención correcta. CSS → `getByTestId`; `locator().expect()` → `expect().toBeVisible()`; anclas de otras pantallas → fuera; «hubo un error» → **el error es de permiso**. Exigió añadir un ancla al producto (§5). |
| E2E-05 Auditoría 5 % | — | **descartado en el plan** | 3 | Criterio circular («se ha realizado correctamente»). Exige `ANALYST_VALIDATED` con auditoría completa. |
| E2E-06 ISCN solo lectura | `tests/agente/E2E-06.spec.ts` | **descartado** | 1, 2, 5 | Mismo patrón: anclas ajenas, `waitForSelector`, `.id` sobre string. |
| E2E-07 Modo degradado | `tests/agente/E2E-07.spec.ts` → `tests/auditado/modo-degradado.spec.ts` | **descartado y reescrito** | 1, 2, 5 | Comprobaba el banner **sin provocar la condición** que lo produce. Reescrito: backend-ml caído de verdad, registro por API, `degraded: true`, `analyzed_count: 0`, y el visor no finge cariotipo. |
| E2E-08 Supervisor ve todo | `tests/agente/E2E-08.spec.ts` | **descartado** | 3, 4, 5 | Recorre 3 pantallas. Usa la misma credencial para analista y supervisor. |
| E2E-09 Listado | `tests/agente/E2E-09.spec.ts` → `tests/auditado/listado-muestras.spec.ts` | **descartado y reescrito** | 1, 2, 4, 5 | `input[name="search"]` es CSS y **ese campo no existe**. `expect` ni importado. 4 pantallas. |
| E2E-10 Sin token | `tests/agente/E2E-10.spec.ts` → `tests/auditado/sesion-sin-token.spec.ts` | **descartado y reescrito** | 3, 4 | Se titula «**sin** token» y **lo primero que hace es sembrar un token**. La pregunta 3 en su forma más pura. |
| E2E-11 Consulta procedencia | añadido → `tests/auditado/consulta-procedencia.spec.ts` | **aceptado (humano)** | — | Análogo directo del ejemplo del laboratorio: se verifica `tool-camino`, nunca la redacción. |

**Plan del Planner:** propuestos **8** · aceptados **1** · corregidos **6** · descartados **1** · añadidos por la auditoría **3**.
**Tests del Generator:** generados **9** · aceptados **0** · corregidos **1** · descartados **8**.

### El patrón del fallo, que es uno solo

Los nueve tests repiten el mismo error de fondo: **el modelo pega la lista entera de anclas que le di en el prompt, en todos los tests, sin mirar en qué pantalla vive cada una**. Comprueba `inbox-forbidden` (bandeja del supervisor) y `tool-fuente` (consultas) dentro de un test de registro de muestra. No es sintaxis: **no tiene modelo de la aplicación**. Le di una lista de anclas y la trató como una lista de la compra.

### Y un hallazgo en el plan, antes de generar

**5 de los 8 casos del Planner emparejaban el caso de uso *N* con la regla *RN-0N* por posición**, no por significado. Verificado con una comprobación explícita:

```
E2E-01 → RN-01   E2E-02 → RN-02   E2E-03 → RN-03   E2E-04 → RN-04   E2E-07 → RN-07
```

Le di dos listas y las cerró con cremallera. Por eso el Generator lee `plan_auditado.json` y no `plan.json`: generar sobre el plan crudo habría producido tests sintácticamente impecables que comprueban **la regla equivocada**, en verde.

---

## 4 · Que esté medido

| | Entrada | Salida | Tiempo |
|---|---:|---:|---:|
| **Planner** (8 casos) | **913** | **894** | 732 s |
| **Generator, promedio por test** (9 tests) | **698** | **379** | 420 s |
| Generator, total | 6 284 | 3 415 | 63 min |

Detalle por test en `specs/REGISTRO_TOKENS.csv`. Los tokens son los que devuelve el SDK, no una estimación.

---

## 5 · Anclas agregadas al producto

| Ancla | Pantalla | Por qué hizo falta |
|---|---|---|
| **`data-testid="karyo-forbidden"`** (añadida) | Visor de cariotipo `/samples/:id/karyotype` | Un 403 se pintaba **igual que cualquier otro fallo** («No se pudo cargar»). RN-06 tiene que **verse**: el analista no sabía si el caso no era suyo o si el servidor estaba caído. Con el ancla, el E2E afirma el **motivo** y no solo «hubo un error». |
| `<label htmlFor>` + `id` en 6 campos, `data-testid` en el input de fichero (identificada, **no añadida**) | Formulario de registro `/samples/register` | Los `<label>` tienen `className="form-label"` y **ningún `htmlFor`**: son decorativos. `getByLabel('CHN')` no encuentra nada. Conducir el formulario exigiría selectores CSS, que la pregunta 1 prohíbe. Por eso los flujos 2 y 13 van a evals. |

Línea base medida antes de empezar: **40 `data-testid`** en el visor y sus paneles, **0** en registro, listado, detalle y formulario.

---

## 6 · Que sea honesto

### Los tres defectos del test de calibración, en mis palabras

`generado-politica.spec.ts` del laboratorio está **verde** y tiene tres defectos:

1. **`#mensajes li:nth-child(2)`** — depende de la posición y de un id de CSS. Basta un saludo de bienvenida arriba para que apunte al mensaje equivocado.
2. **`waitForTimeout(2000)`** — suma dos segundos a cada corrida y no garantiza nada: si la respuesta tarda 2,1 s, falla igual. `expect` ya espera.
3. **`toHaveText` con la redacción completa** — asegura la frase entera que devuelve el modelo. Con reglas de demo pasa; con el modelo real se pone rojo cada vez que lo redacte distinto.

**Por qué estaba verde:** porque los tres son defectos sobre *cómo* comprueba, no sobre *qué*. Con datos deterministas y un DOM que no ha cambiado, las tres afirmaciones se cumplen. El verde no dice que el test sea bueno: dice que hoy, con estos datos, no se rompió.

### Lo que el stack real me corrigió a mí

Elegí correr contra backend-admin + backend-clinic + Vite reales, sin MSW, porque el proyecto ya tiene la cicatriz: el bug de creación de usuarios del 10/07 tuvo como causa raíz el service worker ausente. En la primera hora el stack me corrigió **cinco suposiciones** que ningún mock habría tocado:

| Supuse | Era |
|---|---|
| el login pide `username` | pide **`email`** — `{"email":["Este campo es requerido."]}` |
| las credenciales del seed eran `testpass123` | no; las fijé desde Django |
| el front corre en 5173 | **5174** (`vite.config.ts`) |
| el proxy apunta al clínico en 8000 | **8002** |
| `tool-camino` muestra `KEYWORD` | muestra **«Sin IA — palabra del catálogo»**: afirmé el código, no lo que ve una persona |

La quinta es la pregunta 1 aplicada a mi propia aserción. El producto estaba bien; el test, mal.

---

## 7 · Lo que no se pudo probar en E2E, y por qué (va a evals)

| Flujo | Motivo | A dónde va |
|---|---|---|
| Semaforización por confianza (RN-02) | Exige **backend-ml con el modelo de 42 MB** produciendo un cariotipo real: ~32 s por metafase y un resultado que depende del modelo. E2E no puede fijar que un cromosoma concreto salga naranja. | evals: `eval_umbral_semaforo.py` ya lo mide sobre 443 cromosomas |
| XAI y corrección manual (UC-003) | Ídem: sin cariotipo real no hay cromosoma que corregir. | evals + tests de contrato (`test_contrato_errores_endpoints.py`, 82 tests) |
| Bloqueo por naranjas (RN-01) | Ídem. | tests de servicio (`test_karyotype_p2.py`) |
| Auditoría del 5 % (RN-08) | Exige un caso en `ANALYST_VALIDATED` con auditoría completa: montar ese estado desde la UI son ~15 acciones sobre un cariotipo real. | tests de servicio (`test_supervisor_s1.py`) |
| Registro y edición por la interfaz | El formulario **no se puede conducir por lo que ve una persona**: `<label>` sin `htmlFor`. Se probó por API contra el mismo backend. | anclas pendientes (§5) |
| Firma MFA del supervisor (UC-006) | Exige un TOTP real de backend-admin: el test tendría que conocer el secreto, y eso convierte el segundo factor en un primer factor. | tests de servicio (`test_supervisor_s2.py`) + contrato (423/401/503) |

El patrón se repite: lo que no entra en E2E es **lo que depende del modelo o de un secreto**. Ambos están cubiertos donde se pueden fijar — 868 tests unit/integración/contrato en verde en el clínico (M7).

---

## 8 · Capturas

*Las capturas van anotadas sobre la propia imagen (flecha o recuadro), no descritas. Lo que no esté capturado se considera no ejecutado.*

**Captura 1 — terminal, suite completa en verde.** Comando `npx playwright test --reporter=list`. Anotar: recuadro sobre `5 passed (30.0s)`; flecha sobre el nombre de cada uno de los 5 tests.

**Captura 2 — reporte HTML de Playwright, misma corrida.** `npx playwright show-report`. Anotar: recuadro sobre la lista de los 5 tests con su tick verde y su duración.

**Captura 3 — terminal, generados en rojo controlado.** Comando `npx playwright test --config playwright.agente.config.ts`. Anotar: flecha sobre `Cannot find module '.../fixtures/credenciales'` y nota: *«5 de 9 no cargan: importan un módulo que no existe; se conservan sin tocar como evidencia»*.

---

## 9 · Qué queda en el repositorio

| Ruta | Qué es |
|---|---|
| `frontend-clinic/tests/auditado/*.spec.ts` | los 5 tests aceptados, con las cinco preguntas resueltas por diseño en cada cabecera |
| `frontend-clinic/tests/agente/*.spec.ts` | los 9 generados, **intactos**: la evidencia de la auditoría |
| `frontend-clinic/tests/fixtures/sesion.ts` | JWT real de backend-admin + CHN único por test |
| `frontend-clinic/specs/plan_nucleo_clinico.md` | el plan con la revisión marcada `AUDITORÍA` |
| `frontend-clinic/specs/AUDITORIA_E2E.md` | la tabla de las cinco preguntas, test por test |
| `frontend-clinic/specs/REGISTRO_TOKENS.csv` | tokens por agente y por test |
| `scripts/e2e_planner.py` · `e2e_generator.py` · `e2e_auditar.py` | los agentes; reportan tokens del SDK |
| `docs/M8_E2E/plan_crudo.txt` · `salida_generator/` | lo que devolvió el modelo, sin tocar |
