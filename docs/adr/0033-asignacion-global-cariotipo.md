---
id: ADR-0033
title: Asignación global con cupos blandos — el modelo propone la clase, el código reparte el cariotipo
date: 2026-08-21
status: proposed
related: [ADR-0007, ADR-0021, ADR-0026, ADR-0024]
---

# ADR-0033: Asignación global del cariotipo (cupos blandos)

## Contexto

En el nivel 2 de la escalera de integración este proyecto adoptó una regla que
ha resultado ser la más útil de todo el módulo: **el modelo elige, el código
produce**. El LLM devuelve el nombre de una herramienta y ahí termina su
participación; las filas las genera Django ORM. Lo mismo con el diagnóstico: el
LLM redacta la narrativa pero `generate_iscn()` calcula la nomenclatura
(ADR-0024 D1).

**La capa clínica no respeta esa regla.** `EfficientNetClassifier.classify_all`
clasifica cada recorte de forma independiente y su `argmax` **es** el cariotipo:
la salida del modelo se persiste tal cual en `Chromosome.predicted_class`, sin
que ningún código compruebe después si el conjunto tiene sentido.

Y un cariotipo tiene una estructura que el clasificador desconoce por completo:
**de cada autosoma hay dos copias**. Clasificando 46 objetos por separado, nada
impide una salida con nueve cromosomas 1 y ningún 17 — biológicamente
imposible, y sin embargo perfectamente alcanzable con el diseño actual.

Esa restricción es conocimiento del dominio, no del modelo. Le toca al código.

## Medición

Todo sobre la partición de **validación** del cuaderno v3 (semilla 42, 15 % por
cariograma: el modelo no los vio al entrenar), con el modelo
`efficientnet-b3-metaclass-v3`. La partición se dividió en dos mitades sin
solape: los casos 0–29 (1.306 cromosomas) para **ajustar** la penalización, y
los casos 30–63 (1.478 cromosomas) como **banco nuevo** para comprobarla.

| Penalización | Banco de ajuste | Banco NUEVO |
|---|---:|---:|
| 0 (sin cupo) | +0,00 pp | −0,14 pp |
| 0,5 | +0,84 pp | **+1,42 pp** |
| **1,0** | **+1,45 pp** | **+1,22 pp** |
| 2,0 | **+1,99 pp** | +0,95 pp |
| 4,0 | +1,76 pp | +0,47 pp |
| 8,0 | +1,15 pp | +0,20 pp |
| Cupo duro (prohíbe la 3ª copia) | +1,15 pp | +0,20 pp |

Base `argmax`: 72,89 % en el banco de ajuste, 74,90 % en el nuevo.

Reproducible con `python training/eval_asignacion.py --casos 30` y
`python training/eval_asignacion.py --desde 30 --casos 34`.

### Lo que enseñó el banco nuevo

La primera versión de este ADR proponía **penalización 2,0**, porque era el
máximo del banco de ajuste (+1,99 pp). En datos no vistos rinde **+0,95 pp**:
**la mitad**. Estaba sobreajustada, y el propio ADR lo tenía declarado como
riesgo pendiente antes de comprobarlo.

Dos conclusiones, y la segunda importa más que la primera:

1. **El efecto es real y sobrevive.** Todas las penalizaciones entre 0,5 y 8,0
   ganan en el banco nuevo. No es un artefacto del ajuste.
2. **La ganancia honesta no es +1,99 pp.** Es la que da el parámetro elegido
   sobre datos que no participaron en elegirlo: alrededor de **+1,2 pp**.

### El otro camino: sobre metafases reales

Lo anterior se mide sobre los **recortes limpios del experto**. El sistema en
producción no ve eso: ve lo que produce la segmentación sobre una metafase
cruda, que es mucho peor (`eval_dos_caminos.py`: la confianza media cae de
0,746 a 0,509). Por ese camino **no se puede medir acierto** —la segmentación
no produce los mismos objetos que el experto, no hay con qué parear— pero sí
las dos cosas observables.

Sobre 443 cromosomas de 10 metafases de validación
(`eval_asignacion_metafase.py`):

| | `argmax` (hoy) | Reparto |
|---|---:|---:|
| Copias imposibles (>2 por clase) | **259** | **105** |
| Confianza media | 0,511 | 0,323 |
| Cromosomas en naranja | 94 % | 95 % |

