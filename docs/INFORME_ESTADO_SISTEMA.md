# De la simulación a la implementación — estado del sistema

> **BIOMED UMSS · Plataforma de Cariotipado Asistido por IA**
> Informe de estado a 19 de agosto de 2026 · Módulo 6
> Ing. Guillermo Mamani Chambi

---

## 1. En una página

Este módulo empezó con un sistema que **simulaba** su capa de inteligencia y
termina con uno que la **ejecuta**. El cambio no es de tamaño sino de
naturaleza: donde antes había un PNG de 1×1 píxel haciendo de mapa de calor y
una clasificación por rango de tamaño, hoy hay un EfficientNet-B3 entrenado con
48.000 recortes del propio laboratorio y un Grad-CAM que lee los gradientes de
la última capa convolucional.

Pero el resultado más valioso del módulo **no es lo que se construyó, sino lo
que se midió**. Cinco instrumentos de evaluación devolvieron números
incómodos, y esos números cambiaron decisiones de arquitectura: uno de ellos
demostró que el pipeline hoy **cuesta más trabajo del que ahorra**, y otro
desmontó un diagnóstico que el propio equipo daba por cerrado.

| | |
|---|---|
| Commits del periodo | **41** |
| Código nuevo de la capa IA | **2.111 líneas** (+ 1.474 de pruebas) |
| ADRs firmados | **6** (0027 → 0032) |
| Suite de pruebas | **596 verdes**, cobertura 84,87% |
| Niveles de la escalera implementados | **0 a 5** |

---

## 2. Qué era simulación y qué es implementación

La distinción se mantiene explícita en el DTI §9.1, porque presentar como
construido algo que no lo está es la forma más rápida de perder credibilidad
técnica.

| Componente | Antes del módulo | Hoy |
|---|---|---|
| Clasificación de cromosomas | Placeholder por rango de tamaño, confianza fija 0.55 | **EfficientNet-B3 entrenado**, macro-F1 0.6958 |
| Explicabilidad (XAI) | PNG de 1×1 píxel | **Grad-CAM real** sobre la última capa convolucional |
| Corpus documental | No existía | **1.144 fragmentos** indexados (ISCN 2024, ADRs, FSD, BRD) |
| Consultas en lenguaje natural | No existía | Enrutador de 4 caminos + agente ReAct |
| Herramientas del agente | No existían | **6 publicadas por MCP** (JSON-RPC 2.0) |
| Memoria del agente | No existía | Checkpoints persistentes por `thread_id` |
| Segmentación | OpenCV + watershed | **OpenCV + watershed** *(U-Net sigue siendo diseño, no implementación)* |

La última fila es la que más importa: **sigue sin construirse**, está declarada
como tal, y el §5 de este informe explica por qué eso resultó ser menos
determinante de lo que se creía.

### 2.1 La verificación, no la afirmación

El flujo completo se ejecutó con metafases reales del dataset MetaClass el 19
de agosto:

```
POST /api/clinic/samples/register/   →  31,9 s
CHN-2026-08-19-2414 · READY · 3 imágenes · degraded=false
modelo: opencv-watershed-v0+efficientnet-b3-metaclass-v3
47 cromosomas detectados · 42 naranjas · 5 verdes
confianza media 0,542 — solo 5 superan el umbral de 0,85
```

No hay mocks en esa ruta. La cadena de versión que emite el servicio declara
exactamente qué modelo produjo cada resultado.

---

## 3. Dónde se aplicó lo aprendido en el módulo

El módulo enseña una **escalera de integración** con una regla explícita: *usar
el nivel mínimo que resuelva el problema*. Se implementaron los seis niveles,
cada uno resolviendo un problema real del laboratorio y no un ejercicio.

### Nivel 0 — Llamada al SDK
**Dónde:** redacción de la narrativa clínica del informe (`llm_client.py`).
**Por qué ahí:** convertir una nomenclatura ISCN en un párrafo legible es
generación de texto pura, un solo paso.

> **Decisión propia:** el modelo corre en **local** con Ollama. El corpus
> incluye documentación clínica y RN-03 exige cero fuga de datos: no tiene por
> qué salir de la máquina para convertirse en tokens (ADR-0024).

