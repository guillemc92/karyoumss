# backend-ml/training — Fase C (modelo entrenado)

Pipeline para entrenar el clasificador real (EfficientNet-B3) que reemplaza al
placeholder de `app/classifier.py`, usando el dataset MetaClass real.

## C1 — Extracción de etiquetas (hecho)
`extract_labels.py` — parsea los cariogramas ORDENADOS
(`datasets/metaclass/cariogramas/*.bmp`, extraídos de `SCAAnalisisCariotipos.
ImagenCariotipo`). La disposición estándar del experto (4 filas) da la clase por
POSICIÓN: se segmenta, se agrupan 4 filas, y las clases 1-18 (conteo fijo 5/7/6)
se cortan por los top-K gaps → cada cromosoma queda etiquetado con su clase.

QC: descarta la imagen si no hay 4 filas o si 1-18 no cuadran (etiquetas 1-18
limpias). Fila 4 (19-22/X/Y, variable) = best-effort (más ruidosa).

```bash
python extract_labels.py           # → datasets/metaclass/crops/{clase}/*.png + crops_manifest.csv
python extract_labels.py --viz 2   # valida el etiquetado dibujándolo
```

**Resultado (extracción original, 460 cariogramas):** 453/460 OK, **19.845 crops**
etiquetados. Clases 1-18 ~900 c/u (balanceadas y limpias); 19-22 cientos; X=390,
Y=111.

### C1-bis — la base creció (2026-07-27)

El laboratorio actualizó `SCAMC.mdf`. `SCAAnalisisCariotipos` pasó a **1113
análisis con imagen válida** (589 nuevos sobre el ID 546 previo). `export_from_mdf.py`
los vuelca desde SQL Server; después `extract_labels.py` corre igual, sin cambios.

```bash
python export_from_mdf.py     # 1113 cariogramas -> datasets/metaclass/cariogramas/
python extract_labels.py      # re-genera crops + manifiesto
```

**Resultado medido:** 1096/1113 OK, 17 descartados por QC (98.5% de aprobación,
mejor que el 98.5% previo — el parser aguantó bien las imágenes nuevas).
**48.467 crops** etiquetados, de 19.845: **2.4× más datos**.

| clase | antes | ahora |
|---|---|---|
| 1-18 (típica) | ~900 | ~2.200 |
| 22 | 560 | 1.393 |
| X | 390 | **980** |
| Y | 111 | **359** |

Las clases que estaban flacas son las que más ganaron: **Y se triplicó y X se
duplicó con creces**. Ese desbalance era la causa más probable de su F1 bajo — el
`WeightedRandomSampler` compensa el muestreo pero no inventa variedad que no está
en los datos. Aun así X e Y siguen siendo minoritarias, así que el sampler
ponderado del notebook sigue haciendo falta.

> ⚠️ **Más datos NO arreglan los defectos del v1.** La fuga de datos entre
> train/val y el preprocesamiento deformante se corrigen en
> `train_classifier_v2.ipynb`, no con volumen. De hecho el problema de homólogos
> creció en términos absolutos: **21.088 pares (cariograma, clase) con 2 crops**
> casi idénticos, contra 8.802 antes. Entrenar el v1 sobre estos datos daría una
> métrica aún más inflada. **Usar el v2.**

## C2 — Entrenar EfficientNet-B3 v1 (hecho, con defectos)
`train_classifier.ipynb` — transfer learning, val_acc **0.633** / macro-F1 0.601.

**Esa cifra está inflada y el modelo rinde por debajo de su potencial.** Ver C4.

## C3 — Enchufar (hecho)
`app/efficientnet.py` implementa `EfficientNetClassifier(ClassifierPort)`, carga
el `.pth` y reemplaza al `PlaceholderClassifier` sin tocar la API ni el pipeline
(diseño hexagonal, ADR-0007).

## C4 — Reentrenamiento v2 (`train_classifier_v2.ipynb`)

Corrige tres defectos del v1, diagnosticados sobre el dataset real.

### 1. El split filtraba datos entre train y val (métrica inflada)
El v1 usaba `random_split` sobre los 19.845 crops sueltos. Cada cariograma aporta
~44 crops del mismo paciente y la misma metafase, y los dos homólogos de cada par
son casi idénticos (**8.802 pares (cariograma, clase) con exactamente 2 crops**).
Con split aleatorio, un homólogo caía en train y su gemelo en val: la red podía
reconocer al paciente en vez de la clase.

→ **v2 hace el split por cariograma.** Ningún paciente aparece en ambos lados. El
número resultante será más bajo, y es el primero comparable con producción, donde
cada muestra viene de un paciente que el modelo nunca vio.

### 2. El preprocesamiento borraba la señal discriminante
El v1 aplicaba `Resize((224,224))` a cada crop. Un citogenetista clasifica por
**tamaño relativo** y **relación de aspecto** (posición del centrómero). Medido
sobre el dataset:

