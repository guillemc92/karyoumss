"""
Vistas de apps/config (DD-ADMIN-002).

P0: config_health_view (público, smoke check).
P1: MeProfileView (RetrieveUpdateAPIView con get_or_create).
P2: ChangePasswordView, TwoFactorSetupView, TwoFactorToggleView (este archivo).
P3: ModelConfigView, ModelMetricListCreateView, ModelMetricLatestView (este archivo).
P4: MeNotificationsView (este archivo).
P6: MeAppearanceView (este archivo). P5 diferida.
"""
from datetime import timedelta

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import IsAdminRole

from .models import AdminProfile, AppearancePreference, ModelConfig, ModelMetric, NotificationPreference
from .serializers import (
    AdminProfileSerializer,
    AppearancePreferenceSerializer,
    ChangePasswordSerializer,
    ModelConfigSerializer,
    ModelMetricSerializer,
    NotificationPreferenceSerializer,
    TwoFactorToggleSerializer,
)
from .services import rotate_password, setup_2fa, toggle_2fa

DAYS_DEFAULT = 30
DAYS_MAX = 365


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
        'version': '0.6.0-P6',
        'sections': ['profile', 'security', 'modelos', 'notifications', 'appearance'],  # P1-P4+P6 (P5 diferida)
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


class ModelConfigView(APIView):
    """
    GET/PATCH /api/admin/models/active/ — P3, DD-ADMIN-002 §4.4.

    Singleton lógico: la primera vez que se pide, se crea con defaults
    (`get_or_create` semántico). `select_for_update` dentro de una
    transacción reduce la ventana de race condition en creación
    concurrente (DD §4.2, riesgo #6); el `UniqueConstraint` en el modelo
    es la última línea de defensa si dos requests igual llegan a
    intentar crear a la vez.
    """
    permission_classes = [IsAdminRole]

    def _get_active(self) -> ModelConfig:
        with transaction.atomic():
            config = ModelConfig.objects.select_for_update().filter(is_active=True).first()
            if config is None:
                config = ModelConfig.objects.create(is_active=True)
            return config

    def get(self, request):
        return Response(ModelConfigSerializer(self._get_active()).data)

    def patch(self, request):
        config = self._get_active()
        serializer = ModelConfigSerializer(config, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(updated_by=request.user)
        return Response(serializer.data)


class ModelMetricListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/admin/models/metrics/?days=30  → histórico filtrado
    POST /api/admin/models/metrics/          → snapshot nuevo (append-only)

    P3 — DD-ADMIN-002 §4.4. RN-05: no hay update/delete en este viewset
    (`ListCreateAPIView` no los expone), así que una fila nunca se
    modifica ni se borra tras crearse.
    """
    serializer_class = ModelMetricSerializer
    permission_classes = [IsAdminRole]

    def get_queryset(self):
        raw_days = self.request.query_params.get('days', str(DAYS_DEFAULT))
        try:
            days = int(raw_days)
        except (TypeError, ValueError):
            days = DAYS_DEFAULT
        days = max(1, min(days, DAYS_MAX))
        since = timezone.now() - timedelta(days=days)
        return ModelMetric.objects.filter(measured_at__gte=since)


class ModelMetricLatestView(APIView):
    """GET /api/admin/models/metrics/latest/ — último snapshot (P3).

    204 sin body si todavía no hay ningún snapshot (demo/instalación nueva).
    """
    permission_classes = [IsAdminRole]

    def get(self, request):
        latest = ModelMetric.objects.first()  # Meta.ordering = ['-measured_at']
        if latest is None:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(ModelMetricSerializer(latest).data)


class MeNotificationsView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/admin/me/notifications/  → detalle (crea si no existe)
    PATCH /api/admin/me/notifications/  → edición parcial

    P4 — DD-ADMIN-002 §5.3. Mismo patrón que MeProfileView: preferencias
    propias del usuario autenticado, get_or_create idempotente, sin
    necesidad de IsOwnerOrAdmin a nivel de objeto porque el queryset ya
    se filtra por `user=self.request.user`.
    """
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        prefs, created = NotificationPreference.objects.get_or_create(user=self.request.user)
        if created:
            # Los defaults de TimeField ('20:00') quedan como string crudo
            # en la instancia recién creada hasta el próximo round-trip a
            # la DB — sin este refresh, la primera respuesta serializa
            # "20:00" y las siguientes "20:00:00" (mismo valor, formato
            # inconsistente para el frontend).
            prefs.refresh_from_db()
        return prefs


class MeAppearanceView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/admin/me/appearance/  → detalle (crea si no existe)
    PATCH /api/admin/me/appearance/  → edición parcial

    P6 — DD-ADMIN-002 §7.3. Mismo patrón que MeProfileView/MeNotificationsView.
    """
    serializer_class = AppearancePreferenceSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        prefs, _ = AppearancePreference.objects.get_or_create(user=self.request.user)
        return prefs
