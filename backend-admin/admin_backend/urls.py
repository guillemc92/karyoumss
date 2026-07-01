"""
URL routing for backend-admin (bounded context admin).
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/admin/', include('apps.users.urls')),
    path('api/admin/', include('apps.audit.urls')),
]