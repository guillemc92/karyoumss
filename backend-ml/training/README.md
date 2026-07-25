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

**Resultado:** 453/460 OK, **19.845 crops** etiquetados. Clases 1-18 ~900 c/u
(balanceadas y limpias); 19-22 cientos; X=390, Y=111.

## C2 — Entrenar EfficientNet-B3 (pendiente)
Requiere `torch` + `torchvision`. Recomendado: transfer learning (backbone
ImageNet congelado + entrenar la cabeza de 24 clases) → rápido incluso en CPU.
Salida: `models/classifier.pth` + métricas.

## C3 — Enchufar (pendiente)
Implementar `EfficientNetClassifier(ClassifierPort)` en `app/` que cargue el
`.pth` y reemplace `PlaceholderClassifier` — sin tocar la API ni el pipeline
(diseño hexagonal, ADR-0007).
