"""Límite de inferencias simultáneas — DD-AUD-001 F1 (issue #2, CON-02).

Una segmentación son ~19 s de CPU (medido en la auditoría de M8, 4 núcleos).
PyTorch ya reparte cada inferencia entre varios hilos, así que dos en paralelo
no terminan antes: se reparten la CPU y las dos tardan el doble. Por eso se
limita cuántas corren a la vez (`ML_MAX_INFERENCIAS`, por defecto 1) y las demás
esperan su turno.

La espera también tiene límite (`ML_ESPERA_MAX_S`, por defecto 25 s), por
debajo de los 30 s con los que corta el cliente de backend-clinic. Pasado ese
tiempo se responde 503 con `Retry-After`: es contrapresión, el cliente ya lo
trata como degradación (RN-07). Esperar más solo garantizaría que el cliente
cortara primero sin saber por qué.
"""
from __future__ import annotations

import math
import os
import threading
from contextlib import contextmanager
from typing import Iterator

from fastapi import HTTPException

MAXIMO_POR_DEFECTO = 1
ESPERA_POR_DEFECTO_S = 25.0


class LimiteInferencias:
    def __init__(self, maximo: int = MAXIMO_POR_DEFECTO,
                 espera_s: float = ESPERA_POR_DEFECTO_S) -> None:
        if maximo < 1:
            # Un límite de 0 bloquearía toda inferencia sin decir por qué.
            raise ValueError(f'ML_MAX_INFERENCIAS debe ser >= 1, no {maximo}')
        if espera_s < 0:
            raise ValueError(f'ML_ESPERA_MAX_S no puede ser negativo, no {espera_s}')
        self.maximo = maximo
        self.espera_s = espera_s
        self._semaforo = threading.BoundedSemaphore(maximo)

    @classmethod
    def desde_entorno(cls) -> LimiteInferencias:
        return cls(int(os.environ.get('ML_MAX_INFERENCIAS', MAXIMO_POR_DEFECTO)),
                   float(os.environ.get('ML_ESPERA_MAX_S', ESPERA_POR_DEFECTO_S)))

    @contextmanager
    def turno(self) -> Iterator[None]:
        """Ocupa un hueco mientras dura la inferencia; 503 si no llega a tiempo."""
        if not self._semaforo.acquire(timeout=self.espera_s):
            raise HTTPException(
                status_code=503,
                detail='backend-ml ocupado: hay demasiadas inferencias en curso',
                headers={'Retry-After': str(max(1, math.ceil(self.espera_s)))},
            )
        try:
            yield
        finally:
            self._semaforo.release()
