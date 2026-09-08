# backend-ml — Motor de inferencia de cariotipado (ADR-0007, DD-ML-001)

Microservicio **FastAPI** que backend-clinic consume (`pipeline_client`, `:8000`).
Convierte una imagen de metafase real en cromosomas detectados.

**Fase B (actual):** segmentación **REAL** (OpenCV + watershed) + clasificación
**placeholder** (sin modelo entrenado aún). Diseño hexagonal (ADR-0007): el
modelo U-Net + EfficientNet-B3 se enchufa reemplazando los adaptadores de
`ports.py`, sin tocar la API.

## Ejecutar
```bash
cd backend-ml
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Probar
```bash
# salud
curl http://localhost:8000/health/
# segmentar una metafase real (ver datasets/metaclass/)
curl -F "file=@ruta/a/metafase.bmp" http://localhost:8000/api/v1/segment/
```

## Tests
```bash
pytest        # 11 tests (segmentación + pipeline + API), imagen sintética CI-safe
```

## Estructura
```
app/
  main.py          FastAPI: /health/, /api/v1/segment/
  ports.py         SegmenterPort, ClassifierPort (hexagonal, swap del modelo)
  segmentation.py  OpenCVSegmenter (REAL: Otsu + watershed)
  classifier.py    PlaceholderClassifier (STUB por tamaño, confianza baja)
  pipeline.py      orquesta segmentar → clasificar → SegmentResult
  schemas.py       Pydantic (mapea a Chromosome de backend-clinic)
```

## Roadmap
- **Fase C:** entrenar U-Net + EfficientNet-B3 sobre `datasets/metaclass/`
  (460 metafases anotadas). Requiere torch + GPU + extracción de etiquetas (OCR).
- **Fase B2:** wiring backend-clinic (`/samples/{id}/process/` + `/status/` +
  ingesta de resultados) y frontend sin mock.
