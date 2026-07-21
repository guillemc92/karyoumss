"""
Vistas de apps/config (DD-ADMIN-002).

P0: config_health_view (público, smoke check).
P1: MeProfileView (RetrieveUpdateAPIView con get_or_create).
P2: ChangePasswordView, TwoFactorSetupView, TwoFactorToggleView (este archivo).
P3–P6: vistas adicionales por sección.
"""
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AdminProfile
from .serializers import AdminProfileSerializer, ChangePasswordSerializer, TwoFactorToggleSerializer
from .services import rotate_password, setup_2fa, toggle_2fa


@api_view(['GET'])
@permission_classes([AllowAny])
def config_health_view(request):
    """
    GET /api/admin/config/health/

    Respuesta:
    {
      "status": "ok",
      "app": "config",
      "version": "0.1.0-P0",
      "sections": []  # se rellena en P1–P6 con ["profile", "security", ...]
    }
    """
    return Response({
        'status': 'ok',
        'app': 'config',
        'version': '0.3.0-P2',
        'sections': ['profile', 'security'],  # P1 + P2 habilitados
    })


def _validation_error_response(exc: DjangoValidationError) -> Response:
    """Normaliza django.core.exceptions.ValidationError (dict de
    campo→[msgs] o lista plana) al shape que ya usan los clientes DRF
    del proyecto: {"campo": ["mensaje"]}."""
    if hasattr(exc, 'message_dict'):
        return Response(exc.message_dict, status=status.HTTP_400_BAD_REQUEST)
    return Response({'detail': exc.messages}, status=status.HTTP_400_BAD_REQUEST)


class MeProfileView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/admin/me/profile/  → detalle (crea si no existe)
    PATCH /api/admin/me/profile/  → edición parcial

    P1 — DD-ADMIN-002 §2.3.
    - Permisos: IsAuthenticated (cualquier usuario autenticado puede ver/editar
      su propio perfil). IsOwnerOrAdmin se aplica a nivel de objeto cuando
      se pase a una view que reciba `obj` desde el queryset, pero aquí el
      queryset se filtra por `user=self.request.user`, así que la verificación
      de objeto es trivial.
    - get_or_create idempotente: la primera vez que un usuario hace GET,
      se crea su perfil con defaults sensatos.
    """
    serializer_class = AdminProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        profile, _ = AdminProfile.objects.get_or_create(
            user=self.request.user,
            defaults={
                'full_name': self.request.user.username or self.request.user.email,
                'email': self.request.user.email,
            },
        )
        return profile


class ChangePasswordView(APIView):
    """
    POST /api/admin/me/password/ — P2, DD-ADMIN-002 §3.4/§3.5.

    Body: {"current": str, "new": str, "confirm": str}
    200: {"detail": "Contraseña actualizada"}
    400: dict de campo→[mensajes] (reglas de negocio en services.rotate_password)
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            rotate_password(
                request.user,
                serializer.validated_data['current'],
                serializer.validated_data['new'],
                serializer.validated_data['confirm'],
            )
        except DjangoValidationError as exc:
            return _validation_error_response(exc)
        return Response({'detail': 'Contraseña actualizada'}, status=status.HTTP_200_OK)


class TwoFactorSetupView(APIView):
    """
    POST /api/admin/me/2fa/setup/ — P2, DD-ADMIN-002 §3.4.

    Genera un secret TOTP nuevo (invalida cualquier QR previo no
    confirmado) y lo persiste cifrado. Sin body.
    200: {"secret": str, "qr_code_b64": str}
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        result = setup_2fa(request.user)
        return Response(result, status=status.HTTP_200_OK)


class TwoFactorToggleView(APIView):
    """
    POST /api/admin/me/2fa/toggle/ — P2, DD-ADMIN-002 §3.4.

    Body: {"enabled": bool, "code": str (6 dígitos)}
    200: {"two_factor_enabled": bool}
    400: {"code": ["Código de verificación inválido"]} u otros errores
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = TwoFactorToggleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            two_factor_enabled = toggle_2fa(
                request.user,
                serializer.validated_data['enabled'],
                serializer.validated_data['code'],
            )
        except DjangoValidationError as exc:
            return _validation_error_response(exc)
        return Response({'two_factor_enabled': two_factor_enabled}, status=status.HTTP_200_OK)
