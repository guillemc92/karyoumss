from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/clinic/auth/login/', TokenObtainPairView.as_view(), name='clinic-login'),
    path('api/clinic/auth/refresh/', TokenRefreshView.as_view(), name='clinic-refresh'),
    path('api/clinic/', include('apps.samples.urls')),
]
