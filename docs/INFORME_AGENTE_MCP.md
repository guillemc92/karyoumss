# Informe de progreso — Agente + MCP (Nivel 4)

**Módulo 6 · Día 6** · Entrega del viernes 14 de agosto de 2026

| | |
|---|---|
| Equipo | Individual — Ing. Guillermo Mamani Chambi |
| Proyecto | BIOMED UMSS — Plataforma de Cariotipado Inteligente |
| Repositorio | `https://github.com/guillemc92/karyoumss` |
| Rama | `feature/clinic-django-stack` |
| Modelo | `llama3.2:3b` — versión fija, nunca `latest` |
| Proveedor | Ollama local (`http://localhost:11434/v1`) |
| Embeddings | `nomic-embed-text` local |

---

## 1. Definition of Done

| Requisito | Estado | Evidencia |
|---|---|---|
| Bucle ReAct con tope de pasos | ✅ | `apps/samples/agente.py`, `MAX_PASOS = 6` |
| Multipaso encadenando ≥2 herramientas | ✅ | traza de 6 pasos, §3.2 |
| 4 tools en servidor MCP propio | ✅ **6** | `servidor_mcp.py` |
| Cliente que descubre por protocolo, sin import | ✅ | `cliente_mcp.py` |
| Escritura solo con confirmación explícita | ✅ | `agente_escritura.py`, §4 |
| `POST /agente` con respuesta + traza | ✅ | `AgenteView`, §3.1 |

**Estado de la escalera:** niveles 0 a 4 implementados y medidos. El nivel 3
(RAG) se cerró esta misma semana; este informe cubre el 4.

---

## 2. Qué se construyó

```
apps/samples/agente.py            bucle ReAct: pensamiento → acción → observación
apps/samples/agente_acciones.py   6 acciones: 4 consultas + RAG + 1 escritura
apps/samples/agente_escritura.py  el guardrail de confirmación
apps/samples/mcp_conexion.py      puente: descubrir por protocolo (fase 5)
servidor_mcp.py                   publica las 6 por stdio/JSON-RPC
cliente_mcp.py                    las descubre y llama sin importar Django
apps/samples/views.py → AgenteView   POST /agente
```

**El bucle no sabe qué herramientas existen.** Recibe `(schemas, ejecutar)`. Por
eso el mismo bucle corre con herramientas importadas o descubiertas por MCP:

```python
local  : schemas=agente_acciones.schemas()   ejecutar=agente_acciones.ejecutar
vía MCP: schemas=conexion.descubrir_tools()  ejecutar=conexion.ejecutar_tool
```

Y los *schemas* de las consultas se **derivan** del catálogo que ya existía
(`tools.py`, del Día 4): una quinta herramienta la vería el agente sin tocar
nada. El servidor MCP delega en las mismas funciones. **Una definición, tres
transportes** — HTTP, agente local y MCP.

---

## 3. Recorrido del sistema — qué pasa cuando el usuario pregunta

> Esta sección existe porque explicar el código importa tanto como escribirlo.
> Se recorre el camino completo desde que alguien escribe una pregunta en
> pantalla hasta que ve la respuesta, señalando qué archivo hace cada cosa.

### 3.1 La pantalla que lista las herramientas

El analista entra en `/clinic/consultas` (`ToolQueryPage.tsx`). Lo primero que
ve es **la lista de lo que el sistema sabe hacer**, en lenguaje llano:

```
cromosomas_para_revision     Lista los cromosomas marcados en naranja…
casos_pendientes_firma       Lista los casos que el analista ya validó…
casos_reportados             Lista los casos ya cerrados y firmados…
```

Esa lista **no está escrita en el frontend**. El hook `useToolCatalogo` pide
`GET /api/clinic/tools/query/`, que responde con el catálogo publicado por
`tools.py`. Cada herramienta lleva su `description`, y **esa descripción es a la
vez lo que lee el usuario y lo que lee el modelo** para decidir si la usa. Por
eso escribir descripciones es escribir código: si una descripción es ambigua,
se equivocan los dos.

