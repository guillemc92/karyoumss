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
        # Contadores para `estado()` (FR1.2, FR1.5, FR3). El semáforo no expone
        # cuántos huecos ocupa ni cuántos esperan, así que se llevan aparte,
        # con un lock propio: leerlos nunca pasa por el semáforo (FR2, NFR1).
        self._contadores = threading.Lock()
        self._en_curso = 0
        self._en_espera = 0

    @classmethod
    def desde_entorno(cls) -> LimiteInferencias:
        return cls(int(os.environ.get('ML_MAX_INFERENCIAS', MAXIMO_POR_DEFECTO)),
                   float(os.environ.get('ML_ESPERA_MAX_S', ESPERA_POR_DEFECTO_S)))

    @contextmanager
    def turno(self) -> Iterator[None]:
        """Ocupa un hueco mientras dura la inferencia; 503 si no llega a tiempo.

        FR3.2: `en_espera` sube antes de pedir turno y baja en cuanto `acquire`
        vuelve, lo obtenga o se rinda. FR3.1/FR3.3: `en_curso` sube solo si hay
        turno y baja en el `finally`, también si la inferencia falla; un 503
        por espera agotada nunca lo toca.
        """
        with self._contadores:
            self._en_espera += 1
        try:
            obtenido = self._semaforo.acquire(timeout=self.espera_s)
        finally:
            with self._contadores:
                self._en_espera -= 1
        if not obtenido:
            raise HTTPException(
                status_code=503,
                detail='backend-ml ocupado: hay demasiadas inferencias en curso',
                headers={'Retry-After': str(max(1, math.ceil(self.espera_s)))},
            )
        with self._contadores:
            self._en_curso += 1
        try:
            yield
        finally:
            with self._contadores:
                self._en_curso -= 1
            self._semaforo.release()

    def estado(self) -> dict:
        """Foto del límite sin ocupar turno (FR1, FR2, NFR1).

        Devuelve `maximo`, `en_curso`, `libres` (= maximo − en_curso),
        `espera_max_s` y `en_espera`, leídos juntos bajo el lock para que
        `libres` y `en_curso` sean coherentes entre sí.
        """
        with self._contadores:
            en_curso = self._en_curso
            en_espera = self._en_espera
        return {
            'maximo': self.maximo,
            'en_curso': en_curso,
            'libres': self.maximo - en_curso,
            'espera_max_s': self.espera_s,
            'en_espera': en_espera,
        }