| clase | alto mediano | H/W |
|---|---|---|
| 1  | 133 px | 3.58 |
| 9  | 73 px  | 2.33 |
| 21 | 29 px  | 1.15 |

`Resize` a un cuadrado lleva todo a H/W = 1.0 y a un tamaño único: el 1 y el 21
llegaban a la red con la misma forma y el mismo tamaño. Solo quedaba el patrón de
bandas.

→ **v2 usa `letterbox`** (`app/preprocess.py`): conserva el aspecto (rellena en
blanco, no deforma) y la escala relativa — cada crop se escala contra la altura
mediana de los cromosomas de *su misma* imagen, lo que lo hace invariante al zoom
del microscopio. Verificado: el 1 pasa a ocupar 21.4% del lienzo y el 21 solo 4.5%.

### 3. Se guardaba la última época, no la mejor
→ v2 guarda el checkpoint de mejor macro-F1 en validación.

### Ejecutar en Colab con GPU T4

1. **Subir `crops.zip` a Google Drive** (cualquier carpeta). Son ~84 MB y 48.467
   archivos: `files.upload()` es lento y se corta — por eso el notebook monta
   Drive en su lugar. La celda 3 **busca el archivo sola**; si no lo encuentra,
   lista los `.zip` que sí hay para que copies la ruta en `ZIP_EN_DRIVE`.

   > ⚠️ **`drive.mount()` recibe el punto de montaje del runtime, no una carpeta
   > de tu Drive.** Siempre `'/content/drive'`. Tu Drive queda montado bajo
   > `/content/drive/MyDrive/`, así que un archivo en *Colab Notebooks* está en
   > `/content/drive/MyDrive/Colab Notebooks/crops.zip`. Cambiar el punto de
   > montaje (p. ej. a `'/Colab Notebooks/'`) es la causa más común del
   > `AssertionError: No se encontró ...` — el Drive se "monta" en una ruta que
   > no existe y nada aparece.
2. **Subir el notebook**: colab.research.google.com → *Archivo → Subir cuaderno*
   → `train_classifier_v2.ipynb`.
3. **Activar la GPU** *antes* de correr nada: *Entorno de ejecución → Cambiar
   tipo de entorno de ejecución → **T4 GPU***. Reinicia el entorno.
4. **Verificar**: la celda 1 debe imprimir `device: cuda`. Si dice `cpu`, la GPU
   no se activó y el entrenamiento no es viable.
5. Ejecutar las celdas en orden (*Entorno de ejecución → Ejecutar todas*).

**Duración estimada:** ~1-2 h en T4 con 48.467 crops y 14 épocas (6 cabeza + 8
fine-tune).

**Contra las desconexiones de Colab** (inactividad, cuota de GPU): el notebook
copia el mejor checkpoint a `CKPT_DIR` en Drive **cada vez que mejora el
macro-F1**, no solo al final. Si el runtime muere a mitad del fine-tune,
`classifier_best.pth` y `checkpoint_meta.json` siguen en Drive. La celda 16
también copia los 3 archivos finales a Drive antes de intentar la descarga.

El notebook deriva el cariograma de origen del nombre del crop
(`<clase>/cario<ID>_<idx>.png`), así que no necesita el manifiesto.

### Resultado del v2 (entrenado 2026-07-28)

| | v1 | **v2** |
|---|---|---|
| val_accuracy | 0.6334 | **0.6771** |
| val_macro_F1 | 0.6008 | **0.6517** |
| split | aleatorio (**con fuga**) | por cariograma (932 train / 164 val) |
| preprocesamiento | `Resize` deformante | `letterbox` |

**El v2 es mejor de lo que sugiere la comparación.** Los dos números no son
homologables: el 0.6008 del v1 se midió con homólogos del mismo paciente repartidos
entre train y val, así que estaba inflado. El v2 sube +5 puntos de macro-F1
**a la vez que** pasa a una medición honesta sobre 164 cariogramas nunca vistos.
La mejora real sobre pacientes nuevos es mayor que esos 5 puntos.

### Actualización del dataset (2026-07-29)

La base del laboratorio sumó **56 cariogramas** (IDs 1168-1225). Re-extracción:
**1150/1169 OK**, 19 descartados por QC → **50.864 crops** (antes 48.467).

| clase | antes | ahora | |
|---|---|---|---|
| 1-18 (típica) | ~2.200 | ~2.300 | +5% |
| 22 | 1.393 | 1.458 | +4.7% |
| X | 980 | 1.031 | +5.2% |
| Y | 359 | 380 | +5.8% |

> ⚠️ **+4.9% no mueve la aguja.** El crecimiento fue proporcional en todas las
> clases, así que **el desbalance quedó idéntico**: el cromosoma Y sigue en 1 a 6.3
> contra una clase típica. Verificado sobre los conteos nuevos, el sampler del v2
> le sigue mostrando el Y **5.6× más** de lo que aparece. El problema de X/Y es de
> **calibración, no de volumen** — por eso el cambio que importa sigue siendo
> `SAMPLER_POWER` del v3, no los datos adicionales.

