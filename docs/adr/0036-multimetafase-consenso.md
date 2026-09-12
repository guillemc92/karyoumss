---
id: ADR-0036
title: El consenso multi-metáfase se difiere — medido, hoy no hay nada sobre lo que votar
date: 2026-09-08
status: proposed
related: [ADR-0007, ADR-0021, ADR-0025, ADR-0033, ADR-0035]
---

# ADR-0036: Multi-metáfase con consenso (diferida, con el número que lo justifica)

## Contexto

El sistema pide **tres metáfases** al registrar una muestra y **segmenta solo la
primera**:

```python
# services.SampleRegistrationService.register
raw = self._first_image_bytes(data.get('images', []))   # la 1ª que decodifique
```

Las otras dos se guardan en disco y nadie las mira. El paso siguiente del
producto —acordado, no escrito hasta ahora— era **combinar las tres en un
consenso**: segmentar las tres, comparar los cariotipos y usar el acuerdo para
subir la confianza y detectar mosaicismo.

Antes de construirlo hacía falta un dato que nadie había medido: **cuánto se
parecen entre sí los cariotipos que el pipeline produce sobre metáfases
distintas del mismo paciente**.

### Lo que dice el dato real del laboratorio

`datasets/metaclass/labels.csv` trae la columna `IdMuestra`. Las 460 metáfases
anotadas, exportadas de la base real de MetaClass, no son 460 casos:

```
460 metafases -> 28 muestras
con exactamente 20 metafases: 17 muestras
mediana de metafases por muestra: 20
```

**Veinte es el recuento estándar de la citogenética clínica**, y existe
precisamente para detectar mosaicismo: una anomalía presente en una línea
celular y no en otra solo se ve contando muchas células. El laboratorio real
trabaja con una mediana de 20; el sistema sube 3 y mira 1.

## Medición

    cd backend-ml
    python training/eval_multimetafase.py --muestras 10 --tope 6

Sobre 10 muestras reales, 6 metáfases de cada una:

```
  muestras medidas                 : 10
  metafases clasificadas           : 60
  ...que producen un ISCN          : 6 de 60 (10%)
  ...rechazadas por el motor       : 54 de 60 (90%)
  muestras con >=2 ISCN comparables: 1 de 10
  ...donde TODAS coinciden         : 0 de 1
  cromosomas detectados (media)    : 44.0  (esperado 46)
```

El **90 %** de las metáfases no llega siquiera a producir una nomenclatura: el
motor las rechaza, casi siempre por *«sin cromosomas sexuales: el cariotipo
está incompleto»*. De las 6 que sí producen algo, ninguna es clínicamente
plausible:

```
metafase   detec  exceso   ISCN derivado
2          57     40       57,Y,+1,+1,+1,+1,+1,+1,+1,+1,+1,+1,+1,+1,+1,+1,+1,+1,+1,+2
3          46     25       46,Y,+1,+1,+1,+1,+1,+1,+1,+1,+1,+1,+1,+2,+2,+2,+3,+3,+3,+3
107        39     19       39,X,+1,+1,+1,+1,+1,+1,+1,+1,+1,+1,+1,+1,+1,-2,+3,+3,+3,+3
```

«exceso» son las copias por encima de 2 en alguna clase: biológicamente
imposibles. La media es 44 cromosomas detectados con **una veintena de copias
imposibles** por metáfase.

Y solo **1 de las 10 muestras** llega a tener dos ISCN válidos que comparar
—que es el mínimo para hablar de consenso—, y en esa uno los dos no coinciden.

### El medidor falló primero, y hay que decirlo

La primera versión de este evaluador reportó **«5 de 8 muestras donde todas las
metáfases coinciden»**. Era falso: las cinco «coincidían» en la **cadena de
error**, porque el motor había rechazado las cinco metáfases. La métrica
contaba un rechazo como acuerdo.

Es la **sexta vez** en este proyecto que la primera medición falla por el
instrumento y no por el sistema (ver §7 de `M7_ACTIVIDAD2_SUITE_MEDIDA`). El
motivo quedó escrito en el código, no corregido en silencio:

```python
# OJO: un rechazo NO es un acuerdo. La primera version de este guion
# contaba «5 de 5 metafases coinciden» cuando las cinco habian sido
# rechazadas por el motor ISCN.
```

Si esa cifra hubiera entrado aquí, esta ADR diría lo contrario de lo que dice.

## Decisión

### D1 — El consenso multi-metáfase se difiere. No hay nada sobre lo que votar

Un consenso combina resultados. Con el 90 % de las metáfases sin producir
resultado y el 10 % restante produciendo cariotipos imposibles, **no hay
entradas que combinar**. Construirlo ahora sería añadir una capa de votación
sobre ruido, y su salida heredaría el ruido con apariencia de confirmación —
que es peor que no tenerla, porque parece una segunda opinión.

Es el mismo criterio de ADR-0031: usar el nivel mínimo que resuelva el
problema, y no subir cuando el peldaño de abajo no aguanta.

### D2 — El cuello de botella está aguas arriba, y es la segmentación

El motor ISCN rechaza el 90 % por *falta de cromosomas sexuales*, y la media
detectada es 44 sobre 46 esperados con ~20 copias imposibles. Eso no es un
problema de cómo combinar metáfases: es que **la segmentación no separa bien
los cromosomas** de una metáfase cruda (ya medido en ADR-0035: no hay máscaras
para entrenar ni evaluar un detector).

