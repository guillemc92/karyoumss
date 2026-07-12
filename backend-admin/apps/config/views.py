"""
Vistas de apps/config (DD-ADMIN-002).

P0: config_health_view (público, smoke check).
P1: MeProfileView (este archivo — RetrieveUpdateAPIView con get_or_create).
P2–P6: vistas adicionales por sección.
"""
from rest_framework import generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import AdminProfile
from .serializers import AdminProfileSerializer


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
        'version': '0.2.0-P1',
        'sections': ['profile'],  # P1 habilitado
    })


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