Si mañana se añade una séptima herramienta al catálogo, aparece sola en la
pantalla y en las opciones del modelo. Nadie toca el frontend.

### 3.2 La pregunta baja al backend y se decide el camino

El usuario escribe «¿qué cromosomas están naranjas?» y el frontend hace
`POST /api/clinic/tools/query/`. En `tool_router.py` se decide **cómo** se va a
resolver, y el camino elegido se devuelve al frontend para que se vea en
pantalla:

```
KEYWORD    una palabra del catálogo coincide  → se ejecuta SIN modelo
LLM        no coincide nada                   → el modelo elige la herramienta
RAG        es una pregunta de documentación   → va al corpus
SIN_MATCH  nadie puede responder              → se dice que no se sabe
```

El modelo **solo elige un nombre**. No redacta la respuesta ni toca los datos:
las filas salen de una consulta a PostgreSQL en `tools.py`. Por eso la pantalla
muestra siempre `tool` y `source` — la tabla real de la que salió el dato. Un
usuario puede distinguir un dato consultado de uno inventado, que es justamente
lo que esta arquitectura hace imposible.

### 3.3 Cuando hace falta encadenar, entra el agente

Las preguntas de un solo paso terminan ahí. Otras no:

> «¿Hay cromosomas pendientes de revisar, y por qué hay que revisarlos?»

La primera mitad es estado (una herramienta), la segunda es una regla (el
corpus). Ese caso va a `POST /api/clinic/agente/`, y `agente.py` abre el bucle
**pensar → actuar → observar** hasta que el modelo responde con texto en vez de
pedir otra herramienta, o hasta agotar `MAX_PASOS`.

El bucle **no sabe qué herramientas existen**. Recibe dos cosas: la lista de
`schemas` y una función `ejecutar`. Ese desacople es lo que permite el paso
siguiente sin reescribir nada.

### 3.4 La comunicación con el MCP, paso a paso

Si la petición lleva `"mcp": true`, las herramientas **ya no se importan: se
descubren hablando el protocolo**. Esto es lo que ocurre por dentro:

```
1. mcp_conexion.py lanza `python servidor_mcp.py` como PROCESO HIJO
   No hay puerto ni red: se hablan por stdin/stdout (JSON-RPC 2.0).

2. initialize          handshake de la sesión

3. tools/list          el servidor devuelve las 6 herramientas con su
                       nombre, su descripción y su JSON Schema

4. se traduce el schema al formato que espera el SDK del modelo:
   {"type": "function", "function": {name, description, parameters}}
   Es el MISMO JSON Schema con otro envoltorio.

5. tools/call          cuando el modelo pide una herramienta, se invoca
                       por protocolo y la observación vuelve al bucle
```

En `servidor_mcp.py` publicar una herramienta es **un decorador**: `@mcp.tool()`
sobre una función que delega en el catálogo que ya existía. La lógica no se
duplica — si hay un fallo, se arregla en un solo sitio.

Y el bucle del agente es **exactamente el mismo** en los dos modos:

```
sin MCP:  schemas=agente_acciones.schemas()   ejecutar=agente_acciones.ejecutar
con MCP:  schemas=conexion.descubrir_tools()  ejecutar=conexion.ejecutar_tool
```

Cambia el enchufe, no la lógica. `cliente_mcp.py` lo demuestra: descubre y
ejecuta las 6 herramientas **sin importar Django ni el catálogo**, hablando
solo el protocolo.

### 3.5 Qué ve el usuario al final

La respuesta vuelve con la **traza completa**: cada paso con su tipo —acción,
observación, respuesta— y el consumo de tokens. No es información de
depuración: es lo que permite comprobar si el agente encadenó de verdad o
rellenó el hueco inventando. Sin ella, un agente es un oráculo.

---

## 4. Traza — la evidencia

### 4.1 `POST /agente` — caso simple

