# Guion de defensa — Módulo 6: Agente + MCP

> Documento de trabajo para la defensa. No es un entregable: es la secuencia de
> lo que se muestra, en qué orden y con qué comando, más las preguntas difíciles
> con su respuesta medida.

## 0. Antes de empezar — comprobaciones

```bash
ollama list                      # llama3.2:3b y nomic-embed-text presentes
cd backend-clinic
.venv/Scripts/python manage.py check
```

**El venv correcto no es opcional.** Con `backend-admin/.venv` no está el SDK de
`openai` y el sistema **degrada en silencio**: los escenarios devuelven
`SIN_MATCH` y parece comportamiento correcto. Ya pasó una vez. Usar siempre
`backend-clinic/.venv`.

**Nunca compartir pantalla con una clave a la vista.** Van en `.env`,
protegido por `.gitignore`. Aquí el modelo es local, así que no hay clave de
API — decirlo es un punto a favor, no una excusa.

---

## 1. La escalera, en 60 segundos

El docente evalúa que se use **el nivel mínimo que resuelve el problema**. La
frase de apertura debería ser esa, no «implementé un agente».

| Nivel | Qué se construyó | Comando |
|---|---|---|
| 0 · llamada al SDK | narrativa clínica desde datos reales | `manage.py demo_llm` |
| 1 · salida estructurada | JSON tipado con Pydantic + reintento | (dentro de demo_llm) |
| 2 · tool calling | 4 escenarios de la consigna | `manage.py demo_tools` |
| 3 · RAG | corpus del proyecto, 1.144 fragmentos | `manage.py demo_sugerencias` |
| 4 · agente + MCP | bucle ReAct, 6 tools por MCP | `manage.py demo_agente` |

Nivel 5 (LangGraph) **no se implementa**, y eso es una decisión, no una
carencia: el propio docente lo sitúa en memoria persistente entre sesiones
—«eso todavía no»— y en este sistema el estado clínico ya vive en PostgreSQL
con audit trail encadenado. Ver ADR-0031.

---

## 2. Qué mostrar, en orden

### 2.1 Tool calling — los cuatro escenarios (nivel 2)

```bash
manage.py demo_tools
```

Los cuatro que pide la consigna: happy path, sinónimo, fuera de alcance y
modelo apagado. **El cuarto es el que más vale**: con la IA apagada el sistema
sigue respondiendo por vocabulario. Eso demuestra RN-07 (degradar, no romper).

Para la captura de «código + salida a la vez», que la consigna valora:

```bash
manage.py demo_codigo_salida
```

Lee el código con `inspect.getsource` de la fuente real, así que no puede estar
desincronizado del que se ejecuta un segundo después.

### 2.2 RAG y el paso 6 (nivel 3)

```bash
manage.py demo_sugerencias
```

Muestra las dos ramas. **Detenerse en la segunda**: cuando el corpus no cubre
la pregunta, el sistema no dice sólo «no sé» — dice qué contiene cerca, con su
porcentaje, para que el usuario reformule.

### 2.3 Agente + MCP (nivel 4)

```bash
manage.py demo_agente
```

Enseñar **la traza**, no la respuesta. Pensamiento → acción → observación, con
el consumo de tokens. Es la evidencia que la consigna pide y el único modo de
ver si el agente encadenó de verdad o rellenó el hueco inventando.

Y el servidor MCP por dentro:

```bash
python servidor_mcp.py       # publica 6 tools por stdio (JSON-RPC 2.0)
python cliente_mcp.py        # las descubre SIN importar el módulo
```

El punto: el cliente no importa nada del servidor. Cambia el enchufe, no la
lógica del bucle.

---

## 3. Los guardrails, uno por uno

Es la parte que el docente llama «no negociables». Conviene enseñarlos en el
código, no contarlos.

| Guardrail | Dónde | Qué decir |
|---|---|---|
| `MAX_PASOS = 6` | `agente.py` | «un agente sin tope es un bucle infinito con factura» |
| `temperature = 0.0` | `agente.py` | decisiones técnicas reproducibles, no creativas |
| Confirmación humana | `agente_escritura.py` | **aquí somos más estrictos que el laboratorio** |
| MCP JSON-RPC 2.0 | `servidor_mcp.py` | el guardrail viaja DENTRO de la herramienta |
| Traza con tokens | `Traza` en `agente.py` | sin traza, un agente es un oráculo |

**El guardrail de escritura merece parada.** En el laboratorio de clase,
`cancelar_pedido` ejecuta con `confirmado=true`. Aquí
`preparar_validacion_de_caso` **nunca ejecuta**, ni con `confirmado=true`,
porque RN-01 exige un analista identificado y la firma MFA de un supervisor. El
agente **prepara**; no valida. Es la diferencia entre copiar el laboratorio y
aplicarlo a un dominio regulado.

