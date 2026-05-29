# Prompt: Celery Task — Clasificación con EfficientNet-B3 y Softmax

## Metadata
* **ID:** PR-UC01-CLS
* **Componente:** `backend/app/tasks/classification.py`
* **Objetivo:** Clasificar cultivos cromosómicos en 24 clases con score Softmax y registrar requiere revisión si score < 85%.

## Prompt Cuerpo
```
Role: Eres un ingeniero de ML especializado en clasificación de imágenes médicas con EfficientNet-B3 y en el diseño de pipelines de inferencia confiables para entornos clínicos.

Task: Implementa la función `classify_chromosomes` que:
1. Recibe la lista de cromosomas segmentados (recortados del resultado de U-Net)
2. Ejecuta EfficientNet-B3 via TorchServe para clasificar cada cromosoma en pares 1–22, X, Y
3. Extrae el score Softmax de la clase predicha
4. Retorna para cada cromosoma: {chromosome_id, predicted_pair, confidence_score, all_scores}
5. Aplica el umbral de 85%: si confidence_score < 0.85 → campo "requires_review": true

Context:
- TorchServe endpoint: POST http://torchserve:8080/predictions/efficientnet_karyotype
- Input por cromosoma: imagen recortada 64x64px en base64
- Restricción: nunca redondear el score antes de persistirlo (guardar float completo)

Reasoning:
1. Procesar cromosomas en batch de 16 para optimizar throughput de GPU
2. Verificar que la suma de scores Softmax sea ≈ 1.0
3. Persistir en tabla `chromosomes` con score completo

Stop Condition: Detente cuando: (1) clasifique correctamente los 46 cromosomas de una muestra estándar 46,XY, (2) el umbral 85% esté correctamente aplicado, (3) los scores se persistan sin redondeo.

Output: Código Python + schema JSON:
- `backend/app/tasks/classification.py`
```
