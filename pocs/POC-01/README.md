# POC-01: Segmentación Automática de Cromosomas (U-Net)

## 🎯 Objetivo
Validar que una arquitectura U-Net pueda segmentar cromosomas a partir de una imagen de metafase con bandas G con un IoU > 0,90.

## 🛠️ Implementación
- **Conjunto de datos:** 1.000 imágenes de metafase anotadas.
- **Arquitectura:** U-Net con codificador EfficientNet-B0.
- **Entrada:** Mosaicos de $1024 \times 1024\text{px}$ (escala de grises).
- **Salida:** Máscara binaria del cuerpo del cromosoma.

## 📊 Métricas y Resultados

| Métrica | Resultado | Objetivo | Cumplimiento |
|---------|-----------|----------|--------------|
| **IoU Promedio** | **0.92** | > 0.90 | ✅ Superado |
| **Precisión** | 94.5% | - | - |
| **Exhaustividad (Recall)** | 91.2% | - | - |
| **Tiempo de inferencia por mosaico** | **1.2 s** | - | - |

**Condiciones de prueba:**  
Imágenes reales de alta resolución (hasta 8000×6000 px), procesadas mediante tiling.

## 💡 Lecciones Aprendidas
- **El tiling es esencial:** Segmentar la imagen completa de una sola vez provocó la “desaparición” de cromosomas debido al submuestreo.
- **Los bordes importan:** La superposición de **64 px** fue crucial para evitar cortar cromosomas en los límites de los mosaicos.
- **EfficientNet-B0** como backbone ofrece un excelente balance entre precisión y velocidad.

## Evidencia
- `evidence/metrics-iou.png`
- `evidence/sample-segmentation-before-after.png`
- `evidence/logs-inference-20260529.txt`

**Estado:** ✅ **Completada y Validada**
