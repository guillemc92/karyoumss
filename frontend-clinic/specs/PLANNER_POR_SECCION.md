# Planner por sección — auditoría de cada plan

Corrida del 16/09/2026, `scripts/e2e_planner.py --seccion <s>`, modelo `llama3.2:3b`.
La consigna dice *«sección por sección, nunca sobre toda la app de una vez»*; la
primera corrida (11/09) fue sobre toda la app y esta la sustituye. Los planes
crudos y auditados están en `docs/M8_E2E/secciones/`.

## Totales

| Sección | Pantallas | Propuestos | Aceptados sin tocar | Corregidos | Descartados | Añadidos por auditoría | Tokens in / out | Tiempo |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| muestras | listado, registro, detalle, edición | 4 | 0 | 3 | 1 | 2 | 705 / 333 | 356 s |
| visor | cariotipo | 4 | 0 | 3 | 1 | 0 | 755 / 472 | 370 s |
| supervisor | bandeja | 4 | 0 | 1 | 3 | 1 | 676 / 456 | 352 s |
| consultas | consultas, degradado, inicio | 3 | 0 | 2 | 1 | 1 | 635 / 251 | 244 s |
| **Total** | | **15** | **0** | **9** | **6** | **4** | **2 771 / 1 512** | 22 min |

Comparado con la corrida única del 11/09 (8 casos, 913 / 894 tokens, 732 s): por
sección el modelo propone casi el doble de casos con **menos tokens de entrada
por caso** y en un tercio del tiempo por llamada. Pero **ningún caso salió
aceptable sin tocar**, contra 1 de 8 en la corrida única.

## Por sección: qué propuso y qué se cambió

### muestras (4 pantallas → 4 casos, todos en `/register`)

| Caso | Veredicto | Pregunta / motivo | Qué se cambió |
|---|---|---|---|
| MUE-01 registro happy | corregido | criterio no observable («datos cifrados») | → la persona ve el CHN y no ve el nombre del paciente (RN-03) |
| MUE-02 registro error | **descartado** | afirma la violación de RN-03 como éxito | — |
| MUE-03 campo vacío | corregido | «se registra correctamente con un campo vacío» es lo contrario de un límite | → el formulario no envía y muestra el aviso; sin test (label sin `htmlFor`) |
| MUE-04 ve solo sus muestras | corregido | ruta equivocada (`/register`) | → `/clinic/samples`, `listado-muestras.spec.ts` |
| MUE-05 IA caída | **añadido** | RN-07 estaba en el contexto y no lo usó | `modo-degradado.spec.ts` |
| MUE-06 sin token | **añadido** | el error más básico de la sección | `sesion-sin-token.spec.ts` |

### visor (1 pantalla → 4 casos)

| Caso | Veredicto | Pregunta / motivo | Qué se cambió |
|---|---|---|---|
| VIS-01 UC-002 ↔ RN-01 | corregido | cremallera; RN-01 es un bloqueo, no un happy | → Validar deshabilitado con naranjas; evals (modelo) |
| VIS-02 UC-003 ↔ RN-02 | corregido | cremallera; «contiene naranjas» no dice cuál ni por qué | → 0,40 naranja y 0,95 verde; evals (modelo) |
| VIS-03 ISCN «no es de solo lectura» | **descartado** | afirma la violación; no hay control de edición en la UI | contrato + servicio |
| VIS-04 «puede firmar como supervisor» | corregido | afirma la violación | → aviso de segregación; `segregacion-analista-ajeno.spec.ts` |

**La cremallera vuelve por sección**: caso 1→RN-01, 2→RN-02, 3→RN-04, 4→RN-06, el
orden exacto de la lista de reglas. Acotar el contexto no la quita; la quita la
auditoría.

### supervisor (1 pantalla → 4 casos)

| Caso | Veredicto | Pregunta / motivo | Qué se cambió |
|---|---|---|---|
| SUP-01 sorteo 5 % | corregido | oráculo cruzado (RN-04 en vez de RN-08); criterio circular | → bloque de auditoría visible; evals (`ANALYST_VALIDATED` real) |
| SUP-02 reporte ISCN | **descartado** | oráculo cruzado (RN-06); circular; exige el secreto TOTP | servicio + contrato |
| SUP-03 «no se genera correctamente» | **descartado** | negación del caso 1 sin decir qué falla | — |
| SUP-04 «error en la base de datos» | **descartado** | inventa una condición que el producto no tiene | — |
| SUP-05 analista en la bandeja | **añadido** | el caso de error obvio, ausente | generado → ver tabla de auditoría |

### consultas (3 pantallas → 3 casos)

| Caso | Veredicto | Pregunta / motivo | Qué se cambió |
|---|---|---|---|
| CON-01 «muestra datos cifrados» | corregido | la pantalla no muestra pacientes; el oráculo es la procedencia | → `tool-camino` + fuente; `consulta-procedencia.spec.ts` |
| CON-02 «entra en modo manual» | corregido | describe el estado sin provocar la causa | → backend-ml caído de verdad; `modo-degradado.spec.ts` |
| CON-03 «error al acceder a datos sensibles» | **descartado** | inventa un flujo que no existe para justificar RN-03 | — |
| CON-04 fuera de alcance | **añadido** | el único límite real de la pantalla | generado → ver tabla de auditoría |

## Lo que se aprende de correrlo por sección

1. **Más casos, mismo patrón.** 15 propuestos contra 8, pero los tres defectos son
   los mismos: la regla por posición, el criterio que afirma la violación, y
   el criterio circular («se genera correctamente»).
2. **El Planner no propone los casos de error obvios** (sin token, analista en la
   bandeja del supervisor, IA caída) aunque la regla esté en su contexto. Los
   cuatro casos añadidos por auditoría son todos de ese tipo.
3. **Lo que no está en el FSD, el modelo lo inventa.** La pantalla de consultas
   (tool calling, M6) no tiene caso de uso en el FSD y el Planner la llenó con
   RN-03. El contexto que se le da es el techo de lo que puede planificar.