```
POST /api/clinic/agente/  {"pregunta": "¿Qué casos están reportados?"}
→ 200

[01] pregunta     ¿Qué casos están reportados?
[02] accion       CASOS_REPORTADOS({})
[03] observacion  {"herramienta":"CASOS_REPORTADOS","fuente":"clinic_samples","n":2,…}
[04] respuesta    Hay dos casos reportados: CHN-2026-08-06-2574 y CHN-DEMO-T21.

pasos 4/6 · tokens 1.853 entrada / 43 salida · 300 s · completado: sí
```

### 4.2 Multipaso — encadena herramienta + RAG

```
[01] pregunta     ¿Hay cromosomas pendientes de revisar, y por qué hay que revisarlos?
[02] accion       CROMOSOMAS_PARA_REVISION({})
[03] observacion  {"n":50,"fuente":"clinic_chromosomes",…}
[04] accion       buscar_documentacion({"pregunta":"por qué revisar cromosomas…"})
[05] observacion  {"encontrado":true,"fuentes":[…]}
[06] respuesta    …

pasos 6/6 · tokens 2.705 / 279 · 843 s
```

Ninguna de las dos preguntas la resuelve un nivel inferior: la primera necesita
el estado, la segunda necesita **estado y regla**.

### 4.3 Las 6 herramientas descubiertas por protocolo

```
$ python cliente_mcp.py
6 herramientas via JSON-RPC:
  cromosomas_para_revision     Lista los cromosomas marcados en naranja…
  casos_pendientes_firma       Lista los casos que el analista ya validó…
  casos_reportados             Lista los casos ya cerrados y firmados…
  casos_en_proceso             Lista las muestras que el sistema analiza…
  buscar_documentacion         Busca en la documentación del laboratorio…
  preparar_validacion_de_caso  Prepara la validación de un caso…

Este cliente NO importa Django ni tools.py: solo habla el protocolo.
```

---

## 5. El guardrail de escritura, y por qué aquí es más estricto

El laboratorio de clase permite que `confirmado=true` cancele el pedido. **Aquí
nunca ejecuta**, y la diferencia es de dominio, no de implementación.

AGENTS.md, RN-01, literal:

> Ningún informe puede emitirse sin: (a) validación manual del analista de TODOS
> los cromosomas naranjas (b) firma digital del supervisor (MFA obligatorio)

RN-06 añade que Supervisor y Analista no pueden ser el mismo usuario. Un proceso
automático no cumple ninguna: no es un analista identificado ni puede aportar un
segundo factor. Cancelar una compra es reversible y lo autoriza su dueño;
validar un cariotipo es un acto clínico que firma un profesional con su nombre.

**Con `confirmado=false`** devuelve el trabajo preparado:

```json
{"caso": "CHN-2026-08-06-0001", "estado_actual": "READY",
 "naranjas_sin_resolver": 32,
 "bloqueos": ["32 cromosoma(s) naranja sin resolver (RN-02)"],
 "quien_puede_hacerlo": "un analista identificado, desde la aplicación. No el agente: RN-01."}
```

**Con `confirmado=true`**, llamado **desde el cliente MCP externo** —que no
conoce RN-01—:

```json
{"ejecutado": false, "motivo": "RN-01",
 "detalle": "Un agente no puede validar un caso. RN-01 exige validación manual
             del analista y firma del supervisor con MFA; RN-06 exige además
             que no sean la misma persona."}
```

El guardrail vive **en la herramienta**, no en el bucle. Si viviera en el bucle
solo protegería a nuestro agente; puesto en la herramienta viaja con ella por
MCP a cualquier cliente que la descubra.

---

## 6. Qué no funcionó — hallazgos medidos

### 6.1 El modelo de 3B no encadenaba, y rellenaba el hueco inventando

Ante «¿hay cromosomas pendientes, y por qué hay que revisarlos?» hacía **una**
consulta y se inventaba la segunda mitad. Dio un umbral del **90%** —el real es
85%, y está en el corpus a una llamada de distancia— y lo encabezó con *«según
la herramienta de consulta»*.

Inventar es grave; **atribuirlo a una fuente que no lo dijo, más**. Y solo se ve
mirando la traza: sin ella, la respuesta parece fundamentada. Es exactamente el
argumento de por qué la traza es un guardrail y no una utilidad de depuración.