El trabajo que desbloquea esta ADR es el de ADR-0035, no el de aquí.

### D3 — `Karyotype` deja de ser 1:1 con `Sample` cuando D1 se reactive, no antes

Hoy el modelo impide físicamente guardar dos cariotipos de una muestra:

```python
sample = models.OneToOneField(Sample, ...)          # models.py:189
Karyotype.objects.filter(sample=sample).delete()    # services.py:200
```

`ingest_segmentation` **borra el cariotipo anterior** en cada ingesta. La
migración a `ForeignKey` + una noción de «cariotipo vigente» toca 5 puntos del
backend clínico y 23 ficheros del frontend. **No se hace especulativamente**:
se hará cuando la medición de D4 dé verde, y no antes.

### D4 — El criterio para reabrir esta ADR es una cifra, no una fecha

Se reabre cuando `eval_multimetafase.py` reporte, sobre las mismas 10 muestras:

- **≥ 60 %** de metáfases produciendo un ISCN válido (hoy: 10 %)
- **≥ 5 de 10** muestras con al menos dos ISCN comparables (hoy: 1)

Por debajo de eso, el consenso no tiene materia prima y esta ADR sigue en pie.

## Cómo se sabrá si funcionó

La decisión de **no construir** se valida al revés que una de construir: se
comprueba que el criterio de reapertura se mide de verdad y con regularidad.

- Métrica primaria: `% de metáfases que producen un ISCN válido`. Línea base
  **10 %** (60 metáfases, 10 muestras, 2026-09-08).
- Comando: `python training/eval_multimetafase.py --muestras 10 --tope 6`
- Qué haría reconsiderar esta ADR: cruzar los dos umbrales de D4. También la
  haría reconsiderar lo contrario — que tras mejorar la segmentación el acuerdo
  entre metáfases siga siendo nulo, lo que indicaría que el problema no era la
  segmentación sino la clasificación.

## Consecuencias

**A favor**

- No se escribe una migración de modelo que toca 28 puntos del sistema para
  alimentar una función que hoy no puede funcionar.
- El proyecto gana una medición que no tenía y un evaluador reutilizable: la
  variabilidad entre metáfases del mismo caso es ahora observable, y es la
  métrica que hay que mover.
- El diagnóstico queda donde está el problema. El plan anterior habría gastado
  el esfuerzo en la capa equivocada.

**En contra, y hay que decirlo**

- **El producto sigue mirando 1 de 3 metáfases**, y el usuario no lo sabe. La
  interfaz no dice en ningún sitio que las otras dos no se analizan. Eso es
  deuda de honestidad hacia el analista y debería corregirse aunque el consenso
  no se construya (ver Pendiente 1).
- **El mosaicismo sigue siendo indetectable**, y con 3 metáfases lo seguiría
  siendo aunque el consenso existiera: el estándar pide ~20. El sistema no
  puede reportar `mos …` con fundamento, pese a que `iscn.py` ya soporta el
  prefijo.
- La medición son 10 muestras, no las 28. Se eligieron las de más metáfases; no
  es una muestra aleatoria del laboratorio.
- El criterio de D4 (60 % / 5 de 10) es una elección de ingeniería, no un
  umbral clínico validado. Está puesto para poder decidir, no para acertar.

## Alternativas descartadas

**Construir el consenso igualmente y dejar que el analista juzgue.** Es la
tentación, porque el código es fácil. Pero un consenso sobre tres cariotipos
imposibles produce un cuarto cariotipo imposible con un sello de «confirmado
por 3 metáfases». Añadir confianza aparente a un dato malo es exactamente lo
que RN-01 y RN-02 existen para impedir.

**Promediar los conteos por clase entre metáfases.** No se puede: los
cromosomas no son pareables entre metáfases —no hay correspondencia entre el
cromosoma *i* de una y el de otra—, así que el promedio sería sobre histogramas
de clases, y un histograma promedio de tres histogramas imposibles no es más
plausible que ellos. Además borraría el mosaicismo, que es precisamente lo que
la multiplicidad de metáfases existe para detectar: promediar dos líneas
celulares distintas produce una tercera que no existe en el paciente.

**Segmentar las tres y quedarse con «la mejor».** Requiere un criterio de
calidad que no tenemos. El candidato natural —«la que da 46 cromosomas»— es
circular: elegiría la metáfase cuyo error de segmentación casualmente suma 46,
no la mejor imagen.

**Subir a 20 metáfases en el registro.** Es lo que hace el laboratorio, y
tarde o temprano habrá que hacerlo. Hoy multiplicaría por 20 un procesamiento
que ya produce 90 % de rechazos: 20 veces más ruido, no 20 veces más señal.

## Pendiente antes de pasar a `accepted`

1. **Decir en la interfaz que solo se analiza una metáfase.** Es lo único de
   esta ADR que se puede y se debe hacer ya: el analista tiene derecho a saber
   que las otras dos imágenes están guardadas pero no analizadas. Sin esto, la
   ADR describe un problema conocido que el producto sigue ocultando.
2. Correr `eval_multimetafase.py` sobre las 28 muestras, no 10, para que la
   línea base de D4 no dependa de la selección.
3. Confirmar con el arquitecto si el registro debe pedir 20 metáfases en vez de
   3 cuando D4 se cumpla — es una decisión de producto, no técnica.
