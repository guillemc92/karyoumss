"""Servicio de inferencia de cariotipado (FastAPI) — ADR-0007, DD-ML-001.

Es el microservicio que backend-clinic consume vía `pipeline_client` (ADR-0015
#6). Hoy: segmentación REAL (OpenCV) + clasificación placeholder (sin modelo
entrenado). El modelo U-Net + EfficientNet-B3 se enchufa reemplazando los
adaptadores de los puertos hexagonales (ADR-0007), sin tocar esta API.

Ejecutar:  uvicorn app.main:app --reload --port 8000
"""
from __future__ import annotations

from fastapi import FastAPI, File, HTTPException, UploadFile

from .pipeline import get_classifier, run_pipeline
from .schemas import HealthOut, SegmentResult
from .segmentation import load_gray

app = FastAPI(
    title='BIOMED UMSS — Motor de Inferencia de Cariotipado',
    version='0.1.0',
    description='Segmentación + clasificación de cromosomas (ADR-0007). Baseline OpenCV + placeholder.',
)


@app.get('/health/', response_model=HealthOut)
def health() -> HealthOut:
    clf = get_classifier()
    return HealthOut(
        status='ok',
        service='ai-inference',
        model_version=f'opencv-watershed-v0+{clf.name}',
        trained_model=clf.is_trained,  # True si cargó el EfficientNet-B3 entrenado
    )


@app.post('/api/v1/segment/', response_model=SegmentResult)
async def segment_endpoint(file: UploadFile = File(...)) -> SegmentResult:
    """Recibe una imagen de metafase (BMP/PNG/JPG/TIFF) y devuelve los
    cromosomas detectados (bbox + clase placeholder + confianza). Segmentación
    real; la clasificación precisa requiere el modelo entrenado."""
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail='Archivo vacío')
    try:
        gray = load_gray(data)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return run_pipeline(gray)