Corregido reforzando las instrucciones con el ejemplo concreto y prohibiciones
explícitas. Ahora encadena (§3.2).

### 6.2 Medir el RAG aislado no predice su comportamiento dentro del agente

El RAG mide **89%** (16/18) con preguntas escritas por una persona. Dentro del
bucle las escribe el modelo, y las escribe peor: reformuló la consulta como
«por qué revisar cromosomas pendientes» y recuperó ADR-0027 —un documento sobre
similitud vectorial— con el que construyó una respuesta sin sentido.

La misma pregunta escrita como «¿por qué el sistema marca cromosomas en
naranja?» **sí** la acierta; está en el banco de evaluación.

**Consecuencia metodológica:** un componente medido aislado no queda validado
para su uso dentro de un agente. Queda pendiente volver a medir el RAG con las
consultas que genera el modelo.

### 6.3 El umbral de similitud no decide (nivel 3, se arrastra al 4)

Medido sobre 18 preguntas etiquetadas:

```
cubiertas por el corpus   similitud top-1: 0.601 – 0.695
fuera del corpus          similitud top-1: 0.608 – 0.662
```

El rango a rechazar cae **dentro** del rango bueno. Barrido de 0.50 a 0.75: 56%
en todos los valores útiles. El coseno mide parecido temático y el corpus es
monotemático. Se resolvió separando responsabilidades — el índice recupera, el
modelo decide — y el juez se midió **dos veces**: la primera versión (39%) era
**peor que no tener juez** (56%); la segunda llega a 89%.

### 6.4 Latencia

| | |
|---|---|
| Consulta simple (4 pasos) | ~300 s |
| Multipaso (6 pasos) | ~843 s |

Cada paso reenvía todo el historial y todos los *schemas*. Con un 3B en CPU, el
nivel 4 no es utilizable de forma interactiva. Es un dato para decidir dónde
aplicarlo, no un fallo del diseño.

---

### 6.5 Integrar el RAG en el enrutador costó dos aciertos — medido con A/B

Al añadir `DOCUMENTACION` como cuarto camino, el banco de 56 preguntas bajó de
**48/56 (86%) a 44/56 (79%)**. Para saber si era regresión o efecto de las
etiquetas se reprodujo el estado anterior en un *worktree* de git sobre el
commit previo al RAG, con **el mismo banco, la misma base y el mismo modelo**:
dio **48/56 exacto**. La causa queda aislada en la integración del RAG.

Comparando los fallos uno a uno —8 antes, 12 después— el saldo real es otro:

| | |
|---|---|
| **7 fallos ya existían** y fallan igual | no son regresión |
| **3 nuevos son fallo por etiqueta, acierto por diseño** | el RAG las responde; el banco es anterior a esa capacidad |
| **2 nuevos son regresión real** | el RAG se lleva preguntas que **sí** tenían herramienta |
| **1 se arregló** | |

La **regresión real son 2 preguntas**, no las siete que aparentaba el número:
«¿Dónde no confío en lo que dijo la IA?» y «¿Qué tengo que confirmar a mano?»
esperaban `CROMOSOMAS_PARA_REVISION` y acabaron en documentación. El RAG
compite con las herramientas por preguntas de estado formuladas en tono vago.

Leído con el banco corregido para la capacidad nueva —las 3 preguntas
documentales pasan a esperar `CORPUS_DOCUMENTAL`— el resultado es **47/56
(84%)**. Se reportan **los dos números**: el crudo contra el banco intacto, y
el corregido explicando por qué cambió la expectativa.

**Hallazgo que el A/B destapó y que la métrica escondía:** las 4 preguntas
adversarias que reciben una herramienta equivocada —«¿qué significa que un
cromosoma esté naranja?», «¿por qué el sistema los marca?», «¿cuánto tarda en
procesar una muestra?», «¿qué porcentaje sale alterado?»— **ya fallaban antes
del RAG, con exactamente la misma herramienta equivocada**. No las rompió el
RAG. Y dos de ellas son preguntas que el RAG responde bien: el arreglo no es
tocar el RAG, es que el enrutador las mande a `DOCUMENTACION`. Objetivo
medible y acotado.

