---
id: ADR-0032
title: Memoria conversacional del agente con LangGraph — y por qué el estado clínico no entra ahí
date: 2026-08-18
status: accepted
related: [ADR-0031, ADR-0030, ADR-0022, ADR-0024]
---

# ADR-0032: Memoria conversacional del agente (nivel 5)

## Contexto

ADR-0030 dejó una carencia anotada: la memoria del agente es la lista de
mensajes y **muere con la petición**. Una repregunta —«¿y de esos cuál
mencionaste primero?»— llega sin referente, y el modelo no tiene de dónde
agarrarse.

El nivel 5 de la escalera del módulo (LangGraph) existe precisamente para eso.
El material del Día 6 lo enuncia como el gancho del Día 7: *«hoy la memoria
muere con el proceso y la confirmación vive en el request; mañana ambas
sobreviven — eso ES LangGraph»*.

La tentación es tratar el nivel 5 como «meter LangGraph en el proyecto». Este
ADR acota qué entra y, sobre todo, qué **no**.

## Decisión

### D1 — LangGraph entra solo como memoria conversacional

`agente_grafo.py` implementa el bucle como `StateGraph` con un `SqliteSaver`
por `thread_id`. La conversación sobrevive al proceso y se reanuda.

Nada más. No orquesta el pipeline de visión (ADR-0031), no gestiona el flujo
clínico y no sustituye a nadie.

### D2 — El estado clínico NO vive en los checkpoints

Un caso avanza `READY → ANALYST_VALIDATED → SIGNED → REPORTED` en PostgreSQL,
con un audit trail append-only encadenado por SHA-256 (ADR-0022) que es lo que
sostiene la firma electrónica bajo 21 CFR Part 11.

Duplicar esa máquina de estados en un checkpointer crearía **una segunda fuente
de verdad para un proceso auditado**: cuando alguien pregunte en qué estado
estaba un caso, no puede haber dos respuestas. Es una objeción de
**cumplimiento**, no de complejidad.

### D3 — No se usa `interrupt` para la aprobación humana

Es el que más tienta, porque «aprobar desde otra sesión» es literalmente RN-06:
el analista valida y **otra persona** firma, días después. Parece el caso de
uso perfecto del nivel 5.

No se hace, y por una razón concreta: `preparar_validacion_de_caso` **nunca
ejecuta**, ni con `confirmado=true`, porque la validación real exige un analista
identificado y la firma MFA de un supervisor. Un `interrupt` sobre el agente
sería aprobar algo que de todos modos no escribe: teatro con aspecto de
guardrail.

La aprobación persistente entre sesiones **ya existe** en este sistema. No hace
falta reimplementarla peor.

### D4 — Aditivo: el nivel 4 no se toca

`agente.py` y `POST /agente` siguen exactamente igual. La memoria se activa
pasando `thread_id` en el cuerpo; sin él, el comportamiento es el de siempre.

Dos motivos. El nivel 4 está medido, documentado y es el entregable del módulo:
romperlo para añadir el siguiente sería cambiar algo que funciona por algo que
todavía no se ha medido. Y permite comparar ambos niveles **en la misma
ejecución**, que es lo que hace `eval_memoria`.

### D5 — El catálogo no se duplica

El grafo recibe `schemas()` y `ejecutar()` de `agente_acciones`, los mismos que
usan el bucle del nivel 4 y el servidor MCP. Una séptima herramienta aparecería
en los tres caminos sin tocar este módulo, y el guardrail de escritura sigue
viviendo **dentro** de la herramienta.

## Consecuencias

**Verificado, no supuesto.** El grafo llama a las 6 herramientas reales y, en un
segundo turno sin repetirle el contexto, responde usando lo del primero. La
traza conserva la forma del nivel 4 —`pregunta · accion · observacion ·
respuesta`— para que la evidencia siga siendo comparable entre niveles.

**La memoria vive aparte de la base clínica**, en `agente_memoria.sqlite3`, y
está fuera de git. En el checkpoint queda el historial, que incluye códigos CHN
y referencias `ANON-…`: el dato ya anonimizado (ADR-0003). Ninguna herramienta
del catálogo devuelve PII, así que no hay PII que proteger ahí (RN-03).

**Coste que esto añade.** Cada turno reenvía el historial completo más los 6
schemas. Medido en el primer turno de prueba: 4.914 tokens de entrada en el
turno 2 frente a los de un turno suelto. Es el coste del nivel, y el material
del módulo ya advierte de él.

**Lo que sigue sin resolverse.** El `llama3.2:3b` no siempre aprovecha la
memoria: se le ha visto volver a llamar a las herramientas en el segundo turno
en vez de leer el historial, y emitir una llamada a herramienta como texto
plano en vez de como `tool_call`. Tener memoria y saber usarla son cosas
distintas; lo segundo depende del modelo.

### Resultado medido (`manage.py eval_memoria`, 10 pares, 2026-08-19)

| Grupo | Nivel 4 (sin memoria) | Nivel 5 (con memoria) |
|---|---|---|
| **Conversación** (exigen memoria) | **0/8** | **4/8** |
| Dato (control: reconsultables) | 0/2 | 0/2 |

El grupo de conversación aísla lo que la memoria aporta: sus repreguntas
apuntan a lo que el agente **dijo**, no al dato, así que no hay forma de
contestarlas volviendo a consultar. **El nivel 4 acierta cero de ocho** y su
comportamiento es el correcto sin memoria — «no dije nada anteriormente».

El grupo de control existe para que el banco pueda dar la razón al nivel 4: sus
repreguntas sí son reconsultables. Que ambos den 0/2 dice que el 3B tampoco
aprovecha esa vía, no que la vía no exista.

**La cifra bruta fue 5/8 y se corrigió a la baja.** Uno de los aciertos era
falso: el modelo volcó la observación cruda —`{'herramienta': …, 'fuente': …}`—
como si fuera su respuesta, y como contenía el código CHN pasaba el test.
Volcar un dict no es haber recordado. El instrumento ahora lo descarta
(`es_respuesta`).

De los 4 restantes, **3 son inequívocos** —el mejor devuelve exactamente
`CHN-2026-08-06-1384` y nada más— y **1 es parcial**: recordó la conversación
pero enumeró los dos casos en vez del primero.

## Alternativas descartadas

| Alternativa | Por qué no |
|---|---|
| Migrar el bucle del nivel 4 a LangGraph y borrarlo | Rompe un entregable medido para ganar lo mismo. El nivel 4 es la línea base de la comparación |
| Mover el flujo clínico a un grafo con checkpoints | Segunda fuente de verdad en un proceso auditado (D2) |
| `interrupt` para la firma del supervisor | La aprobación real ya existe y el agente no escribe (D3) |
| Guardar la memoria en la base clínica | Mezcla conversación con historia clínica y ensucia el audit trail |
| Memoria en RAM entre peticiones | No sobrevive al proceso, que es justo lo que el nivel 5 viene a resolver |

## Implementación

`backend-clinic/apps/samples/agente_grafo.py` (93% de cobertura, 18 tests en
`test_agente_grafo.py`), `POST /api/clinic/agente/` con `thread_id` opcional, y
`manage.py eval_memoria` para medir nivel 4 contra nivel 5.
