"""URL routing for apps/audit."""
from django.urls import path

from .views import audit_log_view


urlpatterns = [
    # /api/admin/audit/logs/ — listado paginado de LogEntry del schema admin
    path('audit/logs/', audit_log_view, name='audit-logs'),
]