"""Forma 2: la bitácora en otro servicio, por HTTP (DD-E3-001 D4).

Las protecciones son las de `eterceros/mae-ds-ai/m8/demo-resiliencia`:
- un plazo por intento;
- reintentos con *jitter*;
- un plazo total que ningún reintento puede pasar;
- un circuit breaker que, tras varios fallos seguidos, deja de llamar durante
  un rato y responde enseguida.

Sin el breaker, cada petición esperaría el plazo entero mientras la bitácora
está caída. Con hilos de gunicorn limitados, esas esperas acabarían frenando
también las rutas que no usan la bitácora.
"""
import random
import threading
import time
from uuid import UUID

import httpx
from django.conf import settings

from .puerto import BitacoraNoDisponible

JITTER_MAX_S = 0.05


class Breaker:
    """Circuit breaker de fallos seguidos, con un intento de prueba al reabrir.

    - **Cerrado:** deja pasar todo.
    - **Abierto:** tras `fallos` fallos seguidos, no deja pasar nada durante
      `reset_s` segundos.
    - **Semiabierto:** pasado ese tiempo, deja pasar UNA llamada de prueba. Si
      sale bien, se cierra; si falla, vuelve a abrirse.
    """

    def __init__(self, fallos: int, reset_s: float, reloj=time.monotonic):
        self.fallos = fallos
        self.reset_s = reset_s
        self._reloj = reloj
        self._seguidos = 0
        self._abierto_hasta: float | None = None
        self._probando = False
        self._lock = threading.Lock()

    @property
    def estado(self) -> str:
        if self._abierto_hasta is None:
            return 'cerrado'
        return 'abierto' if self._reloj() < self._abierto_hasta else 'semiabierto'

    def permite(self) -> bool:
        with self._lock:
            estado = self.estado
            if estado == 'cerrado':
                return True
            if estado == 'semiabierto' and not self._probando:
                self._probando = True
                return True
            return False

    def exito(self) -> None:
        with self._lock:
            self._seguidos = 0
            self._abierto_hasta = None
            self._probando = False

    def fallo(self) -> None:
        with self._lock:
            self._seguidos += 1
            if self._probando or self._seguidos >= self.fallos:
                self._abierto_hasta = self._reloj() + self.reset_s
            self._probando = False


class BitacoraHttp:
    def __init__(self, base_url: str, secreto: str, plazo_intento_s: float, intentos: int,
                 plazo_total_s: float, breaker: Breaker, transport: httpx.BaseTransport | None = None):
        self.plazo_intento_s = plazo_intento_s
        self.intentos = intentos
        self.plazo_total_s = plazo_total_s
        self.breaker = breaker
        # Un cliente para todo el proceso: reutiliza las conexiones (keep-alive)
        # en vez de abrir una por petición.
        self._cliente = httpx.Client(base_url=base_url, headers={'X-Internal-Secret': secreto}, transport=transport)

    @classmethod
    def desde_settings(cls) -> 'BitacoraHttp':
        return cls(
            base_url=settings.BITACORA_URL,
            secreto=settings.INTERNAL_SERVICE_SECRET,
            plazo_intento_s=settings.BITACORA_PLAZO_INTENTO_MS / 1000,
            intentos=settings.BITACORA_INTENTOS,
            plazo_total_s=settings.BITACORA_PLAZO_TOTAL_MS / 1000,
            breaker=Breaker(settings.BITACORA_BREAKER_FALLOS, settings.BITACORA_BREAKER_RESET_MS / 1000),
        )

    def listar(self, sample_id: UUID) -> list[dict]:
        if not self.breaker.permite():
            raise BitacoraNoDisponible('breaker abierto')
        limite = time.monotonic() + self.plazo_total_s
        motivo = 'sin intentos'
        for intento in range(self.intentos):
            queda = limite - time.monotonic()
            if queda <= 0:
                motivo = 'plazo total vencido'
                break
            try:
                resp = self._cliente.get(f'/internal/bitacora/{sample_id}/', timeout=min(self.plazo_intento_s, queda))
                resp.raise_for_status()
                eventos = resp.json()
            except (httpx.HTTPError, ValueError) as exc:
                motivo = f'{type(exc).__name__}: {exc}'
                if intento + 1 < self.intentos:
                    time.sleep(min(random.uniform(0, JITTER_MAX_S), max(0.0, limite - time.monotonic())))
                continue
            self.breaker.exito()
            return eventos
        self.breaker.fallo()
        raise BitacoraNoDisponible(motivo)
