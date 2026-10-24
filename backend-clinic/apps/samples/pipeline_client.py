import json
import threading
import time
from contextlib import contextmanager

import httpx
from django.conf import settings

#: La clase de verdad, guardada al importar. Si alguien sustituye `httpx.Client`
#: (los dobles de las pruebas), `_sesion` usa el sustituto como antes.
_CLIENTE_REAL = httpx.Client


class MLDegradedError(Exception):
    """RN-07: pipeline FastAPI no disponible. El caller debe persistir la
    muestra igual y degradar la UI (DegradedBanner), no bloquear."""


class CorteInvalidoError(ValueError):
    """La línea trazada no separa el objeto (422 de backend-ml)."""


class _ConTimeout:
    """El cliente compartido, con el timeout de una llamada concreta."""

    def __init__(self, cliente: httpx.Client, timeout: float):
        self._cliente, self._timeout = cliente, timeout

    def post(self, *args, **kwargs):
        kwargs.setdefault('timeout', self._timeout)
        return self._cliente.post(*args, **kwargs)

    def get(self, *args, **kwargs):
        kwargs.setdefault('timeout', self._timeout)
        return self._cliente.get(*args, **kwargs)


class PipelineClient:
    """Cliente al FastAPI clínico con circuit breaker (ADR-0015 #6, SPEC-008 §8.1)."""

    def __init__(self, base_url: str, timeout: float, threshold: int, cooldown: int):
        self.base_url = base_url
        self.timeout = timeout
        self.threshold = threshold
        self.cooldown = cooldown
        self._failures = 0
        self._circuit_open_until = 0.0
        self._http: httpx.Client | None = None
        self._cerrojo = threading.Lock()

    def _cliente(self) -> httpx.Client:
        """Un solo cliente HTTP por proceso, reutilizado entre llamadas.

        Antes cada llamada creaba un `httpx.Client` nuevo. Medido el 23/10 en
        Windows: crearlo cuesta ~1 s (prepara el contexto TLS aunque se hable
        HTTP plano) y además abre una conexión nueva, que con `localhost` prueba
        primero IPv6 y pierde ~2 s más. Eran ~3 s por llamada a backend-ml:
        separar (corte + dos clasificaciones) tardaba 14 s. Con el cliente
        reutilizado, la misma petición tarda milisegundos.
        """
        with self._cerrojo:
            if self._http is None:
                self._http = _CLIENTE_REAL(timeout=self.timeout)
            return self._http

    @contextmanager
    def _sesion(self, timeout: float):
        """Lo que antes era `with httpx.Client(timeout=...) as client`.

        Con el `httpx.Client` de verdad, devuelve el cliente compartido con el
        timeout de ESTA llamada (cada método tiene el suyo). Si la clase se
        sustituyó, se comporta exactamente como antes.
        """
        if httpx.Client is not _CLIENTE_REAL:
            with httpx.Client(timeout=timeout) as client:
                yield client
            return
        yield _ConTimeout(self._cliente(), timeout)

    def _circuit_open(self) -> bool:
        return time.time() < self._circuit_open_until

    def _record_failure(self):
        self._failures += 1
        if self._failures >= self.threshold:
            self._circuit_open_until = time.time() + self.cooldown

    def _record_success(self):
        self._failures = 0

    def trigger_processing(self, sample_id: str, force_reprocess: bool = False) -> dict:
        if self._circuit_open():
            raise MLDegradedError('circuit_open')
        try:
            with self._sesion(self.timeout) as client:
                resp = client.post(
                    f'{self.base_url}/api/v1/samples/{sample_id}/process/',
                    json={'force_reprocess': force_reprocess},
                )
                resp.raise_for_status()
                self._record_success()
                return resp.json()
        except (httpx.TimeoutException, httpx.HTTPError) as exc:
            self._record_failure()
            raise MLDegradedError(str(exc)) from exc

    def get_status(self, sample_id: str) -> dict:
        try:
            with self._sesion(self.timeout) as client:
                resp = client.get(f'{self.base_url}/api/v1/samples/{sample_id}/status/')
                resp.raise_for_status()
                return resp.json()
        except (httpx.TimeoutException, httpx.HTTPError) as exc:
            raise MLDegradedError(str(exc)) from exc

    def segment_image(self, image_bytes: bytes, filename: str = 'metafase.bmp') -> dict:
        """Envía una imagen de metafase a backend-ml (/api/v1/segment/) y devuelve
        el SegmentResult (cromosomas detectados). DD-ML-002 §2.2, RN-07."""
        if self._circuit_open():
            raise MLDegradedError('circuit_open')
        try:
            with self._sesion(max(self.timeout, 30.0)) as client:
                resp = client.post(
                    f'{self.base_url}/api/v1/segment/',
                    files={'file': (filename, image_bytes, 'application/octet-stream')},
                )
                resp.raise_for_status()
                self._record_success()
                return resp.json()
        except (httpx.TimeoutException, httpx.HTTPError) as exc:
            self._record_failure()
            raise MLDegradedError(str(exc)) from exc


    def xai_heatmap(self, image_bytes: bytes, bbox: dict,
                    filename: str = 'metafase.bmp') -> dict:
        """Grad-CAM real de un cromosoma (/api/v1/xai/, ADR-0007, BR-004).

        Se manda la metafase ENTERA y el bbox, no el recorte: el preprocesado
        del clasificador usa `ref_h` —la altura mediana de todos los cromosomas
        de esa imagen— como señal de escala. Con un recorte suelto el mapa
        correspondería a una entrada que el modelo nunca vio.
        """
        if self._circuit_open():
            raise MLDegradedError('circuit_open')
        try:
            with self._sesion(max(self.timeout, 60.0)) as client:
                resp = client.post(
                    f'{self.base_url}/api/v1/xai/',
                    files={'file': (filename, image_bytes, 'application/octet-stream')},
                    data={k: int(bbox.get(k, 0)) for k in ('x', 'y', 'w', 'h')},
                )
                resp.raise_for_status()
                self._record_success()
                return resp.json()
        except (httpx.TimeoutException, httpx.HTTPError) as exc:
            self._record_failure()
            raise MLDegradedError(str(exc)) from exc


    def classify_crop(self, image_bytes: bytes, bbox: dict,
                      filename: str = 'metafase.bmp') -> dict:
        """Clasifica un recorte concreto (/api/v1/classify/).

        Se usa tras un recorte manual: la clase que se predijo sobre el recorte
        anterior deja de valer en cuanto el analista mueve el límite.
        """
        if self._circuit_open():
            raise MLDegradedError('circuit_open')
        try:
            with self._sesion(max(self.timeout, 60.0)) as client:
                resp = client.post(
                    f'{self.base_url}/api/v1/classify/',
                    files={'file': (filename, image_bytes, 'application/octet-stream')},
                    data={k: int(bbox.get(k, 0)) for k in ('x', 'y', 'w', 'h')},
                )
                resp.raise_for_status()
                self._record_success()
                return resp.json()
        except (httpx.TimeoutException, httpx.HTTPError) as exc:
            self._record_failure()
            raise MLDegradedError(str(exc)) from exc


    def contours(self, image_bytes: bytes, bboxes: list[dict],
                 filename: str = 'metafase.bmp') -> list:
        """Silueta de cada caja sobre la metafase (/api/v1/contours/, DD-KARYO-007 D1).

        Para los cariotipos segmentados antes de que backend-ml devolviera
        contornos. Devuelve una lista paralela a `bboxes`: un polígono
        `[[x, y], ...]` o None por caja.
        """
        if self._circuit_open():
            raise MLDegradedError('circuit_open')
        cajas = [{k: int(b.get(k, 0)) for k in ('x', 'y', 'w', 'h')} for b in bboxes]
        try:
            with self._sesion(max(self.timeout, 30.0)) as client:
                resp = client.post(
                    f'{self.base_url}/api/v1/contours/',
                    files={'file': (filename, image_bytes, 'application/octet-stream')},
                    data={'bboxes': json.dumps(cajas)},
                )
                resp.raise_for_status()
                self._record_success()
                contornos = resp.json().get('contornos')
        except (httpx.TimeoutException, httpx.HTTPError, ValueError) as exc:
            self._record_failure()
            raise MLDegradedError(str(exc)) from exc
        if not isinstance(contornos, list) or len(contornos) != len(cajas):
            # Una respuesta que no casa caja a caja no se puede asignar sin
            # riesgo de pegar la silueta de un cromosoma en otro.
            raise MLDegradedError('respuesta de contornos que no corresponde a las cajas')
        return contornos


    def split(self, image_bytes: bytes, bbox: dict, contour: list | None, linea: list,
              filename: str = 'metafase.bmp') -> list[dict]:
        """Separa un objeto por una línea (/api/v1/split/, DD-KARYO-007 D3).

        Devuelve los trozos `[{contour, bbox, area}]` de mayor a menor. Una línea
        que no separa el objeto es un error del ANALISTA, no de la IA: lanza
        `CorteInvalidoError` y no cuenta como fallo del circuito.
        """
        if self._circuit_open():
            raise MLDegradedError('circuit_open')
        datos = {
            'bbox': json.dumps({k: int(bbox.get(k, 0)) for k in ('x', 'y', 'w', 'h')}),
            'linea': json.dumps(linea),
        }
        if contour:
            datos['contour'] = json.dumps(contour)
        try:
            with self._sesion(max(self.timeout, 30.0)) as client:
                resp = client.post(
                    f'{self.base_url}/api/v1/split/',
                    files={'file': (filename, image_bytes, 'application/octet-stream')},
                    data=datos,
                )
            if resp.status_code == 422:
                self._record_success()   # el servicio respondió: el fallo es del trazo
                raise CorteInvalidoError(resp.json().get('detail') or 'la línea no separa el objeto')
            resp.raise_for_status()
            trozos = resp.json().get('trozos')
        except (httpx.TimeoutException, httpx.HTTPError, ValueError) as exc:
            if isinstance(exc, CorteInvalidoError):
                raise
            self._record_failure()
            raise MLDegradedError(str(exc)) from exc
        if not isinstance(trozos, list) or len(trozos) < 2:
            raise MLDegradedError('respuesta de corte sin trozos')
        self._record_success()
        return trozos

    def join(self, contornos: list[list]) -> dict:
        """Silueta y caja de la unión (/api/v1/join/, DD-KARYO-007 D4)."""
        if self._circuit_open():
            raise MLDegradedError('circuit_open')
        try:
            with self._sesion(max(self.timeout, 30.0)) as client:
                resp = client.post(f'{self.base_url}/api/v1/join/',
                                   data={'contornos': json.dumps(contornos)})
                resp.raise_for_status()
                unido = resp.json()
        except (httpx.TimeoutException, httpx.HTTPError, ValueError) as exc:
            self._record_failure()
            raise MLDegradedError(str(exc)) from exc
        if not isinstance(unido, dict) or not unido.get('contour') or not unido.get('bbox'):
            raise MLDegradedError('respuesta de unión incompleta')
        self._record_success()
        return unido


pipeline_client = PipelineClient(
    base_url=settings.CLINIC_FASTAPI_URL,
    timeout=settings.CLINIC_FASTAPI_TIMEOUT,
    threshold=settings.CLINIC_FASTAPI_CIRCUIT_THRESHOLD,
    cooldown=settings.CLINIC_FASTAPI_CIRCUIT_COOLDOWN,
)
