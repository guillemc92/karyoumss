---
id: ADR-0027
title: Enrutado por similitud vectorial (RAG) como tercer camino del tool calling
date: 2026-08-05
status: rejected
rejected_date: 2026-08-05
refines: [ADR-0024]
---

# ADR-0027: Enrutado por similitud vectorial como tercer camino — RECHAZADO

> ⛔ **RECHAZADO el mismo día de su redacción, antes de escribir código.** La
> propuesta se midió contra tres modelos de embeddings y **ninguno alcanzó una
> precisión utilizable**. Se conserva el documento —en vez de borrarlo— porque la
> medición que lo refuta es el resultado más valioso del ejercicio: explica por
> qué RAG *no* es la herramienta correcta para este problema, y evita que alguien
> vuelva a proponerlo dentro de seis meses.

## Contexto (la motivación era real)

El tool calling resuelve las consultas por dos caminos: coincidencia literal con
el vocabulario del catálogo (`KEYWORD`) o elección del LLM (`LLM`). La medición
expone un problema de costo genuino:

| Camino | Latencia medida |
|---|---|
| `KEYWORD` | **7-8 ms** |
| `LLM` | **~98.000 ms** |

El camino LLM es **doce mil veces más lento**, y cae sobre el caso más común: el
usuario que pregunta con sus palabras en vez de las del catálogo.

La hipótesis era razonable: vectorizar las descripciones de las herramientas y
resolver la paráfrasis por similitud coseno, en milisegundos. El docente del
módulo lo había sugerido en la Clase06 (03/08/2026): *«aquí has puesto el tema de
vectores, aquí podrías haber ingresado el tema de sinónimos, y esas dos
herramientas podrías empezar a jugarlas a tu favor con un tooling»*.

## La medición que lo refutó

Antes de implementar, se midió con **7 consultas** (5 sinónimos con respuesta
conocida + 2 fuera de alcance) contra las 4 descripciones del catálogo real.

| Modelo | Dim | Aciertos | ¿Separa aciertos de fallos? |
|---|---|---|---|
| `nomic-embed-text` | 768 | **3/5** | ❌ acierto mín. 0.669 < fallo máx. 0.695 |
| `mxbai-embed-large` | 1024 | 2/5 | ❌ acierto mín. 0.657 < fallo máx. 0.736 |
| `paraphrase-multilingual` | 768 | 2/5 | ✅ pero acierta menos |

Dos hallazgos, y el segundo es el que decide:

**1. Ninguno supera el 60% de aciertos.** El mejor es el primero que se probó;
los modelos más grandes o explícitamente multilingües rinden *peor*.

**2. La consulta del escenario 2 de la consigna falla en los tres.** Ninguno
relaciona *«¿Cuáles necesitan que el analista los mire de nuevo?»* con
`CROMOSOMAS_PARA_REVISION`. Es precisamente el caso que este ADR existía para
acelerar.

En dos de los tres modelos **los rangos se solapan**: no existe un umbral que deje
pasar los aciertos y frene los fallos. Un umbral en 0.65 admite errores; subirlo a
0.70 descarta casi todos los aciertos.

## Por qué falla — y no es el idioma

La causa no es que los modelos manejen mal el español. Es que **las cuatro
herramientas son semánticamente casi idénticas**: todas hablan de casos,
cromosomas, análisis y estados de un laboratorio de citogenética. En el espacio
vectorial quedan superpuestas, y un vector queda «céntrico» y gana consultas que
no le corresponden (`CASOS_PENDIENTES_FIRMA` ganó tres de siete con
`nomic-embed-text`, incluidas dos que no tenían relación).

**RAG resuelve recuperación, no clasificación fina.** Brilla encontrando el
fragmento relevante entre cientos que hablan de cosas distintas. Acá hay que
discriminar entre cuatro opciones casi iguales — otro problema.

El LLM sí lo resuelve, y por eso los 98 segundos se pagan: *razona* que «mirar de
nuevo» implica revisión manual. La similitud coseno no razona, compara ángulos.

## Decisión

**Se rechaza el tercer camino por similitud.** El enrutado se mantiene con los dos
caminos existentes (`KEYWORD` → `LLM` → `SIN_MATCH`), sin cambios.

### Qué hacer en su lugar con el problema de latencia

- **Ampliar el catálogo de palabras clave** con los sinónimos que aparezcan en uso
  real. Es manual y no escala infinitamente, pero cada palabra agregada mueve una
  consulta de 98 s a 7 ms con **100%** de precisión — mejor que el 60% de la
  similitud.
- **Correr el modelo en hardware con GPU.** Los 98 s son de un 3B en CPU; no son
  una propiedad del diseño.
- **Un modelo más chico solo para enrutar.** Elegir un nombre de un enum es una
  tarea mucho más simple que redactar prosa clínica.

### Dónde sí va RAG

En el **corpus clínico de la narrativa asistida** (ADR-0024): recuperar fragmentos
de nomenclatura ISCN y descripciones de síndromes para que el modelo redacte sobre
texto verificado en vez de sobre lo que recuerde. Ahí el problema es de
recuperación sobre material heterogéneo —el que RAG resuelve bien— y ataca la
alucinación clínica real ya documentada en ADR-0024 (el modelo describiendo la
trisomía 21 como «deficiencia crónica y progresiva de la función cerebral»).

## Consecuencias

- El enrutado no cambia. `tool_router.py` y `tools.py` quedan como están.
- Los modelos de embeddings descargados (`nomic-embed-text`, `mxbai-embed-large`,
  `paraphrase-multilingual`) quedan disponibles para el ADR del corpus clínico.
- **Este rechazo es material de entrega**: la consigna del Módulo 6 pide reportar
  «qué no funcionó», y una hipótesis medida y descartada con datos vale más que
  una funcionalidad que anda.
- Si alguien vuelve a proponer enrutado por similitud, la carga de la prueba es
  suya: debe mostrar una medición que supere el 3/5 documentado acá.
