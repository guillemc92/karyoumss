# Auditoría de los tests E2E generados — las cinco preguntas

Se aplica **test por test**. Un test se acepta solo si responde SÍ a las cinco.

| # | Pregunta |
|---|---|
| 1 | **¿El localizador es lo que ve una persona?** `getByRole`, `getByLabel`, `getByText` o un `data-testid` puesto a propósito. Nada de CSS, ids de estilo, `nth-child`, XPath. |
| 2 | **¿Hay alguna espera fija?** `waitForTimeout`, `sleep`, `waitForSelector`. |
| 3 | **¿Verifica lo que la interfaz promete, o la redacción del modelo?** |
| 4 | **¿Es pequeño e independiente?** Un comportamiento por test. |
| 5 | **¿Los datos son propios del test?** |

---

## Tabla de auditoría

| Caso del plan | Archivo | Veredicto | Pregunta que falló | Qué se cambió |
|---|---|---|---|---|
| E2E-01 Registro de muestra | `tests/agente/E2E-01.spec.ts` | **descartado** | 1, 2, 4, 5 | Recorre 4 pantallas (registro → visor → bandeja → consultas). `input[name="chn"]` es CSS. 4 `waitForSelector`. Navega a `/samples/{chn}/karyotype` usando el **CHN como si fuera el id**. Reescrito desde cero como `E2E-01-registro.spec.ts`. |
| E2E-02 Semaforización | `tests/agente/E2E-02.spec.ts` | **descartado** | 1, 3, 4, 5 | `page.locator('data-testid="x"')` sin corchetes: no es un selector válido. `locator().expect('color')` no existe en Playwright. Asegura que la UI muestra **el texto de mi propio prompt**: `toContain('Confianza < 0,85')`. Mezcla tres pantallas. |
| E2E-03 Bloqueo por naranjas | `tests/agente/E2E-03.spec.ts` | **descartado** | 1, 2, 5 | Importa de `'../fixtures/credenciales'`, que no existe. `chnUnico().id` sobre un string → navega a `/samples/undefined/`. `waitForSelector` con selector inválido. |
| E2E-04 Analista ajeno (403) | `tests/agente/E2E-04.spec.ts` | **corregido** | 1, 3 | Es el **único con la intención correcta**: comprueba el 403 del analista ajeno. Se cambiaron los selectores CSS por `getByTestId` y se añadió el oráculo real (RN-06) en vez de comprobar solo que la página carga. |
| E2E-05 Auditoría del 5 % | — | **descartado en el plan** | — | No se generó. El criterio del Planner era circular («se ha realizado correctamente») y el flujo exige un caso en `ANALYST_VALIDATED` con auditoría completa, un estado que E2E no monta barato. Va a evals. |
| E2E-06 ISCN de solo lectura | `tests/agente/E2E-06.spec.ts` | **descartado** | 1, 2, 5 | Mismo patrón: anclas de otras pantallas, `waitForSelector`, `.id` sobre string. |
| E2E-07 Modo degradado | `tests/agente/E2E-07.spec.ts` | **descartado** | 1, 2, 5 | Ídem. Además el modo degradado exige tirar backend-ml, que el test no hace: comprueba el banner sin provocar la condición que lo produce. |
| E2E-08 Supervisor ve todo | `tests/agente/E2E-08.spec.ts` | **descartado** | 3, 4, 5 | Recorre 3 pantallas. No distingue al supervisor del analista: usa la misma credencial para ambos. |
| E2E-09 Listado | `tests/agente/E2E-09.spec.ts` | **descartado** | 1, 2, 4, 5 | `input[name="search"]` es CSS y **ese campo no existe** en la pantalla. `expect` no está ni importado. Recorre 4 pantallas. |
| E2E-10 Sesión expirada | `tests/agente/E2E-10.spec.ts` | **descartado** | 3, 4 | El más instructivo: se titula «**sin** token» y **lo primero que hace es sembrar un token**. Falla la pregunta 3 en su forma más pura — no verifica lo que promete. |

### Totales

| | Propuestos | Aceptados | Corregidos | Descartados |
|---|---:|---:|---:|---:|
| **Casos del Planner** | 8 | 1 | 6 | 1 |
| **Tests del Generator** | 9 | 0 | 1 | 8 |

A los 8 casos del Planner la auditoría **añadió 2** (E2E-09 listado y E2E-10 sesión),
porque el Planner no propuso ninguno para la pantalla de entrada ni para la
frontera de sesión. El plan aprobado quedó en 10 casos, 9 generables.

---

## El patrón del fallo, que es uno solo

Los nueve tests repiten el mismo error de fondo: **el modelo pega la lista
entera de anclas que le di en el prompt, en todos los tests, sin mirar en qué
pantalla vive cada una**. Comprueba `inbox-forbidden` (bandeja del supervisor) y
`tool-fuente` (consultas) dentro de un test de registro de muestra.

No es un fallo de sintaxis: es que **no tiene modelo de la aplicación**. Le di
una lista de anclas y la trató como una lista de la compra.

De ahí salen tres de las cinco preguntas de golpe: recorre media aplicación
(pregunta 4), usa anclas de pantallas donde no existen (pregunta 1) y termina
comprobando cosas que no tienen que ver con lo que el test dice probar
(pregunta 3).

## Los tres defectos del test de calibración, en mis palabras

El laboratorio trae `generado-politica.spec.ts` **en verde** con tres defectos:

1. **`#mensajes li:nth-child(2)`** — depende de la posición del mensaje y de un
   id de CSS. Basta añadir un saludo de bienvenida arriba para que el test
   apunte al mensaje equivocado y siga pasando o falle sin que nada esté roto.
2. **`waitForTimeout(2000)`** — suma dos segundos a cada corrida y no garantiza
   nada: si la respuesta tarda 2,1 s falla igual. `expect` ya espera.
3. **`toHaveText` con la redacción completa** — asegura la frase entera que
   devuelve el modelo. Con las reglas de demo pasa; con el modelo real se pone
   rojo cada vez que lo redacte distinto, sin que nada esté mal.

**Por qué estaba verde:** porque los tres defectos son sobre *cómo* comprueba,
no sobre *qué* comprueba. Con datos de demo deterministas y un DOM que no ha
cambiado, las tres afirmaciones se cumplen. El verde no dice que el test sea
bueno: dice que hoy, con estos datos, no se rompió.