---

## 7. El paso 6: comparar similitudes y sugerir

El pipeline se cierra con lo que la consigna llama «comparar porcentajes de
similitud para ofrecer la respuesta más óptima y sugerencias apropiadas».

**Antes de construirlo se midió si el puntaje puede sostener esa promesa**, con
el banco de 18 preguntas y el índice de 1.144 fragmentos:

| señal | cubiertas por corpus | fuera del corpus |
|---|---|---|
| similitud top-1 | 0.601 – 0.695 | 0.608 – 0.662 |
| margen top1−top2 | 0.000 – 0.033 | 0.006 – 0.024 |
| dispersión del top-5 | 0.002 – 0.019 | 0.004 – 0.018 |

Las tres se solapan; en margen y dispersión el rango de las preguntas a
rechazar queda *dentro* del de las buenas. El mejor umbral concebible sobre
cualquiera de ellas acierta 67-72%, por debajo del 89% que ya da el juez.

De ahí salen las dos reglas del diseño: **la respuesta más óptima la elige el
juez, no el puntaje**, y **ninguna sugerencia afirma pertinencia** — solo puede
decir «esto es lo más parecido que hay».

Dónde aporta de verdad es en la abstención. Un «no sé» a secas es un callejón
sin salida; con el paso 6 el usuario ve qué contiene el corpus cerca de su
pregunta y puede reformular:

```
PREGUNTA: Cual es el telefono del doctor Rojas?
responde=False   MOTIVO: el corpus no cubre la pregunta

El corpus no cubre esa pregunta. Lo más parecido que contiene es:
  - ADR: 0011-rol-administrador.md — Contexto (62.9%)
  - ADR: 0018-permisos-rol-backend-clinic.md — Positivas (59.0%)
  - BRD: BRD_vFinal.md — 14. Restricciones y supuestos (57.7%)
```

Las sugerencias viajan también en la observación del **agente**, y también
cuando no encuentra: así puede reintentar con una pregunta mejor en vez de
rendirse en el primer paso.

Ejecutarlo contra el índice real corrigió dos cosas que el diseño en papel no
vio: al explorar salían tres secciones del mismo documento (ahora se agrupa por
documento), y las secciones venían como migas de pan ilegibles del troceador.
Reproducible con `python manage.py demo_sugerencias`, que imprime el código y
su salida en la misma pantalla.

---

## 8. Dos desviaciones del laboratorio, justificadas

**La sesión MCP se mantiene abierta durante todo el bucle.** El ejemplo abre una
por llamada; ahí vale porque su servidor es ligero. El nuestro arranca Django
entero, así que abrir y cerrar por acción costaría varios segundos cada vez. Se
resolvió con un hilo con su propio bucle de eventos.

**El SDK cambió de nombres entre versiones.** `FastMCP` → `MCPServer`, e
`inputSchema` → `input_schema`. Se prueban ambas formas en vez de fijar una
versión.

---

## 9. Qué falta

1. **Volver a medir el RAG con consultas generadas por el agente** (§5.2). Es el
   hueco metodológico más importante.
2. **Volver a medir el enrutador**: las 6 preguntas de documentación del banco
   de 56 que antes caían en «no sé» deberían resolverse ahora. El «antes» ya
   está medido (48/56).
3. Aplicar el patrón a los otros módulos troncales.

---

## 10. Cómo reproducirlo

```bash
cd backend-clinic

python cliente_mcp.py                    # descubre las 6 por protocolo
python cliente_mcp.py casos_reportados   # las llama sin importar Django

python manage.py demo_agente             # 3 casos con la traza a la vista
python manage.py demo_agente --mcp       # el MISMO bucle con tools descubiertas

# el endpoint
POST /api/clinic/agente/  {"pregunta": "...", "mcp": false}
```

**44 tests verdes.** Requiere Ollama corriendo con `llama3.2:3b` y
`nomic-embed-text`; el índice del RAG ya está versionado en el repositorio.
