"""Servicio de inferencia de cariotipado (FastAPI) — ADR-0007, DD-ML-001.

Es el microservicio que backend-clinic consume vía `pipeline_client` (ADR-0015
#6). Hoy: segmentación REAL (OpenCV) + clasificación placeholder (sin modelo
entrenado). El modelo U-Net + EfficientNet-B3 se enchufa reemplazando los
adaptadores de los puertos hexagonales (ADR-0007), sin tocar esta API.

Ejecutar:  uvicorn app.main:app --reload --port 8000
"""
from __future__ import annotations

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

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


@app.post('/api/v1/xai/')
async def xai_endpoint(
    file: UploadFile = File(...),
    x: int = Form(...), y: int = Form(...),
    w: int = Form(...), h: int = Form(...),
) -> dict:
    """Grad-CAM real de UN cromosoma de la metafase (ADR-0007, BR-004).

    Recibe la metafase completa y el bbox del cromosoma. Necesita la imagen
    entera y no solo el recorte porque el preprocesado usa `ref_h` —la altura
    mediana de TODOS los cromosomas de esa metafase—, que es la señal de escala
    con la que se entrenó el clasificador. Con un recorte suelto el mapa
    correspondería a una entrada que el modelo nunca vio.

    Devuelve el mapa superpuesto en PNG base64 y un resumen auditable de dónde
    se concentra la activación.
    """
    from .gradcam import GradCamNoDisponible, heatmap_png, resumen_activacion
    from .preprocess import reference_height
    from .segmentation import segment

    try:
        gray = load_gray(await file.read())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    alto, ancho = gray.shape
    if not (0 <= x < ancho and 0 <= y < alto and w > 0 and h > 0
            and x + w <= ancho and y + h <= alto):
        raise HTTPException(status_code=400, detail='bbox fuera de la imagen')

    clf = get_classifier()
    if not clf.is_trained:
        # Sin modelo entrenado no hay gradientes que explicar. Se dice, en vez
        # de devolver un mapa vacío que parezca una explicación.
        raise HTTPException(status_code=503,
                            detail='XAI no disponible: el clasificador no está entrenado')

    ref_h = reference_height([d.bbox[3] for d in segment(gray)])
    crop = gray[y:y + h, x:x + w]

    try:
        return {
            'heatmap_base64': heatmap_png(clf, crop, ref_h),
            'activacion': resumen_activacion(clf, crop, ref_h),
            'modelo': clf.name,
            'metodo': 'grad-cam',
            'ref_h': round(float(ref_h), 1),
        }
    except GradCamNoDisponible as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
