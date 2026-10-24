"""Servicio de inferencia de cariotipado (FastAPI) — ADR-0007, DD-ML-001.

Es el microservicio que backend-clinic consume vía `pipeline_client` (ADR-0015
#6). Hoy: segmentación REAL (OpenCV) + clasificación placeholder (sin modelo
entrenado). El modelo U-Net + EfficientNet-B3 se enchufa reemplazando los
adaptadores de los puertos hexagonales (ADR-0007), sin tocar esta API.

Ejecutar:  uvicorn app.main:app --reload --port 8000
Límites:   ML_MAX_INFERENCIAS (1) y ML_ESPERA_MAX_S (25) — DD-AUD-001 F1.
"""
from __future__ import annotations

import json

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from .concurrencia import LimiteInferencias
from .pipeline import get_classifier, run_pipeline
from .edicion import CorteInvalidoError, cortar, unir
from .schemas import ContornosOut, HealthOut, JoinOut, SegmentResult, SplitOut, TrozoOut
from .segmentation import contorno_en_caja, load_gray

app = FastAPI(
    title='BIOMED UMSS — Motor de Inferencia de Cariotipado',
    version='8.2.0',
    description=('Segmentación + clasificación de cromosomas (ADR-0007) y las operaciones de edición '
                 'de la metafase (DD-KARYO-007). Contrato exportado con `python -m app.exportar_openapi` '
                 '(DD-API-001).'),
    contact={'name': 'Ing. Guillermo Mamani Chambi', 'url': 'https://github.com/guillemc92/karyoumss'},
    servers=[{'url': 'http://localhost:8000', 'description': 'Desarrollo local'}],
    openapi_tags=[
        {'name': 'Salud', 'description': 'Estado del servicio y del modelo cargado.'},
        {'name': 'Inferencia', 'description': 'Segmentar, clasificar y explicar.'},
        {'name': 'Edición de la metafase', 'description': 'Contornos, separar y unir (DD-KARYO-007).'},
    ],
)

#: Errores propios (HTTPException): `detail` es un texto. Los de validación de
#: FastAPI traen una lista; el contrato admite las dos formas para el 422.
_ERROR = {'description': 'Petición inválida.', 'content': {'application/json': {'schema': {
    'type': 'object', 'properties': {'detail': {'type': 'string'}}}}}}
_ERROR_422 = {'description': 'La imagen no se puede leer, el corte no separa el objeto o los campos no validan.',
              'content': {'application/json': {'schema': {'type': 'object', 'properties': {
                  'detail': {'anyOf': [{'type': 'string'}, {'type': 'array', 'items': {'type': 'object'}}]}}}}}}

# DD-AUD-001 F1 (CON-02): los endpoints de inferencia son `def`, no `async def`.
# Hacen ~19 s de CPU síncrona; dentro de un `async def` congelaban el único
# event loop y nada más se atendía, ni `/health/`. Con `def` FastAPI los corre
# en su threadpool, y `limite` decide cuántas inferencias van a la vez.
limite = LimiteInferencias.desde_entorno()


@app.get('/health/', response_model=HealthOut, tags=['Salud'])
def health() -> HealthOut:
    """Estado del servicio y del clasificador cargado (entrenado o de reserva)."""
    clf = get_classifier()
    return HealthOut(
        status='ok',
        service='ai-inference',
        model_version=f'opencv-watershed-v0+{clf.name}',
        trained_model=clf.is_trained,  # True si cargó el EfficientNet-B3 entrenado
    )


@app.post('/api/v1/segment/', response_model=SegmentResult, tags=['Inferencia'],
          responses={400: _ERROR, 422: _ERROR_422})
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


#: Tope de cajas por petición: una metafase trae ~46; el margen cubre los casos
#: sobresegmentados sin dejar que una petición pida miles de recortes.
MAX_CAJAS_CONTORNO = 200


@app.post('/api/v1/contours/', response_model=ContornosOut, tags=['Edición de la metafase'],
          responses={400: _ERROR, 422: _ERROR_422})
