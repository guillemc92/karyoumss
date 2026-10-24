"""
DRF Views for bounded context admin (apps/users).

ViewSets para CRUD de AdminUser + vista custom para auth bridge.
"""

import jwt
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.decorators import (
    action,
    api_view,
    authentication_classes,
    permission_classes,
    throttle_classes,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from .auth_bridge import exchange_fastapi_jwt
from .models import AdminUser
from .permissions import IsAdminRole
from .serializers import (
    AdminUserSerializer,
    AdminUserCreateSerializer,
    AdminUserUpdateSerializer,
    SoftDeleteResponseSerializer,
)
from .services import (
    can_delete_user,
    create_admin_user,
    soft_delete_admin_user,
    update_admin_user,
)


class AdminUserViewSet(viewsets.ModelViewSet):
    """
    /api/admin/users/

    - GET    /              → list (filtra WHERE deactivated_at IS NULL por defecto)
    - GET    /{id}/         → retrieve
    - POST   /              → create (solo admin)
    - PATCH  /{id}/         → partial_update (solo admin)
    - DELETE /{id}/         → soft_delete (solo admin, no self)
    """
    queryset = AdminUser.objects.filter(deactivated_at__isnull=True)
    serializer_class = AdminUserSerializer
    permission_classes = [IsAuthenticated, IsAdminRole]
    lookup_field = 'id'

    def get_serializer_class(self):
        if self.action == 'create':
            return AdminUserCreateSerializer
        if self.action in ('update', 'partial_update'):
            return AdminUserUpdateSerializer
        return AdminUserSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            actor = self._get_actor_admin_user(request.user)
        except AdminUser.DoesNotExist:
            actor = None
        try:
            admin_user = create_admin_user(
                full_name=serializer.validated_data['full_name'],
                email=serializer.validated_data['email'],
                role=serializer.validated_data['role'],
                password=serializer.validated_data['password'],
                active=serializer.validated_data.get('active', True),
                created_by=actor,
            )
        except Exception as e:
            # ValidationError del service
            error_msg = str(e)
            if isinstance(e, dict) or hasattr(e, 'message_dict'):
                return Response(e.message_dict if hasattr(e, 'message_dict') else e,
                                status=status.HTTP_400_BAD_REQUEST)
            if 'Email ya registrado' in error_msg:
                return Response({'email': 'Email ya registrado'},
                                status=status.HTTP_409_CONFLICT)
            return Response({'detail': error_msg}, status=status.HTTP_400_BAD_REQUEST)

        out = AdminUserSerializer(admin_user)
        return Response(out.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = AdminUserUpdateSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            update_admin_user(
                instance,
                full_name=serializer.validated_data.get('full_name'),
                role=serializer.validated_data.get('role'),
                active=serializer.validated_data.get('active'),
            )
        except Exception as e:
            error_msg = str(e)
            return Response({'detail': error_msg}, status=status.HTTP_400_BAD_REQUEST)
        return Response(AdminUserSerializer(instance).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        # Regla: no auto-desactivación
        if not can_delete_user(instance, request.user.id):
            return Response(
                {'detail': 'No puede desactivarse a sí mismo'},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            actor = self._get_actor_admin_user(request.user)
        except AdminUser.DoesNotExist:
            actor = None
        try:
            soft_delete_admin_user(instance, actor=actor)
        except Exception as e:
            error_msg = str(e)
            if 'ya está desactivado' in error_msg:
                return Response({'detail': error_msg}, status=status.HTTP_409_CONFLICT)
            return Response({'detail': error_msg}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            SoftDeleteResponseSerializer({
                'id': instance.id,
                'deactivated_at': instance.deactivated_at,
            }).data,
            status=status.HTTP_200_OK,
        )

    def _get_actor_admin_user(self, user) -> AdminUser:
        """Obtiene el AdminUser asociado al User autenticado."""
        return AdminUser.objects.get(user=user)

    @action(detail=True, methods=['get'], url_path='history')
    def history(self, request, id=None):
        """
        GET /api/admin/users/{id}/history
        Devuelve el historial de cambios del usuario (django-auditlog LogEntry).
        """
        admin_user = self.get_object()
        from auditlog.models import LogEntry
        # LogEntry.action: 0=create, 1=update, 2=delete
        entries = LogEntry.objects.filter(
            object_pk=str(admin_user.pk),
            content_type__model='adminuser',
        ).order_by('-timestamp')[:50]

        data = [
            {
                'timestamp': e.timestamp.isoformat(),
                'action': {0: 'create', 1: 'update', 2: 'delete'}.get(e.action, 'unknown'),
                'actor': e.actor.username if e.actor else None,
                'changes': e.changes or {},
            }
            for e in entries
        ]
        return Response(data)


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([AllowAny])
@throttle_classes([ScopedRateThrottle])
def auth_exchange_view(request):
    """
    POST /api/admin/auth/exchange
    Headers: Authorization: Bearer <fastapi_jwt>
    Body: (vacío)
    Response 200: { "token": "<django_token>", "role": "admin", "expires_at": "..." }

    ADR-0017: `authentication_classes` se fija explícitamente a solo
    TokenAuthentication (excluyendo el JWTAuthentication global agregado por
    ADR-0017) porque este endpoint recibe un JWT ajeno (firmado con
    AUTH_BRIDGE_SECRET, no con AUTH_ADMIN_JWT_SECRET) en el header
    `Authorization: Bearer`, que se parsea manualmente más abajo — no como
    credencial de autenticación de este propio backend. Sin este override,
    JWTAuthentication intenta validar ese Bearer como su propio JWT, falla la
    firma, y aborta la cadena de autenticación completa con 401 antes de que
    el cuerpo de esta vista llegue a ejecutarse.
    """
    if not getattr(request, 'throttle_classes', None):
        request.throttle_classes = [ScopedRateThrottle]
    request.throttle_scope = 'auth_exchange'

    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth_header.startswith('Bearer '):
        return Response(
            {'error': 'Missing Bearer token'},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    fastapi_jwt = auth_header[len('Bearer '):]
    try:
        token, payload = exchange_fastapi_jwt(fastapi_jwt)
    except jwt.ExpiredSignatureError:
        return Response({'error': 'FastAPI JWT expired'}, status=status.HTTP_401_UNAUTHORIZED)
    except jwt.InvalidTokenError as e:
        return Response({'error': f'Invalid FastAPI JWT: {e}'}, status=status.HTTP_401_UNAUTHORIZED)

    return Response({
        'token': token.key,
        'role': payload['role'],
        'email': payload['email'],
        'expires_at': timezone.now() + timezone.timedelta(hours=24),  # Django Token TTL
    }, status=status.HTTP_200_OK)