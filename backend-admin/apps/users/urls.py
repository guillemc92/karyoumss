"""URL routing for apps/users."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import AdminUserViewSet, auth_exchange_view


router = DefaultRouter()
router.register(r'users', AdminUserViewSet, basename='admin-users')

urlpatterns = [
    path('auth/exchange', auth_exchange_view, name='auth-exchange'),
    path('', include(router.urls)),
]