**El riesgo que se temía no se materializó.** La confianza cae mucho —al mover
un cromosoma fuera de su `argmax`, la probabilidad del modelo para la clase
nueva es menor (D4)— y eso hacía temer una avalancha de naranjas y, con ella,
más trabajo de revisión. Medido: **+4 naranjas sobre 443**. La caída ocurre casi
toda **por debajo** del umbral, donde ya no cambia ninguna decisión: con el 94 %
del caso ya en naranja, el semáforo está saturado.

El balance medido es **154 copias imposibles menos a cambio de ~8 acciones**.

**Pero esto es cierto solo mientras la segmentación siga siendo mala.** Si
mejora y las confianzas suben, una parte de la caída pasaría a cruzar el umbral
y el balance habría que volver a medirlo. Queda anotado como condición, no como
resultado permanente.

**Y hay un dato que obliga a la trazabilidad:** el reparto mueve **el 53 % de
los cromosomas** fuera de la clase que el modelo había elegido. El analista ve
una clase que no es la propuesta del modelo en uno de cada dos casos. Sin
registrarlo, esa decisión no es auditable (ver pendiente 3).

## Decisión

### D1 — El clasificador entrega probabilidades, no clases

`classify_all` pasa a exponer la distribución completa sobre las 24 clases.
El `argmax` deja de ser la salida del sistema y pasa a ser una de las entradas
del repartidor.

### D2 — El reparto es una asignación global de coste mínimo

Se construye una matriz de coste `-log p(clase)` entre los cromosomas
detectados y las plazas disponibles, y se resuelve con asignación húngara. La
salida es el reparto que maximiza la probabilidad conjunta **respetando la
estructura del cariotipo**, no la suma de decisiones locales.

Se implementa el algoritmo en el propio repositorio (~50 líneas,
Jonker-Volgenant). **No se añade scipy** como dependencia para una sola
función: es la regla del nivel mínimo aplicada a la infraestructura, la misma
que llevó a usar NumPy por fuerza bruta en vez de ChromaDB (ADR-0029 D3).

### D3 — El cupo es BLANDO, y esta es la decisión que más importa

Cada clase recibe **2 plazas libres y 2 penalizadas**. La tercera copia sigue
siendo posible, pero el modelo tiene que sostenerla con evidencia fuerte.

Un cupo duro de dos copias haría el sistema **estructuralmente incapaz de
diagnosticar una trisomía** — es decir, incapaz de detectar el síndrome de
Down, que es el hallazgo más frecuente del laboratorio. Un sistema que no puede
representar la anomalía que busca no es un sistema clínico.

La medición lo confirma además por la vía práctica: el cupo duro es la peor de
las configuraciones con cupo en **los dos** bancos (+1,15 y +0,20 pp), porque
gana rigidez y pierde los casos anómalos.

**Penalización adoptada: 1,0**, y no se elige por ser la mejor de ningún banco
—precisamente por eso—. Es la más **estable**: +1,45 pp en el de ajuste y
+1,22 pp en el nuevo, la única que se mantiene por encima de +1,2 en ambos. El
máximo de cada banco (2,0 y 0,5 respectivamente) no coincide, y quedarse con
cualquiera de los dos sería repetir el error que el banco nuevo acaba de
destapar.

Tiene además lectura directa: el coste está en `-log p`, así que penalizar con
1,0 significa que **una tercera copia solo se acepta si es unas 2,7 veces más
probable** que colocar ese cromosoma en otra parte. Es un criterio que se puede
discutir con un citogenetista; «2,0 porque midió mejor» no lo es.

Queda como constante con nombre, no como número incrustado.

### D4 — La confianza que se persiste sigue siendo la del modelo

`Chromosome.confidence_score` continúa guardando la probabilidad que el
clasificador asignó a la clase finalmente elegida. La semaforización (RN-02) no
cambia de fuente: el reparto decide la clase, no la confianza.

Es deliberado. Mezclar el coste de la asignación con la confianza del modelo
produciría un número que no significa nada clínicamente y que rompería la
comparabilidad con todas las mediciones anteriores.

### D5 — Se declara en la cadena de versión

