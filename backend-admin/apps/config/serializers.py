"""
Serializers de apps/config (DD-ADMIN-002).

P1: AdminProfileSerializer (este archivo).
P2–P6: ChangePassword, TwoFactorSetup, ModelConfig/Metric, NotificationPreference,
       Integration, AppearancePreference.
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
    Campos read-only: id, updated_at (auto_now).
    """

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
        ]
        read_only_fields = ['id', 'updated_at']

    def validate_full_name(self, value):
        return _validate_full_name(value)

    def validate_email(self, value):
        return _normalize_email(value)

    def validate_phone(self, value):
        return _validate_phone(value)