### Nivel 1 — Salida estructurada
**Dónde:** el esquema Pydantic que valida la respuesta del modelo, con reintento
pasándole el error de validación.
**Hallazgo:** en un caso adversario el modelo alucinó tres veces seguidas y el
sistema **se bloqueó las tres**. Es el comportamiento correcto: mejor no
responder que responder mal.

### Nivel 2 — Tool calling
**Dónde:** enrutador de consultas (`tool_router.py`) con cuatro caminos.

```
KEYWORD    coincide una palabra del catálogo  → se ejecuta SIN modelo
LLM        no coincide nada                   → el modelo elige la herramienta
RAG        pregunta de documentación          → va al corpus
SIN_MATCH  nadie puede responder              → se dice que no se sabe
```

> **Lo que hace este diseño distinto:** el modelo **solo elige un nombre**. No
> redacta la respuesta ni toca los datos — las filas salen de una consulta a la
> base. La pantalla muestra siempre la herramienta usada y la tabla real de
> origen, así que un usuario puede distinguir un dato consultado de uno
> inventado.

El camino KEYWORD no es una optimización: es lo que hace que el sistema **siga
respondiendo con la IA apagada** (RN-07).

### Nivel 3 — RAG
**Dónde:** corpus del propio proyecto — el estándar ISCN 2024, los ADRs, el FSD
y el BRD.

| Fuente | Fragmentos |
|---|---:|
| ISCN 2024 | 711 |
| ADRs | 337 |
| FSD | 37 |
| BRD | 33 |
| Guía | 26 |

> **Desviación deliberada del laboratorio de clase:** se usa NumPy por fuerza
> bruta en vez de ChromaDB. Son 1.144 fragmentos — un producto matriz-vector de
> 1.144×768 que NumPy resuelve en microsegundos. Chroma añadiría una base
> binaria que no se versiona bien en git. Es la regla del nivel mínimo aplicada
> a la infraestructura (ADR-0029 D3).

### Nivel 4 — Agente + MCP
**Dónde:** bucle ReAct (`agente.py`) con seis herramientas publicadas en un
servidor MCP propio sobre JSON-RPC 2.0 por stdio.

Los tres guardrails del módulo, y cómo se aplican aquí:

| Guardrail | Implementación |
|---|---|
| **Freno** — `MAX_PASOS = 6` | Un bucle sin tope es una fuga de dinero |
| **Cinturón** — confirmación de escritura | *Más estricto que el laboratorio* (ver abajo) |
| **Caja negra** — traza | Acción, observación y tokens de cada paso |

> **La desviación más importante del módulo.** En el laboratorio de clase,
> `cancelar_pedido` **sí ejecuta** con `confirmado=true`. Aquí
> `preparar_validacion_de_caso` **nunca ejecuta**, ni confirmado.
>
> La diferencia no es de implementación sino de dominio: cancelar una compra es
> reversible y lo autoriza su dueño; validar un cariotipo es un acto clínico que
> firma un profesional con su identidad. RN-01 exige validación manual del
> analista y firma del supervisor con MFA, y RN-06 exige que no sean la misma
> persona. Un proceso automático no es un analista identificado ni puede aportar
> un segundo factor.
>
> El guardrail vive **dentro de la herramienta**, no en el bucle: así viaja con
> ella por MCP a cualquier cliente que la descubra.

### Nivel 5 — LangGraph
**Dónde:** memoria conversacional del agente (`agente_grafo.py`), con
checkpoints persistentes por `thread_id`.

**Alcance acotado a propósito**, y esta es la decisión de arquitectura más
delicada del módulo: el **estado clínico no vive en los checkpoints**. Un caso
avanza `READY → ANALYST_VALIDATED → SIGNED → REPORTED` en PostgreSQL con un
audit trail encadenado por SHA-256 que sostiene la firma electrónica.

> Duplicar esa máquina de estados en un checkpointer crearía **una segunda
> fuente de verdad para un proceso auditado**: cuando un inspector pregunte en
> qué estado estaba un caso, no puede haber dos respuestas. Es una objeción de
> **cumplimiento**, no de complejidad (ADR-0032 D2).

