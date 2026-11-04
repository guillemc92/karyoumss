"""Rutas del servicio extraído de la bitácora (DD-E3-001 D3)."""
from django.urls import path

from apps.samples.bitacora.servicio import BitacoraInternaView, salud

urlpatterns = [
    path('internal/bitacora/<uuid:sample_id>/', BitacoraInternaView.as_view(), name='bitacora-interna'),
    path('salud/', salud, name='bitacora-salud'),
]