---

## 4. Las mediciones — la parte fuerte

Nada de esto es una opinión. Todo se puede volver a correr delante del tribunal.

| Qué | Resultado | Comando |
|---|---|---|
| Enrutador, banco intacto | **44/56 (79%)** — antes 48/56 | `manage.py eval_enrutado` |
| Enrutador, banco al día | 47/56 (84%) | (ver §5.4 del informe) |
| RAG con juez (18 preguntas) | 16/18 (89%) | `manage.py eval_rag --con-juez` |
| Tests backend | 534 verdes | `pytest` |

**Tres decisiones que se tomaron midiendo, no opinando:**

1. **El umbral de similitud no discrimina.** Medido tres veces: similitud
   top-1, margen top1−top2 y dispersión del top-5 se solapan entre preguntas
   cubiertas y no cubiertas. Ningún corte separa. Por eso decide el juez, no el
   número (ADR-0029 D4 y D7).
2. **El prompt del juez se midió dos veces.** La v1 decía «ante la duda, no
   respondas» y el modelo se abstuvo en 11 de 12 preguntas que sí estaban
   cubiertas: 39%, **peor que no tener juez** (56%). Invertir el defecto lo
   subió a 89%.
3. **Un componente medido aislado no queda validado dentro de un agente.** El
   RAG da 89% con preguntas escritas por una persona; dentro del bucle las
   escribe el modelo y las escribe peor. Está declarado como hueco abierto, no
   tapado.

---

## 5. Preguntas difíciles, con respuesta

**«¿Por qué NumPy y no ChromaDB, como en el laboratorio?»**
El corpus son 1.144 fragmentos: un producto matriz-vector de 1.144×768, que
NumPy resuelve en microsegundos. Chroma añade una base binaria que no se
versiona bien en git. Es la regla del nivel mínimo aplicada a la
infraestructura. Si el corpus creciera dos órdenes de magnitud, `buscar()` es
la única función que habría que cambiar. ADR-0029 D3.

**«¿Por qué no LangGraph?»**
Porque el estado clínico ya vive en PostgreSQL con un audit trail append-only
encadenado por SHA-256, que es lo que sostiene la firma electrónica. Meterlo en
checkpoints de LangGraph crearía **una segunda fuente de verdad para un proceso
auditado**. No es objeción de complejidad, es de cumplimiento. ADR-0031.

**«¿Por qué un solo agente y no uno por módulo?»**
Es literalmente lo que el docente advierte: «un agente confundido es una fuga
de dinero». Y en este flujo, seis de las siete cajas que se propusieron no eran
agentes — el propio diagrama describía el validador ISCN como «función
determinística». ADR-0031.

**«¿El agente puede modificar datos clínicos?»**
No. Prepara una validación y se detiene, incluso con confirmación explícita.
RN-01 y RN-06 exigen persona identificada y segregación de funciones.

**«¿Qué pasa si se cae Ollama?»**
El camino KEYWORD sigue resolviendo por vocabulario y el RAG se degrada a «no
puedo fundamentar» en vez de volcar el fragmento más parecido. RN-07.

**«El enrutador empeoró al meter el RAG, ¿no?»** — *pregunta que conviene
hacerse uno mismo antes de que la haga el tribunal.*
Bajó de 48/56 a 44/56, sí. Se hizo un **A/B** reproduciendo el estado anterior
en un worktree de git sobre el commit previo, con el mismo banco y el mismo
modelo: dio 48/56 exacto, así que la causa está aislada. Comparando fallo a
fallo: 3 de las 4 pérdidas son **etiqueta desactualizada** —el banco es
anterior a que existiera el camino RAG— y **la regresión real son 2 preguntas**
de estado que el RAG se lleva. Y el A/B destapó algo que el número escondía:
las 4 adversarias que reciben herramienta equivocada **ya fallaban antes del
RAG, con la misma herramienta**. Se reportan los dos números y no se tocó el
banco para que subiera.

**«¿Esto mejora el cariotipado?»**
No, y es importante decirlo antes de que lo pregunten. Esta capa responde sobre
el estado y la documentación; no segmenta ni clasifica cromosomas. El producto
clínico se mide aparte, y ahí el dato es que corregir la IA cuesta hoy 64
acciones por caso frente a 46 a mano (DTI §9.1.1). Reconocerlo con el número
delante vale más que evitarlo.

---

## 6. Lo que NO hay que hacer

- No llamar «orquestación de agentes» al pipeline de visión. El material del
  propio docente lo contradice.
- No presentar el `macro-F1 0.6958` como si midiera el producto.
- No enseñar el flujograma de siete agentes: fue descartado y está firmado el
  porqué (ADR-0031).
- No improvisar sobre lo que falta. Está escrito en §7 del informe.