def contours_endpoint(file: UploadFile = File(...), bboxes: str = Form(...)) -> ContornosOut:
    """Silueta de cada caja dada sobre la metafase (DD-KARYO-007 D1).

    Para los casos que se segmentaron antes de que `/segment/` devolviera
    contornos: solo tienen `bbox`. `bboxes` es una lista JSON de
    `{x, y, w, h}` en píxeles de la metafase; la respuesta trae un contorno por
    caja y en el mismo orden, o `null` si la caja no tiene una silueta
    utilizable (fuera de la imagen, sin tinta).

    No pasa por el límite de inferencias: no toca el modelo y es Otsu sobre
    recortes, milisegundos por caja.
    """
    try:
        cajas = json.loads(bboxes)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail='bboxes no es JSON válido') from exc
    if not isinstance(cajas, list) or not all(isinstance(c, dict) for c in cajas):
        raise HTTPException(status_code=400, detail='bboxes debe ser una lista de {x, y, w, h}')
    if len(cajas) > MAX_CAJAS_CONTORNO:
        raise HTTPException(status_code=400,
                            detail=f'como mucho {MAX_CAJAS_CONTORNO} cajas por petición')
    data = file.file.read()
    if not data:
        raise HTTPException(status_code=400, detail='Archivo vacío')
    try:
        gray = load_gray(data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    contornos = []
    for c in cajas:
        try:
            caja = tuple(int(c[k]) for k in ('x', 'y', 'w', 'h'))
        except (KeyError, TypeError, ValueError):
            contornos.append(None)  # una caja mal formada no tumba las demás
            continue
        contornos.append(contorno_en_caja(gray, caja))
    return ContornosOut(contornos=contornos)


def _json_form(valor: str | None, nombre: str):
    """Un campo de formulario que trae JSON. 400 si no lo es."""
    if valor is None or valor == '':
        return None
    try:
        return json.loads(valor)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f'{nombre} no es JSON válido') from exc


def _poligono(valor, nombre: str) -> list[list[int]]:
    if not isinstance(valor, list) or not all(
            isinstance(p, list) and len(p) == 2 and all(isinstance(v, (int, float)) for v in p)
            for p in valor):
        raise HTTPException(status_code=400, detail=f'{nombre} debe ser una lista de [x, y]')
    return [[int(round(x)), int(round(y))] for x, y in valor]


def _caja(t) -> dict[str, int]:
    return {'x': int(t[0]), 'y': int(t[1]), 'w': int(t[2]), 'h': int(t[3])}


@app.post('/api/v1/split/', response_model=SplitOut, tags=['Edición de la metafase'],
          responses={400: _ERROR, 422: _ERROR_422})
def split_endpoint(
    file: UploadFile = File(...),
    bbox: str = Form(...),
    linea: str = Form(...),
    contour: str | None = Form(None),
) -> SplitOut:
    """Separa un objeto por la línea que trazó el analista (DD-KARYO-007 D3).

    `bbox` `{x, y, w, h}` y `contour` `[[x, y], …]` (opcional) son los del
    objeto; `linea` es la polilínea, todo en píxeles de la metafase. Corte en
    ráster: ver `edicion.cortar`.

    - 200 los trozos, de mayor a menor
    - 400 datos mal formados
    - 422 la línea no separa el objeto (o la imagen no se puede leer)

    No pasa por el límite de inferencias: no usa el modelo.
    """
    caja = _json_form(bbox, 'bbox')
    try:
        caja_t = tuple(int(caja[k]) for k in ('x', 'y', 'w', 'h'))
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail='bbox debe ser {x, y, w, h}') from exc
    trazo = _poligono(_json_form(linea, 'linea'), 'linea')
    silueta = _json_form(contour, 'contour')
    silueta = _poligono(silueta, 'contour') if silueta is not None else None
    data = file.file.read()
    if not data:
        raise HTTPException(status_code=400, detail='Archivo vacío')
    try:
        gray = load_gray(data)
        trozos = cortar(gray, caja_t, silueta, trazo)
    except ValueError as exc:  # imagen ilegible o CorteInvalidoError
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return SplitOut(trozos=[TrozoOut(contour=t.contour, bbox=_caja(t.bbox), area=t.area) for t in trozos])


@app.post('/api/v1/join/', response_model=JoinOut, tags=['Edición de la metafase'],
          responses={400: _ERROR, 422: _ERROR_422})
def join_endpoint(contornos: str = Form(...)) -> JoinOut:
    """Silueta de la unión de varias siluetas (DD-KARYO-007 D4). Sin imagen:
    es geometría sobre los contornos. 400 mal formado, 422 menos de dos."""
    lista = _json_form(contornos, 'contornos')
    if not isinstance(lista, list):
        raise HTTPException(status_code=400, detail='contornos debe ser una lista de polígonos')
    poligonos = [_poligono(c, 'contornos[]') for c in lista]
    try:
        contorno, caja = unir(poligonos)
    except CorteInvalidoError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return JoinOut(contour=contorno, bbox=_caja(caja))


@app.post('/api/v1/xai/', tags=['Inferencia'], responses={400: _ERROR, 422: _ERROR_422})
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


@app.post('/api/v1/classify/', tags=['Inferencia'], responses={400: _ERROR, 422: _ERROR_422})
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
