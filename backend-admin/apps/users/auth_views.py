"""
Views del login unificado (ADR-0017): login, logout, me.

refresh/ no tiene wrapper propio — se monta directamente TokenRefreshView
de la librería en auth_urls.py (sin lógica custom que agregar ahí).
"""
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .auth_serializers import AdminTokenObtainPairSerializer, MeSerializer


class LoginView(TokenObtainPairView):
    """
    POST /api/auth/login/

    throttle_scope se declara sin redeclarar throttle_classes: hereda
    DEFAULT_THROTTLE_CLASSES de settings (ScopedRateThrottle en producción,
    vacío en settings_test.py) — mismo patrón que AdminUserViewSet.
    """
    serializer_class = AdminTokenObtainPairSerializer
    permission_classes = [AllowAny]
    throttle_scope = 'login'


class LogoutView(APIView):
    """POST /api/auth/logout/  Body: {"refresh": "..."}"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh = request.data.get('refresh')
        if not refresh:
            return Response({'detail': 'refresh requerido'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            RefreshToken(refresh).blacklist()
        except TokenError:
            return Response({'detail': 'Token inválido'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_205_RESET_CONTENT)


class MeView(APIView):
    """GET /api/auth/me/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(MeSerializer.from_user(request.user))
