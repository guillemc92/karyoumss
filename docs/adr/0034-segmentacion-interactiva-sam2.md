---
id: ADR-0034
title: Segmentación interactiva asistida (SAM 2) — y la anotación como producto secundario
date: 2026-08-31
status: proposed
related: [ADR-0007, ADR-0021, ADR-0026, ADR-0033, ADR-0035]
---

# ADR-0034: Segmentación interactiva asistida por SAM 2

## Contexto

### El problema que se creía tener

El analista corrige a mano los cromosomas que la segmentación automática juntó,
partió o se dejó. Hoy dispone del recorte rectangular (RECROP,
`POST /samples/{id}/chromosomes/{cid}/recrop/`): dibuja una caja sobre el
lienzo Konva y el servidor reclasifica con el recorte nuevo.

Un rectángulo no separa dos cromosomas que se tocan. Para eso haría falta una
herramienta de píxel, que produce fatiga visual y es lenta.

### El problema que de verdad se tiene

Medido el 21/08/2026 (`eval_dos_caminos.py`), sobre 12 casos que el modelo no
vio al entrenar:

| | Recortes del experto | Desde la metafase |
|---|---:|---:|
| Confianza media | 0,746 | 0,509 |
| Cromosomas en naranja | 54 % | 94 % |
| Acierto contra el experto | 74,9 % | **no medible** |

La última fila es la que ordena todo lo demás. Por el camino de la metafase
**no se puede puntuar la segmentación**, porque no produce los mismos objetos
que el experto y no hay con qué parear.

Al buscar la causa aparece el hecho central: **el dataset no tiene ni una
máscara ni una caja sobre ninguna metafase.** `crops_manifest.csv` solo tiene
`file, class, source`, y `source` es el **cariograma** —una imagen ya
reordenada por el citogenetista—, no la metafase. Los 48.467 recortes no se
pueden mapear a coordenadas de la imagen original.

Consecuencia: **no se puede entrenar un detector, y tampoco se puede medir uno.**
Esa es la razón de que ADR-0035 no pueda decidirse todavía.

### La observación que une los dos problemas

Cuando un analista hace clic para separar dos cromosomas fusionados, está
produciendo exactamente el dato que falta: **la frontera entre dos instancias
sobre una metafase real, validada por un experto**.

La herramienta de corrección no es solo ergonomía. Es el pipeline de anotación.

## Decisión

### D1 — SAM 2 como asistente de segmentación interactiva

Se integra SAM 2 en el visor de cariotipo (React + Konva, ADR-0021 P3) para que
el analista corrija con clics en vez de con píxeles:

- **clic positivo** sobre el fragmento que la IA omitió → la máscara lo absorbe
- **clic positivo en A + clic negativo en B** sobre dos cromosomas fusionados →
  el modelo traza la frontera

Se elige SAM 2 por su capacidad *zero-shot*: no hay que entrenarlo con
cromosomas para que responda a estímulos geométricos. Es justo lo que hace
falta cuando no hay datos anotados — que es el punto de partida.

### D2 — Cada corrección se persiste como anotación

Toda máscara aceptada por el analista se guarda asociada a `(SampleImage,
coordenadas)`, con el actor y el instante. No es telemetría: es el corpus de
entrenamiento y evaluación de ADR-0035, construido por el uso normal del
sistema.

**Es el motivo principal de este ADR, no un efecto colateral.** Sin esto,
ADR-0035 no puede ejecutarse nunca.

### D3 — El embedding se calcula una vez por imagen y se cachea

SAM 2 tiene dos mitades de coste muy distinto: el codificador de imagen es
pesado (segundos en CPU) y el decodificador de máscara es barato
(milisegundos). Se codifica **una sola vez** al abrir el caso y se cachea; cada
clic posterior solo ejecuta el decodificador.

Sin esta separación, la promesa de «respuesta instantánea al clic» es falsa en
una máquina sin GPU — que es la máquina donde corre este sistema.

### D4 — Transporte: REST síncrono, no WebSockets

Un clic produce una petición y espera una máscara. Es una interacción
petición-respuesta, y el endpoint de recorte ya existente
(`ChromosomeRecropView`) ya tiene esa forma.

