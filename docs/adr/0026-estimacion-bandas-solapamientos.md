---
id: ADR-0026
title: Estimación de conteo de bandas y detección de solapamientos
date: 2026-08-05
status: accepted
refines: [ADR-0006, ADR-0007, ADR-0021]
---

# ADR-0026: Estimación de bandas y solapamientos (métricas de calidad de imagen)

## Contexto

El analista decide qué metafase vale la pena analizar **antes** de invertir tiempo
en corregir su cariotipo. Hoy esa decisión es puramente visual: abre la imagen,
la mira y juzga. Dos señales que un citogenetista usa para ese juicio no están
disponibles en el sistema:

- **Conteo de bandas** — la resolución del bandeo G. Una metafase de 300 bandas
  permite detectar alteraciones que una de 400 no, y una de 550 permite ver
  deleciones submicroscópicas. Es *el* indicador de si la muestra sirve para el
  hallazgo que se busca.
- **Solapamientos** — cuántos cromosomas se tocan o cruzan. Cada solapamiento es
  trabajo manual de separación (P3, ADR-0021) y una fuente de error de
  clasificación.

**Referencia externa (no requisito):** Ikaros 7 de MetaSystems —el estándar
comercial del dominio, IVDR Clase A— publica ambas métricas y las justifica así:
*«permite evaluar rápidamente la calidad de la imagen y reemplaza el conteo
manual tedioso por una verificación rápida de los resultados propuestos»*. Se cita
como validación del valor clínico de la funcionalidad, **no** como compromiso de
paridad de producto.

**Hallazgo del análisis de impacto:** `Chromosome.measures` ya declara
`band_count` en su contrato desde P1 (`{length_um, centromeric_index, band_count,
quality}`), pero **nunca se pobló**. El campo se serializa y se copia en las
operaciones de P3 siempre vacío. Este ADR lo materializa.

## Decisión

### D1 — Son métricas de CALIDAD DE IMAGEN, no de confianza del clasificador

Eje distinto al de ADR-0006. El semáforo mide *cuán seguro está el modelo de la
clase de un cromosoma*; estas métricas miden *cuán utilizable es la imagen*.

Una metafase puede tener todos sus cromosomas en verde y aun así ser inservible
para el hallazgo buscado, por resolución de bandeo insuficiente. Y al revés: una
imagen excelente puede tener naranjas por un cromosoma atípico.

**Consecuencia deliberada: estas métricas NO bloquean nada.** No entran en el
gate de RN-01/RN-02 ni en el de emisión del informe. Son informativas: ayudan al
analista a priorizar, no deciden por él. Convertirlas en gate exigiría validación
clínica que este ADR no tiene.

### D2 — Solapamientos: derivar lo que el segmentador ya sabe

`OpenCVSegmenter` usa watershed sobre la transformada de distancia precisamente
para partir cromosomas que se tocan (ADR-0007, `segmentation.py`). Ese trabajo ya
ocurre en cada procesamiento; hoy **el resultado se descarta**.

Un solapamiento se cuenta cuando un componente conexo de la máscara binaria se
divide en dos o más regiones tras el watershed: el segmentador tuvo que separar
algo que venía pegado. La cuenta se emite a nivel de metafase, no de cromosoma.

Es la parte sólida de este ADR: no estima nada nuevo, expone una señal existente.

### D3 — Bandas: estimación por perfil de intensidad, declarada EXPERIMENTAL

El bandeo G produce, a lo largo del eje mayor del cromosoma, una alternancia de
regiones oscuras y claras. El conteo se estima proyectando la intensidad sobre
ese eje y contando picos, escalado al total del cariotipo según la convención
ISCN (300/400/550/700 bandas).

**Se declara experimental por una razón concreta, no por prudencia genérica: no
hay ground truth.** El dataset MetaClass (1169 cariogramas) no tiene anotación de
resolución de bandeo, así que **la exactitud de esta estimación no se puede medir
con los datos disponibles**. Se publica como orientación —«~300 bandas»— nunca
como dato preciso, y la UI debe reflejar esa incertidumbre.

Si en el futuro se consigue un conjunto anotado, la estimación se valida y este
ADR se refina; hasta entonces, un analista que necesite la resolución exacta
sigue contando a mano.

### D4 — Dónde vive el cálculo

En **backend-ml**, junto al resto del pipeline de visión (ADR-0007). No en Django.

Ambas métricas se derivan de la imagen y de la máscara de segmentación, datos que
solo existen en ese servicio. Calcularlas en Django obligaría a transportar la
imagen y reimplementar el watershed — duplicando la lógica que ADR-0007 puso ahí
justamente para no duplicar.

Se mantiene **Fase 1** de ADR-0007 (monolito modular): ninguno de sus cuatro
triggers de extracción se cumple, y este ADR no los acerca.

### D5 — Persistencia

- **Bandas**, por cromosoma: en `Chromosome.measures['band_count']` — campo que ya
  existe, sin migración.
- **Solapamientos**, por metafase: campo nuevo `Karyotype.overlap_count` (entero,
  `null` cuando el pipeline no lo reportó). Requiere migración.

`null` y `0` significan cosas distintas y no deben confundirse: `null` es «no se
midió» (imagen procesada por una versión previa del pipeline); `0` es «se midió y
no hay solapamientos». La UI debe distinguirlos.

### D6 — Presentación

En el visor (ADR-0021), como panel de calidad junto al cariograma. Nunca mezcladas
con la semaforización: son ejes distintos y unificarlos visualmente induciría a
leer una métrica de imagen como una de confianza.

El conteo de bandas se muestra con marca explícita de estimación (`~300 bandas`,
o similar) por D3.

## Trade-offs

- **Pros:** el analista prioriza antes de invertir tiempo; los solapamientos
  anticipan cuánto trabajo manual de separación implica un caso; se materializa un
  contrato que existía vacío desde P1; ninguna métrica bloquea el flujo clínico.
- **Cons:** el conteo de bandas no es verificable con los datos actuales — se
  entrega como orientación y podría resultar poco fiable en imágenes de baja
  calidad. Se acepta porque la alternativa (no dar ninguna señal de resolución) es
  peor, y porque D1 garantiza que un error no puede propagarse a una decisión
  clínica.

## Consecuencias

- Migración en `apps/samples`: `Karyotype.overlap_count`.
- `SegmentResult` (backend-ml) suma `overlap_count` y `band_count` por cromosoma;
  el contrato es aditivo, así que un backend-ml previo sigue siendo compatible
  (los campos llegan ausentes → `null`).
- El visor suma un panel de calidad (ADR-0021).
- **No se toca** el gate de RN-01/RN-02 ni el de emisión: D1 lo prohíbe
  explícitamente.
- Si se consigue un dataset con resolución de bandeo anotada, D3 debe revisarse en
  un ADR nuevo que lo valide o lo descarte.
