"""
URL routing for apps/config (DD-ADMIN-002).

P0: config/health/ (público, smoke check).
P1: me/profile/ (autenticado, RetrieveUpdate).
P2: me/password/, me/2fa/setup/, me/2fa/toggle/ (autenticado, action endpoints).
P3: models/active/, models/metrics/, models/metrics/latest/ (solo admin).
P4: me/notifications/ (autenticado, RetrieveUpdate).

Namespace: 'config'. Se monta en admin_backend/urls.py con prefijo
'/api/admin/' (igual que apps/users y apps/audit).
"""
from django.urls import path

from .views import (
    config_health_view,
    ChangePasswordView,
    MeNotificationsView,
    MeProfileView,
    ModelConfigView,
    ModelMetricLatestView,
    ModelMetricListCreateView,
    TwoFactorSetupView,
    TwoFactorToggleView,
)


app_name = 'config'

urlpatterns = [
    # Health check del bounded context config.
    # GET /api/admin/config/health/  → {"status": "ok", "app": "config"}
    path('config/health/', config_health_view, name='health'),

    # P1 — Perfil del usuario autenticado.
    # GET   /api/admin/me/profile/  → detalle (crea si no existe)
    # PATCH /api/admin/me/profile/  → edición parcial
    path('me/profile/', MeProfileView.as_view(), name='me-profile'),

    # P2 — Seguridad: cambio de contraseña y 2FA.
    # POST /api/admin/me/password/    → rota la contraseña
    # POST /api/admin/me/2fa/setup/   → genera secret TOTP + QR
    # POST /api/admin/me/2fa/toggle/  → activa/desactiva 2FA (exige código)
    path('me/password/', ChangePasswordView.as_view(), name='me-password'),
    path('me/2fa/setup/', TwoFactorSetupView.as_view(), name='me-2fa-setup'),
    path('me/2fa/toggle/', TwoFactorToggleView.as_view(), name='me-2fa-toggle'),

    # P3 — Modelo IA: configuración activa (singleton) + métricas append-only.
    # GET/PATCH /api/admin/models/active/         → ModelConfig singleton
    # GET/POST  /api/admin/models/metrics/?days=N → histórico / nuevo snapshot
    # GET       /api/admin/models/metrics/latest/ → último snapshot
    path('models/active/', ModelConfigView.as_view(), name='models-active'),
    path('models/metrics/', ModelMetricListCreateView.as_view(), name='models-metrics'),
    path('models/metrics/latest/', ModelMetricLatestView.as_view(), name='models-metrics-latest'),

    # P4 — Notificaciones del usuario autenticado.
    # GET   /api/admin/me/notifications/  → detalle (crea si no existe)
    # PATCH /api/admin/me/notifications/  → edición parcial
    path('me/notifications/', MeNotificationsView.as_view(), name='me-notifications'),
]
