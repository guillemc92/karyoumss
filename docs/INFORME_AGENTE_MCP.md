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

## 3. Traza — la evidencia

### 3.1 `POST /agente` — caso simple

```
POST /api/clinic/agente/  {"pregunta": "¿Qué casos están reportados?"}
→ 200

[01] pregunta     ¿Qué casos están reportados?
[02] accion       CASOS_REPORTADOS({})
[03] observacion  {"herramienta":"CASOS_REPORTADOS","fuente":"clinic_samples","n":2,…}
[04] respuesta    Hay dos casos reportados: CHN-2026-08-06-2574 y CHN-DEMO-T21.

pasos 4/6 · tokens 1.853 entrada / 43 salida · 300 s · completado: sí
```

### 3.2 Multipaso — encadena herramienta + RAG

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

### 3.3 Las 6 herramientas descubiertas por protocolo

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

## 4. El guardrail de escritura, y por qué aquí es más estricto

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

## 5. Qué no funcionó — hallazgos medidos

### 5.1 El modelo de 3B no encadenaba, y rellenaba el hueco inventando

Ante «¿hay cromosomas pendientes, y por qué hay que revisarlos?» hacía **una**
consulta y se inventaba la segunda mitad. Dio un umbral del **90%** —el real es
85%, y está en el corpus a una llamada de distancia— y lo encabezó con *«según
la herramienta de consulta»*.

Inventar es grave; **atribuirlo a una fuente que no lo dijo, más**. Y solo se ve
mirando la traza: sin ella, la respuesta parece fundamentada. Es exactamente el
argumento de por qué la traza es un guardrail y no una utilidad de depuración.

Corregido reforzando las instrucciones con el ejemplo concreto y prohibiciones
explícitas. Ahora encadena (§3.2).

### 5.2 Medir el RAG aislado no predice su comportamiento dentro del agente

El RAG mide **89%** (16/18) con preguntas escritas por una persona. Dentro del
bucle las escribe el modelo, y las escribe peor: reformuló la consulta como
«por qué revisar cromosomas pendientes» y recuperó ADR-0027 —un documento sobre
similitud vectorial— con el que construyó una respuesta sin sentido.

La misma pregunta escrita como «¿por qué el sistema marca cromosomas en
naranja?» **sí** la acierta; está en el banco de evaluación.

**Consecuencia metodológica:** un componente medido aislado no queda validado
para su uso dentro de un agente. Queda pendiente volver a medir el RAG con las
consultas que genera el modelo.

### 5.3 El umbral de similitud no decide (nivel 3, se arrastra al 4)

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

### 5.4 Latencia

| | |
|---|---|
| Consulta simple (4 pasos) | ~300 s |
| Multipaso (6 pasos) | ~843 s |

Cada paso reenvía todo el historial y todos los *schemas*. Con un 3B en CPU, el
nivel 4 no es utilizable de forma interactiva. Es un dato para decidir dónde
aplicarlo, no un fallo del diseño.

---

## 6. Dos desviaciones del laboratorio, justificadas

**La sesión MCP se mantiene abierta durante todo el bucle.** El ejemplo abre una
por llamada; ahí vale porque su servidor es ligero. El nuestro arranca Django
entero, así que abrir y cerrar por acción costaría varios segundos cada vez. Se
resolvió con un hilo con su propio bucle de eventos.

**El SDK cambió de nombres entre versiones.** `FastMCP` → `MCPServer`, e
`inputSchema` → `input_schema`. Se prueban ambas formas en vez de fijar una
versión.

---

## 7. Qué falta

1. **Volver a medir el RAG con consultas generadas por el agente** (§5.2). Es el
   hueco metodológico más importante.
2. **Paso 6 del pipeline RAG**: sugerencias basadas en similitud.
3. **Volver a medir el enrutador**: las 6 preguntas de documentación del banco
   de 56 que antes caían en «no sé» deberían resolverse ahora. El «antes» ya
   está medido (48/56).
4. Aplicar el patrón a los otros módulos troncales.

---

## 8. Cómo reproducirlo

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
