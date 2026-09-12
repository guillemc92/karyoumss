"""Rutas internas service-to-service (ADR-0023 D3, DD-SUP-002).

Se montan bajo /api/internal/ (ver admin_backend/urls.py). Autenticadas por
secreto de servicio, no por JWT.
"""
from django.urls import path

from .internal_views import InternalMfaVerifyView

app_name = 'internal'

urlpatterns = [
    path('mfa/verify/', InternalMfaVerifyView.as_view(), name='mfa-verify'),
]
