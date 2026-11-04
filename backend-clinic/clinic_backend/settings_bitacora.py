"""Punto de entrada del servicio extraído de la bitácora (DD-E3-001 D3).

Es la misma imagen y el mismo código que la API. Solo cambian las rutas: aquí
no hay nada clínico, solo la lectura interna de la bitácora.
"""
from .settings import *  # noqa: F401,F403

ROOT_URLCONF = 'clinic_backend.urls_bitacora'
