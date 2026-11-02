"""El lado del servicio extraído: lo que expone por HTTP (DD-E3-001 D3).

Es una ruta interna, sin JWT ni RBAC. La protege el secreto de servicio, y
el permiso del usuario ya lo comprobó la API antes de llamar.
"""
import hmac

from django.conf import settings
from django.http import JsonResponse
from rest_framework.response import Response
from rest_framework.views import APIView

from .en_proceso import eventos_de


def _secreto_valido(request) -> bool:
    recibido = request.headers.get('X-Internal-Secret', '')
    return hmac.compare_digest(recibido.encode(), settings.INTERNAL_SERVICE_SECRET.encode())


class BitacoraInternaView(APIView):
    """GET /internal/bitacora/{sample_id}/ → los eventos del caso."""

    authentication_classes: list = []
    permission_classes: list = []

    def get(self, request, sample_id):
        if not _secreto_valido(request):
            return Response({'code': 'FORBIDDEN', 'detail': 'Secreto de servicio inválido'}, status=403)
        return Response(eventos_de(sample_id))


def salud(request):
    """GET /salud/ → 200. Para el healthcheck del contenedor."""
    return JsonResponse({'servicio': 'bitacora', 'ok': True})
