"""
Serializers de apps/config (DD-ADMIN-002).

P1: AdminProfileSerializer (este archivo).
P2: ChangePasswordSerializer, TwoFactorToggleSerializer (este archivo).
P3: ModelConfigSerializer, ModelMetricSerializer (este archivo).
P4–P6: NotificationPreference, Integration, AppearancePreference.
"""
from decimal import Decimal

from rest_framework import serializers

from .models import (
    AdminProfile,
    ModelConfig,
    ModelMetric,
    _validate_full_name,
    _normalize_email,
    _validate_phone,
)


class AdminProfileSerializer(serializers.ModelSerializer):
    """
    Serializer de perfil (P1 — DD-ADMIN-002 §2.4).

    Campos editables: full_name, email, specialty, professional_license,
                      phone, location, avatar_url.
    Campos read-only: id, updated_at (auto_now), two_factor_enabled
                      (P2 — vive en users.User, no en AdminProfile; se
                      expone acá para que el frontend conozca el estado
                      de 2FA sin un endpoint nuevo, ya que /me/profile/
                      es el "estado de mí mismo" que la SPA ya consume).
    """
    two_factor_enabled = serializers.BooleanField(source='user.two_factor_enabled', read_only=True)

    class Meta:
        model = AdminProfile
        fields = [
            'id',
            'full_name',
            'email',
            'specialty',
            'professional_license',
            'phone',
            'location',
            'avatar_url',
            'updated_at',
            'two_factor_enabled',
        ]
        read_only_fields = ['id', 'updated_at', 'two_factor_enabled']

    def validate_full_name(self, value):
        return _validate_full_name(value)

    def validate_email(self, value):
        return _normalize_email(value)

    def validate_phone(self, value):
        return _validate_phone(value)


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer de entrada para POST /api/admin/me/password/ (P2 —
    DD-ADMIN-002 §3.4/§3.5). Solo valida presencia/forma de los 3 campos;
    las reglas de negocio (fortaleza, no-reutilización, confirmación) las
    aplica services.rotate_password contra el modelo.

    trim_whitespace=False: un espacio al inicio/fin puede ser parte
    intencional de la contraseña — DRF recorta por defecto.
    """
    current = serializers.CharField(write_only=True, trim_whitespace=False)
    new = serializers.CharField(write_only=True, trim_whitespace=False)
    confirm = serializers.CharField(write_only=True, trim_whitespace=False)


class TwoFactorToggleSerializer(serializers.Serializer):
    """Serializer de entrada para POST /api/admin/me/2fa/toggle/ (P2 —
    DD-ADMIN-002 §3.4). `code` es el TOTP de 6 dígitos de la app
    autenticadora, exigido tanto para activar como para desactivar."""
    enabled = serializers.BooleanField()
    code = serializers.CharField(max_length=6, min_length=6, trim_whitespace=False)


class ModelConfigSerializer(serializers.ModelSerializer):
    """
    Serializer de la configuración activa del pipeline IA (P3 —
    DD-ADMIN-002 §4.5). `compliance_warning` es read-only, derivado de
    `ModelConfig.compliance_warning` (RN-02: threshold < 0.85).
    """
    compliance_warning = serializers.BooleanField(read_only=True)

    class Meta:
        model = ModelConfig
        fields = [
            'id', 'is_active',
            'unet_version', 'unet_enabled',
            'classifier_version', 'classifier_enabled',
            'confidence_threshold', 'detection_sensitivity',
            'analysis_mode', 'log_level',
            'updated_at', 'updated_by', 'compliance_warning',
        ]
        read_only_fields = ['id', 'is_active', 'updated_at', 'updated_by', 'compliance_warning']

    def validate_confidence_threshold(self, value: Decimal) -> Decimal:
        if not (Decimal('0') <= value <= Decimal('1')):
            raise serializers.ValidationError('Debe estar entre 0 y 1')
        return value

    def validate_detection_sensitivity(self, value: Decimal) -> Decimal:
        if not (Decimal('0') <= value <= Decimal('1')):
            raise serializers.ValidationError('Debe estar entre 0 y 1')
        return value


class ModelMetricSerializer(serializers.ModelSerializer):
    """Serializer append-only de snapshots de métricas (P3 — DD-ADMIN-002
    §4.3). Sin campos read_only especiales: el viewset no expone
    PATCH/DELETE (RN-05), así que todos los campos son de entrada válida
    únicamente en el POST de creación."""

    class Meta:
        model = ModelMetric
        fields = [
            'id', 'measured_at',
            'precision_overall', 'precision_per_class', 'recall_overall', 'f1_overall',
            'latency_p50_ms', 'latency_p95_ms', 'latency_p99_ms',
            'samples_evaluated', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']
