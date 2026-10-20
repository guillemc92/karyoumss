"""Servicio de inferencia de cariotipado (FastAPI) — ADR-0007, DD-ML-001.

Es el microservicio que backend-clinic consume vía `pipeline_client` (ADR-0015
#6). Hoy: segmentación REAL (OpenCV) + clasificación placeholder (sin modelo
entrenado). El modelo U-Net + EfficientNet-B3 se enchufa reemplazando los
adaptadores de los puertos hexagonales (ADR-0007), sin tocar esta API.

Ejecutar:  uvicorn app.main:app --reload --port 8000
Límites:   ML_MAX_INFERENCIAS (1) y ML_ESPERA_MAX_S (25) — DD-AUD-001 F1.
Estado:    GET /api/v1/inferencias/ con X-Internal-Secret (INTERNAL_SERVICE_SECRET).
"""
from __future__ import annotations

import hmac
import os

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile

from .concurrencia import LimiteInferencias
from .pipeline import get_classifier, run_pipeline
from .schemas import EstadoInferenciasOut, HealthOut, SegmentResult
from .segmentation import load_gray

app = FastAPI(
    title='BIOMED UMSS — Motor de Inferencia de Cariotipado',
    version='0.1.0',
    description='Segmentación + clasificación de cromosomas (ADR-0007). Baseline OpenCV + placeholder.',
)

# DD-AUD-001 F1 (CON-02): los endpoints de inferencia son `def`, no `async def`.
# Hacen ~19 s de CPU síncrona; dentro de un `async def` congelaban el único
# event loop y nada más se atendía, ni `/health/`. Con `def` FastAPI los corre
# en su threadpool, y `limite` decide cuántas inferencias van a la vez.
limite = LimiteInferencias.desde_entorno()


@app.get('/health/', response_model=HealthOut)
def health() -> HealthOut:
    clf = get_classifier()
    return HealthOut(
        status='ok',
        service='ai-inference',
        model_version=f'opencv-watershed-v0+{clf.name}',
        trained_model=clf.is_trained,  # True si cargó el EfficientNet-B3 entrenado
    )


@app.get('/api/v1/inferencias/', response_model=EstadoInferenciasOut)
def estado_inferencias(
    x_internal_secret: str | None = Header(default=None, alias='X-Internal-Secret'),
) -> EstadoInferenciasOut:
    """Estado del límite de inferencias: plazas, ocupadas y en espera (FR1).

    No llama a `limite.turno()`: responde aunque no quede ninguna plaza y no
    ocupa ninguna (FR2, NFR1). Exige el secreto interno con la convención de
    backend-admin (FR4): 503 si backend-ml no lo tiene configurado (FR4.3),
    403 si la cabecera falta o no coincide (FR4.2). La comparación es de tiempo
    constante y el valor del secreto no sale en ninguna respuesta (NFR2).
    """
    # Se lee en cada petición: sin secreto el servicio arranca igual (FR4.3).
    secreto = os.environ.get('INTERNAL_SERVICE_SECRET', '')
    if not secreto:
        raise HTTPException(status_code=503,
                            detail='Estado de inferencias no configurado')
    if x_internal_secret is None or not hmac.compare_digest(
            x_internal_secret.encode(), secreto.encode()):
        raise HTTPException(status_code=403, detail='Secreto de servicio inválido')
    return EstadoInferenciasOut(**limite.estado())


@app.post('/api/v1/segment/', response_model=SegmentResult)
def segment_endpoint(file: UploadFile = File(...)) -> SegmentResult:
    """Recibe una imagen de metafase (BMP/PNG/JPG/TIFF) y devuelve los
    cromosomas detectados (bbox + clase placeholder + confianza). Segmentación
    real; la clasificación precisa requiere el modelo entrenado."""
    data = file.file.read()
    if not data:
        raise HTTPException(status_code=400, detail='Archivo vacío')
    try:
        gray = load_gray(data)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    with limite.turno():
        return run_pipeline(gray)


@app.post('/api/v1/xai/')
def xai_endpoint(
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
        gray = load_gray(file.file.read())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    alto, ancho = gray.shape
    if not (0 <= x < ancho and 0 <= y < alto and w > 0 and h > 0
            and x + w <= ancho and y + h <= alto):
        raise HTTPException(status_code=400, detail='bbox fuera de la imagen')

    with limite.turno():
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


@app.post('/api/v1/classify/')
def classify_endpoint(
    file: UploadFile = File(...),
    x: int = Form(...), y: int = Form(...),
    w: int = Form(...), h: int = Form(...),
) -> dict:
    """Clasifica UN recorte de la metafase (bbox dado por el usuario).

    Existe para cerrar el bucle del recorte manual: si el analista corrige el
    límite de un cromosoma, la clase que se predijo sobre el recorte anterior
    queda obsoleta. Volver a clasificar con el recorte bueno es justo lo que
    ataca el fallo medido —recortes malos producen clases falsas—, así que la
    corrección manual tiene que arrastrar una nueva predicción.

    Recibe la metafase entera, no el recorte, por la misma razón que /xai/: el
    preprocesado usa `ref_h`, la altura mediana de TODOS los cromosomas de esa
    imagen, como señal de escala.
    """
    from .preprocess import reference_height
    from .segmentation import Detection, segment

    try:
        gray = load_gray(file.file.read())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    alto, ancho = gray.shape
    if not (0 <= x < ancho and 0 <= y < alto and w > 0 and h > 0
            and x + w <= ancho and y + h <= alto):
        raise HTTPException(status_code=400, detail='bbox fuera de la imagen')

    with limite.turno():
        clf = get_classifier()
        # La escala de referencia sale de la segmentación automática de ESTA
        # metafase, no del recorte: es la mediana de la imagen completa.
        ref_h = reference_height([d.bbox[3] for d in segment(gray)])

        deteccion = Detection(bbox=(x, y, w, h), area=w * h,
                              centroid=(x + w / 2.0, y + h / 2.0))
        resultados = clf.classify_all(gray, [deteccion])
        if not resultados:
            raise HTTPException(status_code=503, detail='el clasificador no devolvió resultado')

        clase, confianza = resultados[0]
        return {
            'predicted_class': clase,
            'confidence_score': confianza,
            'modelo': clf.name,
            'entrenado': clf.is_trained,
            'ref_h': round(float(ref_h), 1),
        }
