---
id: ADR-0028
title: Corpus clínico determinístico para fundamentar la narrativa asistida
date: 2026-08-06
status: accepted
refines: [ADR-0024]
related: [ADR-0027]
---

# ADR-0028: Corpus clínico determinístico para fundamentar la narrativa

## Contexto

ADR-0024 documentó una alucinación **medida, no hipotética**: el modelo describió
la trisomía 21 como *«una deficiencia crónica y progresiva de la función
cerebral»* — clínicamente falso. La validación no la detectó porque solo verifica
coherencia citogenética (el `+21` sí estaba en el ISCN), no corrección médica de
la prosa.

La causa es que el modelo redacta **desde su memoria de entrenamiento**. Un 3B
recuerda mal. Nada en el prompt le dice qué es realmente una trisomía 21, así que
confabula algo que suena médico.

## Decisión

### D1 — Búsqueda determinística por clave, NO recuperación vectorial

El ISCN que recibe la narrativa es un **dato estructurado que el propio sistema
generó** con `generate_iscn()`. Para encontrar el contexto clínico de
`47,XY,+21` no hace falta búsqueda semántica: hace falta leer la entrada `+21`.

| | Búsqueda por clave | Recuperación vectorial |
|---|---|---|
| Precisión | 100% (coincidencia exacta) | ~60% medido en ADR-0027 |
| Latencia | microsegundos | decenas de ms + modelo cargado |
| Trazabilidad | se prueba qué entrada se usó | aproximada, por score |
| Dependencias | ninguna | modelo de embeddings |

Es la misma lección que ADR-0027: usar la herramienta que corresponde al
problema. Allí el problema era clasificación fina y RAG fallaba; acá la clave de
búsqueda ya existe y es exacta, así que RAG solo agregaría imprecisión.

**Consecuencia de licencia:** con búsqueda determinística el corpus se compone de
entradas propias que **citan** la sección del estándar, sin reproducir su prosa.
Los hechos citogenéticos no son material protegible; la expresión del documento
publicado sí. Este ADR no incorpora texto de terceros al repositorio.

### D2 — El corpus declara su procedencia y su estado de revisión

Cada entrada lleva `fuente` (la sección del estándar o la referencia clínica),
`revisado_por` y `revisado_el`.

**Las entradas semilla nacen sin revisar** (`revisado_por: null`). Fueron
redactadas por un asistente de IA a partir de conocimiento citogenético general,
**no por un profesional clínico**. Un error ahí sería peor que la alucinación que
este ADR combate: entraría al sistema con apariencia de autoridad verificada.

Por eso el estado de revisión **no es decorativo**:

- El evento de auditoría `NARRATIVE_GENERATED` registra qué entradas
  fundamentaron el texto y **cuántas estaban sin revisar**.
- Un caso cuya narrativa se apoyó en material no revisado queda identificable
  después, para poder rehacerlo si una entrada resulta incorrecta.

El mecanismo lo aporta el sistema; **el contenido lo firma el laboratorio**.

### D3 — El corpus alimenta el prompt; NO reemplaza al modelo

El contexto recuperado entra en el prompt como material de referencia, y el
modelo redacta *sobre* él. No se concatena el corpus como respuesta.

Se mantiene ADR-0024 D1 sin cambios: el LLM **redacta**, nunca calcula. El ISCN
sigue viniendo de la función pura, y el corpus solo aporta el significado clínico
de las anomalías que ese ISCN ya contiene.

**El corpus no es exhaustivo y no debe pretenderlo.** Ante un ISCN sin entrada
—una anomalía estructural rara, por ejemplo— la narrativa se genera igual, con
menos fundamento. Bloquearla por falta de corpus convertiría un vacío
documental en un fallo clínico, y RN-07 lo prohíbe.

### D4 — La validación existente no se relaja

`NarrativaCariotipo.es_coherente_con()` (ADR-0024 D4) sigue verificando que las
anomalías citadas existan en el ISCN. El corpus **reduce** la probabilidad de
alucinación; no la elimina, y no sustituye la verificación estructural.

Tampoco sustituye la revisión humana de D3 en ADR-0024: el texto sigue siendo un
borrador. Un corpus correcto no garantiza que el modelo lo parafrasee bien.

### D5 — El corpus vive en el repositorio, versionado

Un archivo Python con estructuras declarativas, no una base de datos.

Es contenido que cambia con revisión clínica, no con la operación: debe pasar por
el mismo control de cambios que el código —diff, revisión, historia—. Una tabla
en la base lo volvería invisible al versionado y haría imposible reconstruir qué
texto fundamentó un informe de hace seis meses.

## Trade-offs

- **Pros:** ataca una alucinación medida; precisión y trazabilidad exactas; sin
  dependencias nuevas; sin material de terceros en el repositorio; el estado de
  revisión queda auditado por caso.
- **Cons:** cobertura manual —cada anomalía nueva requiere escribir su entrada—,
  a diferencia de un corpus vectorial que absorbe texto a granel. Se acepta
  porque el dominio es acotado (las aneuploidías frecuentes son pocas) y porque
  la alternativa medida rinde 60%. **Y porque las entradas semilla sin revisión
  clínica son una deuda real, no un detalle de formato:** hasta que un
  profesional las firme, el sistema está fundamentando informes con texto que
  nadie del dominio validó.

## Consecuencias

- `apps/samples/corpus.py`: entradas + búsqueda por clave.
- `iscn.py` expone la descomposición de un ISCN en sus anomalías (ya existía
  para validar; se publica para reutilizarla).
- `llm_client._build_prompt()` inyecta el contexto recuperado.
- El evento `NARRATIVE_GENERATED` suma `corpus_entradas` y `corpus_sin_revisar`.
- **Acción pendiente del laboratorio:** revisar y firmar las entradas semilla.
  Mientras `revisado_por` sea `null`, la auditoría lo refleja en cada informe.