Por la misma razón no se usa el `interrupt` de LangGraph para la aprobación
humana, aunque «aprobar desde otra sesión» sea literalmente RN-06: como la
herramienta nunca ejecuta, un `interrupt` sería aprobar algo que de todos modos
no escribe.

---

## 4. La regla de la escalera, aplicada en sentido contrario

Se propuso durante el módulo una arquitectura de **siete agentes** —Orquestador,
Preprocesador, Detector, Clasificador, Pairing, Validador ISCN y narrativa— y
se **rechazó**, con las razones firmadas en ADR-0031.

Tres hechos la decidieron:

1. **El flujo dibujado no tiene decisiones.** Preprocesar → detectar →
   clasificar tiene un orden fijo e inevitable: no se puede clasificar antes de
   segmentar. El flujograma era una línea recta con una sola bifurcación, y esa
   bifurcación era un `if` sobre un umbral. Un orquestador que reparte siempre
   en el mismo orden es una caja de paso.
2. **Seis de las siete cajas no eran agentes.** La propia propuesta describía el
   Validador ISCN como «función determinística», que es exactamente lo contrario
   de un agente.
3. **Los servicios que el diagrama repartía no existen** — el DTI se contradecía
   con su propia tabla de diseñado-frente-a-construido.

**La ramificación real del sistema está después del pipeline**, en la
semaforización: los cromosomas naranjas desvían el caso a corrección manual. Ahí
es donde el diagrama se bifurca, y es donde está el valor clínico.

Aplicar la regla de la escalera significó, en este caso, **bajar un peldaño en
lugar de subirlo**.

---

## 5. Lo que se midió, y lo que las mediciones cambiaron

Cinco instrumentos de evaluación, todos reproducibles con un comando.

| Medición | Resultado | Comando |
|---|---|---|
| Enrutador (56 preguntas) | 44/56 · 79% | `manage.py eval_enrutado` |
| RAG con juez (18 preguntas) | 16/18 · 89% | `manage.py eval_rag --con-juez` |
| Memoria: nivel 4 vs 5 | **0/8 → 4/8** | `manage.py eval_memoria` |
| Coste de corrección por caso | **64 acciones vs 46 a mano** | `training/eval_correccion.py` |
| Suite de pruebas | 596 verdes · 84,87% | `pytest` |

### 5.1 La medición que cambió la hoja de ruta

`eval_correccion.py` responde a una pregunta que el `macro-F1` no contesta:
**¿cuántas acciones necesita el analista para llevar la propuesta de la IA a un
cariotipo correcto?** La vara de comparación es ordenar el cariograma a mano:
46 colocaciones.

```
Acciones por caso   mediana 64 | min 51 | max 87
  estructura   4     separar / unir
  clase       28     reclasificar
  resolución  34     ver XAI + aceptar
Casos que cuestan MÁS que hacerlo a mano: 20/20 (100%)
```

**Hoy el pipeline añade trabajo en vez de ahorrarlo.** Y corrigió un diagnóstico
que se daba por cerrado: se asumía que el cuello de botella era la segmentación,
pero **la estructura son 4 de 64 acciones (6%)**. El grueso está en resolver
naranjas — 34 acciones, más de la mitad — y eso nace del umbral 0,85 y de la
obligación de consultar XAI antes de aceptar. Con un clasificador perfecto al
0,84 se pagarían igual.

**Consecuencia de producto:** una resolución **en bloque** recortaría del orden
de 30 acciones por caso **sin tocar ningún modelo**. Es más barato que entrenar
U-Net y ataca la mitad del coste.

### 5.2 El instrumento falla antes que el sistema

El aprendizaje metodológico más transferible del módulo: **cinco veces** la
primera medición fue inválida por un defecto del medidor, no del sistema medido.

| Instrumento | Qué estaba mal | Efecto |
|---|---|---|
| `eval_rag` | el prompt del juez decía «ante la duda, no respondas» | 39%: **peor que no tener juez** |
| `eval_correccion` | solo el 43% del ground truth tenía totales plausibles | cobraba como error de la IA el ruido de la etiqueta |
| `eval_memoria` | un timeout hacía `return` y borraba la corrida | se perdían pares buenos |
| `eval_memoria` | testigos de un solo dígito («0», «1») | **1/4 vs 3/4 inflado por los dos lados** |
| `eval_memoria` | el modelo volcaba la observación cruda como respuesta | contenía el código → pasaba por acierto |

