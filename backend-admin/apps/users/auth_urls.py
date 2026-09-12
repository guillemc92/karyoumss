"""URL routing del login unificado (ADR-0017). Montado en /api/auth/."""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .auth_views import LoginView, LogoutView, MeView

urlpatterns = [
    path('login/', LoginView.as_view(), name='auth-login'),
    path('logout/', LogoutView.as_view(), name='auth-logout'),
    path('refresh/', TokenRefreshView.as_view(), name='auth-refresh'),
    path('me/', MeView.as_view(), name='auth-me'),
]
