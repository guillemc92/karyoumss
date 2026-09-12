---
id: ADR-0029
title: RAG documental sobre el corpus del proyecto, con el modelo como juez de pertinencia
date: 2026-08-16
status: accepted
related: [ADR-0027, ADR-0028, ADR-0024]
---

# ADR-0029: RAG documental sobre el corpus del proyecto

## Contexto

El sistema sabe responder **qué hay** —las cuatro herramientas de `tools.py`
consultan el estado del flujo clínico— pero no sabe responder **por qué**.

Medido con el banco de 56 preguntas de `eval_enrutado` (ADR previo al tool
calling), seis caen sistemáticamente en `SIN_MATCH`:

```
«¿Qué significa que un cromosoma esté naranja?»
«¿Cómo se calcula la nomenclatura ISCN?»
«¿Quién tiene permiso para firmar un caso?»
«¿Qué umbral de confianza deberíamos usar?»
```

Son preguntas de documentación, no de estado. La respuesta existe —está en el
estándar ISCN 2024, en los ADRs y en AGENTS.md— pero el sistema no puede
alcanzarla. Ninguna clave exacta las resuelve, que es justo lo contrario del
caso de ADR-0028.

**Esto NO reabre ADR-0027.** Aquel midió la recuperación vectorial sobre datos
**estructurados** (enrutar preguntas a herramientas) y la rechazó con razón: la
clave exacta ya existía y el vector solo añadía imprecisión. Aquí no hay clave.

## Decisión

### D1 — Se indexa documentación, no filas de la base

El corpus son 1.144 fragmentos del estándar ISCN 2024, los 28 ADRs, el FSD, el
BRD y AGENTS.md. **No se indexa ninguna tabla**: el estado lo siguen resolviendo
las herramientas, que son exactas y cuestan milisegundos.

La frontera es la forma de la pregunta, no el tema: si se responde con una lista
de casos o cromosomas que existen ahora, hay herramienta; si pide una
explicación, una definición o una regla, hay RAG.

### D2 — Troceado por secciones, no por longitud ciega

Cortar cada N caracteres parte definiciones a la mitad. Como todas las fuentes
son Markdown con encabezados, se trocea respetando la jerarquía y cada fragmento
arrastra su cadena de secciones («ISCN 2024 — 5.2 Sexo»). Eso sirve para dos
cosas: da contexto al modelo de embeddings y **permite citar la procedencia
exacta**, que en un sistema clínico no es opcional.

### D3 — Sin base de datos vectorial

Son 1.144 fragmentos de 768 dimensiones. Buscar por fuerza bruta es un producto
matriz-vector que NumPy resuelve en microsegundos. Montar pgvector, FAISS o un
servicio en la nube añadiría infraestructura, despliegue y un punto de fallo
más sin ganar nada medible.

El índice es un fichero (`.npy` + `.json`, 2,9 MB) **versionado con el código**.
Si el corpus creciera dos órdenes de magnitud, esta decisión se revisa;
`Indice.buscar()` es la única función que habría que cambiar.

### D4 — El umbral de similitud NO decide si responder

Este es el hallazgo que ordena el diseño. Medido sobre 18 preguntas etiquetadas:

| | similitud del top-1 |
|---|---|
| preguntas cubiertas por el corpus | 0.601 – 0.695 |
| preguntas **fuera** del corpus | 0.608 – 0.662 |

El rango a rechazar cae **dentro** del rango bueno. El barrido de 0.50 a 0.75 da
**56% de acierto en todos los valores útiles**: con umbral bajo responde a todo
(abstención 0/6), con umbral alto abstiene bien pero pierde 10 de 12 preguntas
legítimas.

No es falta de calibración ni un mal modelo de embeddings: el coseno mide
parecido **temático** y el corpus es monotemático. «¿Cuál es el teléfono del
doctor Rojas?» recupera un ADR sobre el rol de administrador con 62,9% — más que
algunas preguntas válidas. Es el mismo fenómeno de ADR-0027, reproducido sobre
documentos.

**Se separan responsabilidades:** el índice **recupera** con umbral bajo
(orientado a recall) y el **modelo decide** si esos fragmentos responden. Es la
misma regla que rige el resto del sistema —el modelo decide, el código
produce— aplicada a la pertinencia.

### D5 — Las citas se resuelven contra los candidatos reales

Si el modelo cita un fragmento que no existe, se ignora en vez de inventar una
fuente. Una respuesta clínica sin fuente verificable no vale, y una con fuente
falsa es peor que ninguna.

### D6 — Con la IA apagada, el RAG no responde

Sin juez no hay forma de saber si los fragmentos son pertinentes. Se prefiere
callar antes que volcar el fragmento más parecido y dejar que el usuario decida.
El camino KEYWORD sigue funcionando (RN-07: degradar, no romper).

### D7 — Las sugerencias comparan el ranking, no confían en el puntaje

El paso 6 de la consigna pide «comparar porcentajes de similitud para ofrecer
la respuesta más óptima y sugerencias apropiadas». Antes de construirlo se
midió si el puntaje puede sostener esa promesa, sobre el mismo banco de 18:

| señal | cubiertas por corpus | fuera del corpus |
|---|---|---|
| similitud top-1 | 0.601 – 0.695 | 0.608 – 0.662 |
| margen top1−top2 | 0.000 – 0.033 | 0.006 – 0.024 |
| dispersión del top-5 | 0.002 – 0.019 | 0.004 – 0.018 |

**Las tres se solapan**, y en margen y dispersión el rango de las preguntas a
rechazar queda *contenido dentro* del de las buenas: no existe corte. El mejor
umbral concebible sobre cualquiera acierta 67-72%, por debajo del 89% del juez.
Es la tercera confirmación del mismo fenómeno (D4, y ADR-0027 sobre tablas).

Hallazgo secundario, más útil: **los márgenes son diminutos** —los candidatos
llegan separados por milésimas—. «El fragmento más parecido es la respuesta» no
se sostiene: el top-1 no destaca lo suficiente como para que la diferencia
signifique algo.

En consecuencia: la **respuesta más óptima la elige el juez, no el puntaje**, y
ninguna sugerencia afirma pertinencia. Solo puede decir *«esto es lo más
parecido que hay»*. El valor está en el caso de abstención, donde convierte un
«no sé» en una pista para reformular.

Al ejecutarlo contra el índice real aparecieron dos defectos que el diseño en
papel no anticipó, y ambos cambiaron el código: al explorar, las tres primeras
sugerencias eran tres secciones del **mismo** documento (ahora `explorar`
agrupa por documento y `ampliar` por sección), y las secciones venían como
migas de pan ilegibles heredadas del troceador (ahora se muestra el último
tramo). La búsqueda pasó a traer 8 vecinos en vez de 3 —sin coste: el mismo
ranking ya calculado— porque con 3 solo se podía sugerir un sitio; el juez
sigue viendo 3.

## Consecuencias

**Resultado medido** (`manage.py eval_rag --con-juez`, 18 preguntas):

| | Global | Cubiertas | Fuera del corpus |
|---|---|---|---|
| Solo recuperación | 56% | 83% | 0% |
| Con juez, prompt v1 | 39% | 8% | 100% |
| **Con juez, prompt v2** | **89%** | **83%** | **100%** |

El prompt del juez se midió **dos veces**. La v1 decía «ante la duda,
responde=false» y el modelo tomó la duda por norma: se abstuvo en 11 de 12
preguntas cubiertas, **peor que no tener juez**. La v2 invierte el defecto
—responder es lo normal, abstenerse la excepción acotada— y recorta el contexto
de 5 fragmentos × 2.000 caracteres a 3 × 900. La latencia cayó de 420-671 s a
27-200 s: un modelo de 3B con 10.000 caracteres de contexto se ahoga.

**Advertencia sobre ese 89%:** de 72% a 89% el código no cambió. Tres de los
cinco fallos eran de la vara de medir —el banco exigía fuentes concretas y
rechazaba respuestas correctas por venir del BRD o de un ADR— y se corrigieron
por mérito. La mejora real del sistema es la de v1 a v2.

**Lo que no funciona:** dos preguntas cubiertas siguen sin responderse (permisos
de firma, protección de PII). Es el peaje de bajar de 5 candidatos a 3.

**Alucinación observada:** preguntado por «46,XY» acertó el contenido pero
inventó la expansión de la sigla ISCN. Fundamentar en fragmentos no impide que
el modelo adorne — mismo fallo que ADR-0024 documentó en la narrativa.

**Pendiente (importante):** el 89% se midió con preguntas escritas por una
persona. Dentro del agente (ADR-0030) las escribe el modelo, y las escribe peor.
Un componente medido aislado **no queda validado** para su uso dentro de un
agente.

## Alternativas descartadas

| Alternativa | Por qué no |
|---|---|
| Subir el umbral y prescindir del juez | Medido: ningún valor supera 56%. Los rangos se solapan |
| Probar otros modelos de embeddings | No es el modelo: es el método sobre un corpus monotemático |
| ChromaDB, como el laboratorio de clase | Base binaria que no se versiona bien. Con 1.144 fragmentos NumPy sobra |
| Indexar también las tablas | ADR-0027 ya lo midió y lo rechazó |

## Implementación

`backend-clinic/apps/samples/rag_corpus.py` (carga y troceado, 10 tests),
`rag_index.py` (embeddings, índice, top-k), `rag_qa.py` (el juez),
`rag_sugerencias.py` (paso 6, puro, 24 tests). Comandos `build_rag_index` y
`eval_rag`. Cuarto camino del enrutador: `KEYWORD → LLM → RAG → SIN_MATCH`.

Las sugerencias viajan en las tres salidas: `Respuesta.sugerencias` del
enrutador, la observación del agente (ADR-0030) —también cuando no encuentra,
para que pueda reintentar con una pregunta mejor en vez de rendirse en el
primer paso— y `RespuestaRag.as_dict()`.
