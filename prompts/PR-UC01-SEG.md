# Prompt: Celery Task — Segmentación de Muestra con U-Net

## Metadata
* **ID:** PR-UC01-SEG
* **Componente:** `backend/app/tasks/segmentation.py`
* **Objetivo:** Descarga de S3, pre-procesamiento CLAHE, inferencia U-Net por tiles, y NMS en bordes.

## Prompt Cuerpo
```
Role: Eres un ingeniero de Machine Learning especializado en visión computacional para aplicaciones médicas, con experiencia en U-Net para segmentación de instancias y procesamiento de imágenes citogenéticas.

Task: Implementa la Celery task `process_metaphase_image` que:
1. Descarga la imagen de metafase desde S3/MinIO usando el CHN como identificador
2. Aplica pre-procesamiento CLAHE para realzar las bandas G de los cromosomas
3. Ejecuta inferencia con U-Net via TorchServe REST API
4. Retorna lista de objetos con: {chromosome_id, mask_polygon, bounding_box, confidence_pre}
5. Maneja el tiling para imágenes >4K que exceden la VRAM de la GPU

Context:
- Stack: Celery 5 + PyTorch + TorchServe REST API en localhost:8080
- Imágenes de entrada: TIFF/PNG, resolución hasta 8000x6000px, hasta 50MB
- TorchServe endpoint: POST http://torchserve:8080/predictions/unet
- Tiling strategy: dividir en patches 1024x1024 con overlap 64px, ensamblar con NMS
- El task debe publicar progreso: "preprocessing", "segmenting", "assembling"
- IoU mínimo aceptable: 0.95

Reasoning:
1. Verificar que la imagen se descargue correctamente antes de iniciar pipeline
2. Aplicar CLAHE con parámetros: clipLimit=3.0, tileGridSize=(8,8)
3. Para imágenes >4K: dividir en tiles con overlap, ejecutar U-Net por tile
4. Post-procesamiento: Non-Maximum Suppression para eliminar duplicados en bordes de tiles
5. Si TorchServe no responde en 10s: reintentar hasta 3 veces, luego marcar como error

Stop Condition: Detente cuando la task: (1) procese correctamente una imagen de 15MB en <15s, (2) maneje el tiling sin perder cromosomas en los bordes, (3) registre el progreso en Redis para el WebSocket.

Output: Bloque de código Python con:
- `backend/app/tasks/segmentation.py` — Celery task completa
- Ejemplo de output: lista de dicts con polygon_coords en formato GeoJSON-like
```
