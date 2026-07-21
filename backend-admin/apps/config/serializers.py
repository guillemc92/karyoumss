"""
Serializers de apps/config (DD-ADMIN-002).

P1: AdminProfileSerializer (este archivo).
P2: ChangePasswordSerializer, TwoFactorToggleSerializer (este archivo).
P3–P6: ModelConfig/Metric, NotificationPreference, Integration, AppearancePreference.
"""
from rest_framework import serializers

from .models import (
    AdminProfile,
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