La cadena pasa a incluir el sufijo del repartidor, p. ej.
`opencv-watershed-v0+efficientnet-b3-metaclass-v3+asignacion-p1.0`. Un caso
tiene que decir qué produjo su resultado, o la trazabilidad clínica miente
(misma regla que ADR-0021).

## Consecuencias

**A favor**

- **+1,2 pp de acierto sobre datos no vistos**, a coste de cómputo
  despreciable frente a los ~30 s que ya tarda la inferencia. La ganancia se
  comprobó en un banco que no participó en elegir el parámetro.
- **Sobre metafases reales, 154 copias imposibles menos** (259 → 105) a cambio
  de ~8 acciones de revisión. Es la única mejora del núcleo clínico medida en
  el camino que el sistema usa de verdad.
- Se aplica al núcleo clínico la regla que mejor ha funcionado en la capa
  conversacional: el modelo propone, el código decide.

**En contra, y hay que decirlo**

- **La ganancia es modesta.** Un punto y pico no convierte un prototipo en
  herramienta clínica: el cuello de botella sigue siendo la segmentación, que
  no tiene verdad de terreno (ver `eval_dos_caminos.py`).
- **La asignación puede empeorar un cromosoma concreto.** Al optimizar el
  conjunto, un cromosoma que el `argmax` acertaba puede acabar en otra clase
  para que encaje el reparto. Sube el total y puede bajar el caso individual.
  El analista ve el resultado del reparto, no el del `argmax`, y esa diferencia
  debe quedar en la bitácora.
- **El reparto mueve el 53 % de los cromosomas** fuera de la clase que eligió
  el modelo. Es mucho, y hace obligatorio el registro en bitácora: sin él, la
  mitad de las clases que ve el analista no se pueden explicar.
- **El balance del semáforo depende de que la segmentación siga siendo mala.**
  Hoy el 94 % del caso ya está en naranja, así que la caída de confianza no
  cambia decisiones. Si la segmentación mejora, hay que volver a medirlo.
- **La ganancia es sensible al parámetro.** Entre 0,5 y 2,0 el efecto va de
  +0,95 a +1,42 pp según el banco, y los óptimos de cada mitad no coinciden.
  Se eligió por estabilidad, no por máximo, pero con dos bancos de 30 casos no
  se puede afinar más de lo que se ha afinado.

## Alternativas descartadas

**Cupo duro de dos copias.** Descartada por D3: prohíbe el diagnóstico que el
laboratorio más emite, y además mide peor.

**Reentrenar el clasificador con la restricción dentro.** Mucho más caro, y
mete conocimiento del dominio en unos pesos donde nadie puede auditarlo. La
restricción escrita en código se lee, se prueba y se discute.

**Un agente que revise la coherencia del cariotipo.** Es exactamente el
antipatrón que la guía del módulo penaliza: un nivel de integración más alto
del que el problema necesita. Esto es un problema de asignación con solución
exacta conocida; no necesita un modelo de lenguaje.

## Pendiente antes de pasar a `accepted`

1. ~~Medir la penalización sobre un banco **nuevo**, no el de ajuste.~~
   **Hecho el 21/08/2026**, y cambió la decisión: 2,0 → 1,0. Ver §Medición.
2. Decidir si el reparto queda tras un interruptor (`CLINIC_ASIGNACION_ENABLED`)
   para poder comparar en producción, como se hizo con `CLINIC_LLM_ENABLED`.
3. Registrar en la bitácora cuándo el reparto cambió la clase respecto al
   `argmax`. Deja de ser deseable y pasa a ser **bloqueante**: se midió que
   afecta al **53 %** de los cromosomas, así que sin ese registro la mitad de
   lo que ve el analista es una decisión del código que nadie puede auditar.

## Implementación

Hecha el 21/08/2026, **apagada por defecto** porque este ADR sigue en
`proposed`:

- `backend-ml/app/asignacion.py` — húngaro + reparto con cupos (sin scipy)
- `backend-ml/app/efficientnet.py` — interruptor `ML_ASIGNACION_ENABLED`
- `backend-ml/tests/test_asignacion.py` — 11 pruebas; la primera fija que **no
  se prohíbe una trisomía**
- `backend-ml/training/eval_asignacion.py` y `eval_asignacion_metafase.py` —
  los dos instrumentos de esta medición