### Enchufar el v2
Copiá `classifier.pth`, `classes.json` y `model_meta.json` a `backend-ml/models/`.

> ⚠️ **Los tres archivos van juntos, siempre.** El v2 cambió el orden de las clases:
> el v1 usaba el alfabético de `ImageFolder` (`1, 10, 11, 12, ..., 2, 20, ...`) y el
> v2 usa el citogenético (`1, 2, 3, ..., 22, X, Y`). Mezclar el `classifier.pth` del
> v2 con el `classes.json` del v1 **traduce cada predicción a la clase equivocada**
> sin fallar ni avisar: el índice 1 sería "10" en vez de "2". Un respaldo del v1
> completo queda en `backend-ml/models_v1_backup/`.
> `tests/test_efficientnet.py::TestCoherenciaDeLosArtefactos` detecta el desajuste.

## C6 — v3 (`train_classifier_v3.ipynb`)

Parte del v2 y ataca lo que revela su reporte por clase. **Split por cariograma y
letterbox se mantienen sin cambios** — funcionaron.

### Lo que el v2 demostró
F1 por **grupo de Denver** (clasificación citogenética por tamaño): A (1-3) 0.85 →
D 0.69 → E 0.68 → C 0.67 → F 0.66 → B 0.65 → **G (21-22) 0.54**. El gradiente es
limpio: cuanto más grande el cromosoma, mejor lo clasifica. **El letterbox funcionó**
— la señal de tamaño relativo llega a la red. La confusión residual cae entre
cromosomas de tamaño similar, que es también donde la tiene un humano (lo cubre el
HITL de RN-01).

### Los tres cambios

**1. Sampler suavizado — el de mayor impacto.** El v2 sobre-predice X e Y: con
P=0.14 / R=0.43 sobre 58 casos, el Y da **25 aciertos y ~153 falsos positivos**.
Recall ≫ precisión es la firma de la sobre-corrección del `WeightedRandomSampler`:
con pesos `1/frecuencia` la red veía el Y **5.6× más** de lo que aparece y aprendió
«ante la duda, decí X o Y». Con `1/sqrt(frecuencia)` (`SAMPLER_POWER = 0.5`) baja a
**2.4×** — verificado sobre los conteos reales del dataset. Sin X ni Y el macro-F1
del v2 sería 0.685 en vez de 0.652: esas dos clases cuestan 3.4 puntos.

**2. 224 → 300 px.** Resolución nativa de EfficientNet-B3. Los cromosomas 21 y 22
miden ~29 px: en un lienzo de 224 con letterbox ocupan poquísimo. `BATCH` baja a 32
para compensar la memoria.

**3. Más fine-tune (8 → 12 épocas) y rotación 25° → 15°.** La mejor época del v2 fue
la **7 de 8**: seguía mejorando al final, no convergió. Y cuando el tamaño ya no
alcanza (grupos C y G), lo discriminante es el **patrón de bandas**, que una rotación
agresiva difumina por interpolación.

> ⚠️ **Costo:** 300 px son ~1.8× más cómputo por imagen. Con 48.467 crops y 18
> épocas, calcular **3-4 h en T4**. Si la cuota de GPU aprieta, bajá `EPOCHS_HEAD`
> a 4 o volvé a `IMG_SIZE = 224` — los otros dos cambios aportan por sí solos.

La celda 14-bis compara X/Y y los grupos de Denver **contra los números del v2**, así
que se ve de inmediato si la calibración mejoró.

El `model_meta.json` del v2 trae `"preprocess": "letterbox"`. **Ese campo es
load-bearing:** `app/efficientnet.py` lo lee para decidir el preprocesamiento y,
si falta, asume el `resize` del v1. Por eso el v1 actual sigue funcionando sin
cambios — y por eso un v2 al que se le pierda el campo se degradaría en silencio.

> ⚠️ `app/preprocess.py` y la celda 7 del notebook son el **mismo** letterbox
> duplicado (el notebook corre en Colab, sin acceso al repo). Si tocás uno, tocá
> el otro: divergir hace que el modelo vea en producción algo distinto de lo que
> vio al entrenar, sin ningún síntoma visible. `tests/test_preprocess.py` protege
> las propiedades (aspecto, escala relativa, invarianza al zoom, relleno).

### Cómo leer los resultados
- **No compares el macro-F1 del v2 contra el 0.601 del v1**: el v1 se midió con
  fuga de datos. Para la línea base honesta, reentrená el v1 con split por
  cariograma.
- **Confusión entre clases de tamaño similar** (19/20/21/22, o 4/5) es esperable,
  y es justo lo que cubre el HITL de RN-01: caen en naranja y las valida el
  analista.
- **Confusión entre grupos lejanos** (1 ↔ 21) indicaría que la señal de escala no
  está llegando — revisar el letterbox (celda 7 / `app/preprocess.py`).
