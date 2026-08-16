import time

import httpx
from django.conf import settings


class MLDegradedError(Exception):
    """RN-07: pipeline FastAPI no disponible. El caller debe persistir la
    muestra igual y degradar la UI (DegradedBanner), no bloquear."""


class PipelineClient:
    """Cliente al FastAPI clínico con circuit breaker (ADR-0015 #6, SPEC-008 §8.1)."""

    def __init__(self, base_url: str, timeout: float, threshold: int, cooldown: int):
        self.base_url = base_url
        self.timeout = timeout
        self.threshold = threshold
        self.cooldown = cooldown
        self._failures = 0
        self._circuit_open_until = 0.0

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
            with httpx.Client(timeout=self.timeout) as client:
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
            with httpx.Client(timeout=self.timeout) as client:
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
            with httpx.Client(timeout=max(self.timeout, 30.0)) as client:
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
            with httpx.Client(timeout=max(self.timeout, 60.0)) as client:
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


pipeline_client = PipelineClient(
    base_url=settings.CLINIC_FASTAPI_URL,
    timeout=settings.CLINIC_FASTAPI_TIMEOUT,
    threshold=settings.CLINIC_FASTAPI_CIRCUIT_THRESHOLD,
    cooldown=settings.CLINIC_FASTAPI_CIRCUIT_COOLDOWN,
)
