"""
URL routing for apps/config (DD-ADMIN-002).

P0: config/health/ (público, smoke check).
P1: me/profile/ (autenticado, RetrieveUpdate).

Namespace: 'config'. Se monta en admin_backend/urls.py con prefijo
'/api/admin/' (igual que apps/users y apps/audit).
"""
from django.urls import path

from .views import config_health_view, MeProfileView


app_name = 'config'

urlpatterns = [
    # Health check del bounded context config.
    # GET /api/admin/config/health/  → {"status": "ok", "app": "config"}
    path('config/health/', config_health_view, name='health'),

    # P1 — Perfil del usuario autenticado.
    # GET   /api/admin/me/profile/  → detalle (crea si no existe)
    # PATCH /api/admin/me/profile/  → edición parcial
    path('me/profile/', MeProfileView.as_view(), name='me-profile'),
]