De ahí salieron tres reglas: un testigo tiene que ser **específico**; un fallo de
infraestructura **anota y continúa**, nunca aborta; y hay que declarar qué casos
del banco son **débiles por diseño** y leer el resultado desglosado.

### 5.3 Cuando el A/B desmintió el análisis

Al integrar el RAG, el enrutador bajó de 48/56 a 44/56. El análisis a ojo
concluyó que había cuatro regresiones graves. Se reprodujo el estado anterior en
un **worktree de git** sobre el commit previo, con el mismo banco y el mismo
modelo: dio **48/56 exacto**.

Comparando fallo a fallo, la conclusión inicial era **falsa**: aquellas cuatro
preguntas ya fallaban antes con la misma herramienta equivocada. De las cuatro
pérdidas, **tres son etiqueta desactualizada** —el banco es anterior a que
existiera el camino RAG— y **la regresión real son dos preguntas**.

> Se reportan **dos números**: 44/56 con el banco intacto y 47/56 con el banco
> al día. No se tocó el banco para que subiera.

---

## 6. Contraste con el estado del arte

Contrastar con un producto comercial maduro no es una cortesía: es la única
manera de saber si las decisiones tomadas aquí son razonables o caprichosas.

> **Precisión sobre la fuente.** Lo que sigue procede de una captura de
> **Ikaros 7 (MetaSystems)**, software comercial de cariotipado asistido. **No
> es el sistema que usa este laboratorio** — el laboratorio trabaja con
> **MetaClass** (base SQL Server `SCAMC`, 48 tablas), que es lo que este
> proyecto reemplaza. Ikaros se usa aquí como **referencia externa del estado
> del arte**, no como el sistema desplazado.

### 6.1 Tres decisiones que el estado del arte confirma

**Su salida se llama «Proposal», no diagnóstico.** En pantalla, abajo a la
izquierda: `Proposal 47,XXY`. Un producto de referencia presenta el cariotipo
como **propuesta** que el citogenetista acepta o corrige — exactamente el papel
que cumple aquí la semaforización. Que la IA proponga y la persona decida no es
una limitación de este proyecto: es cómo funciona el estándar del sector.

**Cuenta células analizadas.** El panel inferior muestra `Analyzed Cells: 9` y
`Karyogramm Count: 9` como campos de primer nivel. Es el mismo dato que el
informe del laboratorio expresa como `[20]` y que aquí falta (§7). La necesidad
de un caso multi-metafase queda validada por un producto real, no solo por la
lectura de un informe.

**Expone un control manual del umbral de segmentación** (`Lower Threshold`).
Incluso el software comercial asume que ninguna segmentación automática basta y
le entrega la perilla al analista. La sub-segmentación medida en §5.1 no es una
carencia exclusiva de este prototipo: es el estado del problema.

### 6.2 Lo que el estado del arte hace y aquí no está

`Est. Overlaps: 0` — **mide los solapamientos y los muestra como métrica**, para
que el analista decida si una metafase merece su tiempo *antes* de invertirlo.
Es el problema de sub-segmentación convertido en un número accionable.

Aquí eso está **decidido y sin construir**:
[ADR-0026](adr/0026-estimacion-bandas-solapamientos.md) —«Estimación de conteo
de bandas y detección de solapamientos»— está en estado `accepted` desde el 5 de
agosto, **antes** de ver esa pantalla. La comparación no originó la idea: la
valida.

### 6.3 Mapa de operaciones

| Operación en Ikaros 7 | Equivalente aquí |
|---|---|
| Auto Separate | ✅ `SPLIT` |
| Classify | ✅ `CORRECT_CLASS` |
| Check Objects | ✅ `XAI_VIEWED` + `ACCEPT_CHROMOSOME` |
| Region | ✅ `RECROP` |
| Count | ✅ conteo por clase |
| **Reject Objects** | ❌ no se puede descartar una detección |
| **Annotate** | ❌ falta anotar sobre la metafase |
| **Estimate Band Count** | ❌ ADR-0026, sin construir |

