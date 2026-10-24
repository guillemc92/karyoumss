from django.contrib import admin
from django.urls import include, path

# SSO (ADR-0020): login/refresh propios eliminados. backend-admin es la
# única autoridad de JWT del sistema — cualquier cliente que llame a
# /api/clinic/auth/login/ o /refresh/ ahora recibe 404, intencionalmente.

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/clinic/', include('apps.samples.urls')),
]
