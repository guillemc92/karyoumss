"""Endpoints internos service-to-service (ADR-0023 D3, DD-SUP-002).

NO usan JWT de usuario: se autentican por el header X-Internal-Secret contra
settings.INTERNAL_SERVICE_SECRET. Sólo backend-clinic los consume (delegación de
la verificación MFA de la firma del Supervisor). El secreto TOTP vive únicamente
acá (ADR-0020, autoridad única de credenciales).
"""
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import _verify_totp_code

User = get_user_model()


class InternalMfaVerifyView(APIView):
    """POST /api/internal/mfa/verify/ — verifica un código TOTP para un usuario.

    Body: {"email": "...", "code": "123456"}.
    Header: X-Internal-Secret (secreto de servicio).
    Respuesta: {"valid": bool, "enrolled": bool}. 403 si el secreto no coincide.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        provided = request.META.get('HTTP_X_INTERNAL_SECRET', '')
        if provided != settings.INTERNAL_SERVICE_SECRET:
            return Response({'code': 'FORBIDDEN', 'detail': 'Secreto de servicio inválido'}, status=status.HTTP_403_FORBIDDEN)

        email = (request.data.get('email') or '').strip().lower()
        code = request.data.get('code') or ''
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'valid': False, 'enrolled': False}, status=status.HTTP_200_OK)

        enrolled = bool(user.two_factor_enabled and user.two_factor_secret)
        valid = enrolled and _verify_totp_code(user, code)
        return Response({'valid': valid, 'enrolled': enrolled}, status=status.HTTP_200_OK)
