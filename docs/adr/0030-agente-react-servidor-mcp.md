---
id: ADR-0030
title: Un agente ReAct con guardrails, y las herramientas publicadas por MCP
date: 2026-08-16
status: accepted
related: [ADR-0029, ADR-0024]
---

# ADR-0030: Agente ReAct + servidor MCP

## Contexto

Los niveles anteriores deciden **una** cosa y responden: el tool calling elige
una herramienta, el RAG recupera unos fragmentos. Hay preguntas que ninguno
resuelve solo:

> «¿Hay cromosomas pendientes de revisar, y por qué hay que revisarlos?»

La primera mitad es estado (una herramienta), la segunda es una regla (el RAG).
Y el orden **no está programado en ninguna parte**: depende de la pregunta.

Al mismo tiempo, las herramientas viven dentro del proceso. Mientras el único
cliente sea nuestro agente eso funciona; en cuanto aparece otro —un IDE, un
agente de otro equipo— cada uno tendría que importar Django, sus settings y su
base de datos.

## Decisión

### D1 — UN agente con varias acciones, no varios agentes

Se implementa **un** agente con seis acciones: cuatro consultas de estado, el
RAG documental (ADR-0029) y una escritura con guardrail.

La alternativa —un agente por escenario— multiplica el coste y la superficie de
fallo sin resolver nada que un agente con más acciones no resuelva. La
orquestación **es** el encadenado de acciones, no la coordinación de agentes.

### D2 — El bucle no sabe qué herramientas existen

`ejecutar_agente(pregunta, schemas, ejecutar, instrucciones, max_pasos)`. El
bucle recibe los *schemas* y un callback, y le da igual de dónde vengan:

```
local  : schemas=agente_acciones.schemas()   ejecutar=agente_acciones.ejecutar
vía MCP: schemas=conexion.descubrir_tools()  ejecutar=conexion.ejecutar_tool
```

Los *schemas* de las consultas se **derivan** del `CATALOGO` que ya existía: una
quinta herramienta la vería el agente sin tocar nada. El servidor MCP delega en
las mismas funciones. **Una definición, tres transportes** — HTTP, agente local
y MCP.

### D3 — Tres guardrails no negociables

**Tope de pasos** (`MAX_PASOS = 6`). Un agente que no converge repite la misma
herramienta indefinidamente, y aquí cada paso cuesta minutos de CPU.

**Temperatura 0.** Enrutar y decidir acciones es determinista, no creativo.

**Traza por paso** con acción, observación y tokens. No es depuración: es lo
único que permite auditar por qué el agente dijo lo que dijo, y sin ella el
fallo de la sección «Consecuencias» habría pasado por respuesta fundamentada.

### D4 — El guardrail de escritura vive EN la herramienta

No en el bucle. Si viviera en el bucle solo protegería a *nuestro* agente; un
servidor MCP existe precisamente para que lo invoquen clientes ajenos, y ninguno
de ellos conoce RN-01. Puesto en la herramienta, la política viaja con ella.

Verificado llamando `preparar_validacion_de_caso(confirmado=true)` **desde el
cliente MCP externo**: devuelve la negativa, no ejecuta.

### D5 — El agente NUNCA valida un caso, ni con `confirmado=true`

Es más estricto que el patrón del material de clase, donde la confirmación sí
ejecuta la acción. La diferencia es de dominio:

> **RN-01:** Ningún informe puede emitirse sin (a) validación manual del
> analista de TODOS los cromosomas naranjas (b) firma digital del supervisor
> (MFA obligatorio).

Y RN-06 exige que Supervisor y Analista no sean el mismo usuario. Un proceso
automático no cumple ninguna de las dos: no es un analista identificado ni puede
aportar un segundo factor. Cancelar una compra es reversible y lo autoriza su
dueño; validar un cariotipo es un acto clínico que firma un profesional.

Lo que el agente **sí** hace es preparar el trabajo: devuelve el estado del
caso, cuántos naranjas lo bloquean y qué regla aplica, para que la persona
decida con la información delante en vez de ir a buscarla.

### D6 — La sesión MCP se mantiene abierta durante todo el bucle

El ejemplo de referencia abre una sesión por llamada. Aquí cada apertura relanza
el servidor, que arranca Django entero: varios segundos por acción, y el agente
hace varias. La sesión vive en un hilo con su propio bucle de eventos, cerrada
por gestor de contexto.

## Consecuencias

**Funciona, verificado:**

| | |
|---|---|
| `POST /agente` | 200, 4 pasos, 1.853/43 tokens, traza completa |
| Multipaso | 6 pasos encadenando herramienta + RAG |
| Descubrimiento MCP | 6 herramientas por JSON-RPC, sin importar Django |
| Guardrail vía MCP | `confirmado=true` desde cliente externo → no ejecuta |

**El fallo más grave, y por qué la traza es un guardrail.** Antes de reforzar las
instrucciones, ante la pregunta multipaso el modelo hacía **una** consulta y se
inventaba la segunda mitad: dio un umbral del **90%** —el real es 85%, y está en
el corpus a una llamada de distancia— encabezado con *«según la herramienta de
consulta»*.

Inventar es grave; **atribuirlo a una fuente que no lo dijo, más**. Y solo se ve
mirando la traza: sin ella, la respuesta parece fundamentada. Corregido con
instrucciones explícitas; ahora encadena.

**Un componente medido aislado no queda validado dentro del agente.** El RAG
mide 89% con preguntas escritas por una persona (ADR-0029). Dentro del bucle las
escribe el modelo: reformuló una consulta como «por qué revisar cromosomas
pendientes», recuperó un ADR sobre similitud vectorial y construyó una respuesta
sin sentido. Queda pendiente medir el RAG con consultas generadas por el agente.

**Latencia — el coste real del nivel 4:**

| | |
|---|---|
| Consulta simple (4 pasos) | ~300 s |
| Multipaso (6 pasos) | ~843 s |

Cada paso reenvía todo el historial y todos los *schemas*. Con un 3B en CPU el
nivel 4 **no es utilizable de forma interactiva**. No invalida el diseño, pero
determina dónde aplicarlo: procesos asíncronos, no una caja de búsqueda.

**Cuándo NO usar el agente.** Una pregunta de un solo dato la resuelve el tool
calling en 30 ms; una de documentación, el RAG. El agente se justifica con
ramificación real —dos fuentes distintas y un orden que depende de la
pregunta— y se paga en latencia y superficie de fallo.

## Alternativas descartadas

| Alternativa | Por qué no |
|---|---|
| Un agente por escenario | Multiplica coste y superficie de fallo sin resolver más |
| Guardrail en el bucle | Solo protegería a nuestro agente, no a otros clientes MCP |
| Permitir `confirmado=true` real | Violaría RN-01 y RN-06: sin identidad ni segundo factor |
| Sesión MCP por llamada | Relanza Django en cada acción |
| LangGraph (nivel 5) | Resuelve persistencia de memoria; no se necesita todavía |

## Implementación

`apps/samples/agente.py` (bucle), `agente_acciones.py` (las seis acciones),
`agente_escritura.py` (guardrail), `mcp_conexion.py` (puente),
`servidor_mcp.py` y `cliente_mcp.py`, `AgenteView` → `POST /api/clinic/agente/`,
comando `demo_agente [--mcp]`.