WebSockets añadiría estado de conexión, reconexión y un modo de fallo nuevo
para resolver un problema que no se tiene. Es la regla del nivel mínimo, la
misma que llevó a NumPy en vez de ChromaDB (ADR-0029 D3) y a una cola de tareas
en vez de siete agentes (ADR-0031).

Si se mide latencia inaceptable con el embedding ya cacheado, se reabre.

### D5 — Inferencia local, como el resto (RN-03)

SAM 2 corre en `backend-ml`, en la misma máquina. Las metafases son datos
clínicos y RN-03 exige cero fuga: no salen a ningún servicio externo, igual que
el LLM corre en local con Ollama (ADR-0024).

### D6 — El analista acepta o descarta; SAM 2 no escribe solo

Una máscara propuesta no modifica el caso hasta que el analista la acepta. Es
la misma regla que gobierna toda la capa de IA de este proyecto: **el modelo
propone, la persona decide** — y en el núcleo clínico, además, queda en la
bitácora encadenada (RN-05).

## Cómo se sabrá si funcionó

Sin criterio de éxito esto no es una decisión, es una intención. Se mide contra
la línea base ya establecida (`eval_correccion.py`: mediana de **64 acciones**
por caso frente a **46** de hacerlo a mano):

1. **Acciones por caso** con la herramienta nueva frente a las 64 actuales.
2. **Máscaras anotadas acumuladas** por semana de uso — el indicador de que D2
   está cumpliendo su función.
3. **Tiempo por corrección**, medido en el propio flujo, no estimado.

El objetivo declarado es bajar de 46. No se afirma que se vaya a conseguir.

## Consecuencias

**A favor**

- Ataca el cuello de botella real (separar cromosomas que se tocan), no el
  clasificador, que ya se midió que no es el problema.
- **Genera el dataset que hoy no existe**, y sin el cual ADR-0035 es inejecutable.
- Zero-shot: útil desde el primer día, sin esperar a tener datos.

**En contra, y hay que decirlo**

- **Un modelo grande más en una máquina sin GPU.** El pipeline actual ya tarda
  26–32 s por metafase. Hay que medir el coste del codificador antes de
  prometer interactividad.
- **Las anotaciones tendrán sesgo de selección**: solo se anota lo que el
  analista corrige, es decir, los casos donde la segmentación automática falló.
  Un detector entrenado solo con eso ve un mundo más difícil que el real. Hay
  que registrarlo y compensarlo en ADR-0035.
- **Las máscaras heredan la calidad de SAM 2**, que no fue entrenado con
  cromosomas. Son verdad de terreno *asistida*, no verdad de terreno pura, y en
  el corpus debe quedar marcado cuáles se aceptaron sin retoque.

## Alternativas descartadas

**Herramienta de pincel píxel a píxel.** Es lo que el draft original quería
evitar, y con razón: fatiga visual y lentitud. Pero conviene decir el motivo
real por el que se descarta — no es que sea fea, es que **nadie la usaría lo
bastante como para producir corpus**.

**Seguir solo con RECROP rectangular.** Ya existe y es barato, pero un
rectángulo no separa dos objetos que comparten píxeles. Se mantiene: SAM 2 lo
complementa, no lo sustituye.

**Esperar a tener un detector mejor antes de tocar la interfaz.** Es el orden
inverso y no se puede: sin anotaciones no hay detector. Este ADR va **antes**
que ADR-0035, no después.

## Pendiente antes de pasar a `accepted`

1. Medir el coste del codificador de SAM 2 en la máquina real, sin GPU. Si el
   embedding tarda más de unos pocos segundos por metafase, D3 no basta y hay
   que replantear.
2. Definir el esquema de persistencia de las máscaras (D2) — es lo que
   determina si el corpus servirá para entrenar o solo para auditar.
3. Decidir qué se hace con las máscaras de casos ya firmados: RN-04 y RN-05
   hacen el caso inmutable, así que la anotación debe vivir fuera del registro
   clínico o el modelo de datos no cuadra.
