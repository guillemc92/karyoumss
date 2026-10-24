"""admin_client — cliente interno a backend-admin (ADR-0023 D3, DD-SUP-002).

Delega la verificación MFA de la firma del Supervisor a backend-admin (autoridad
única de credenciales, ADR-0020). Mismo patrón de circuit breaker que
pipeline_client (ADR-0015 #6): si backend-admin no responde, la firma no procede
(no se degrada silenciosamente — la firma es un acto de cumplimiento 21 CFR).
"""
import time

import httpx
from django.conf import settings


class MfaServiceError(Exception):
    """backend-admin no disponible para verificar el MFA (503)."""


class AdminClient:
    def __init__(self, base_url: str, secret: str, timeout: float, threshold: int, cooldown: int):
        self.base_url = base_url
        self.secret = secret
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

    def verify_mfa(self, email: str, code: str) -> dict:
        """POST /api/internal/mfa/verify/ → {valid: bool, enrolled: bool}."""
        if self._circuit_open():
            raise MfaServiceError('circuit_open')
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    f'{self.base_url}/api/internal/mfa/verify/',
                    json={'email': email, 'code': code},
                    headers={'X-Internal-Secret': self.secret},
                )
                resp.raise_for_status()
                self._record_success()
                return resp.json()
        except (httpx.TimeoutException, httpx.HTTPError) as exc:
            self._record_failure()
            raise MfaServiceError(str(exc)) from exc


admin_client = AdminClient(
    base_url=settings.ADMIN_INTERNAL_URL,
    secret=settings.INTERNAL_SERVICE_SECRET,
    timeout=float(getattr(settings, 'CLINIC_FASTAPI_TIMEOUT', 2.0)),
    threshold=3,
    cooldown=60,
)