**Cinco de ocho**, y las tres ausentes están identificadas con su decisión
escrita. Ninguna es un descubrimiento tardío.

### 6.4 Lo que este contraste no dice

No dice que este sistema compita con un producto comercial certificado y en uso
clínico; esto es un prototipo cuyo coste de corrección se midió y salió
desfavorable (§5.1).

Y tampoco dice que el laboratorio use ese producto. **Lo que este proyecto
reemplaza es MetaClass**, del que se conserva hasta el esquema de base de datos
y del que salieron las 1.113 imágenes usadas para entrenar el clasificador.

Lo que sí dice es que **las decisiones de diseño apuntan en la misma dirección
que el producto de referencia**, y que las diferencias son de madurez, no de
criterio.

---

## 7. Lo que falta, sin maquillar

**El detector.** La segmentación junta cromosomas que se tocan, y ese recorte
malo produce clasificaciones erróneas. La vía de fondo es U-Net; la vía
inmediata es RECROP, la herramienta de recorte manual que se construyó este
módulo.

**El caso multi-metafase.** El laboratorio analiza **20 metafases por caso** y
reporta el consenso — por eso el informe real dice `47,XY,+21[20]`. El sistema
guarda N imágenes pero `Karyotype` es `OneToOne` con `Sample`: analiza solo la
primera y no hay dónde guardar el consenso. **Es lo que separa esto de un
informe clínico emitible**, y es un cambio de modelo, no un parche.

**El pipeline corre síncrono.** Celery está declarado en el stack pero no
implementado: una metafase pesada bloquea el hilo de la petición (ADR-0031).

**La memoria del nivel 5 gana 4 de 8.** El checkpoint persiste siempre; lo que
falla es que `llama3.2:3b` lo aproveche — vuelve a consultar las herramientas en
vez de leer el historial. El límite es el modelo, no la arquitectura.

---

## 8. Trazabilidad documental

| ADR | Decisión |
|---|---|
| **0027** | Similitud vectorial para enrutar consultas — medido y acotado |
| **0028** | Corpus clínico para fundamentar la narrativa |
| **0029** | RAG documental sobre el corpus del proyecto (D1–D7) |
| **0030** | Un agente ReAct con guardrails, herramientas por MCP |
| **0031** | La orquestación es una cola de tareas, **no** multiagente |
| **0032** | Memoria conversacional con LangGraph, sin estado clínico |

Cada decisión llegó **después** de una medición, no antes. Es la diferencia
entre elegir una tecnología y justificarla.

---

## 9. Cómo reproducir todo

```bash
# servicios
cd backend-ml      && python -m uvicorn app.main:app --port 8000
cd backend-admin   && .venv/Scripts/python manage.py runserver 127.0.0.1:8001 --noreload
cd backend-clinic  && CLINIC_LLM_ENABLED=true .venv/Scripts/python manage.py runserver 127.0.0.1:8002 --noreload
cd frontend-clinic && npm run dev            # :5174

# los seis niveles de la escalera
cd backend-clinic
.venv/Scripts/python manage.py demo_llm          # niveles 0 y 1
.venv/Scripts/python manage.py demo_tools        # nivel 2 — los 4 escenarios
.venv/Scripts/python manage.py demo_sugerencias  # nivel 3 — RAG + paso 6
.venv/Scripts/python manage.py demo_agente       # nivel 4 — bucle + traza
.venv/Scripts/python servidor_mcp.py             # publica 6 tools por stdio
.venv/Scripts/python cliente_mcp.py              # las descubre SIN import

# las mediciones
.venv/Scripts/python manage.py eval_enrutado
.venv/Scripts/python manage.py eval_rag --con-juez
.venv/Scripts/python manage.py eval_memoria
cd ../backend-ml && python training/eval_correccion.py

# la suite
cd backend-clinic && .venv/Scripts/python -m pytest
```

---

*Repositorio: `github.com/guillemc92/karyoumss`, rama `feature/clinic-django-stack`*
