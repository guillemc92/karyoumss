"""
DRF serializers for AdminUser CRUD (apps/users).
"""
from rest_framework import serializers

from .models import AdminUser, VALID_ROLES, _normalize_email, _validate_full_name


class AdminUserSerializer(serializers.ModelSerializer):
    """Serializer principal para GET / POST / PATCH."""

    class Meta:
        model = AdminUser
        fields = [
            'id',
            'full_name',
            'email',
            'role',
            'active',
            'created_at',
            'updated_at',
            'deactivated_at',
            'created_by',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'deactivated_at', 'created_by']

    def validate_full_name(self, value):
        try:
            return _validate_full_name(value)
        except Exception as e:
            raise serializers.ValidationError(str(e.message_dict if hasattr(e, 'message_dict') else e))

    def validate_email(self, value):
        return _normalize_email(value)

    def validate_role(self, value):
        if value not in VALID_ROLES:
            raise serializers.ValidationError(f'Rol inválido. Debe ser uno de: {VALID_ROLES}')
        return value

    def validate(self, attrs):
        # Unicidad case-insensitive (además del UNIQUE constraint a nivel DB).
        # El DB constraint es la autoridad final; este check es para UX temprana.
        email = attrs.get('email')
        if email:
            qs = AdminUser.objects.filter(email__iexact=email)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError({'email': 'Email ya registrado'})
        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                validated_data['created_by'] = AdminUser.objects.get(user=request.user)
            except AdminUser.DoesNotExist:
                pass  # El actor puede no tener perfil AdminUser aún (edge case bootstrap)
        return super().create(validated_data)


class AdminUserCreateSerializer(AdminUserSerializer):
    """Serializer específico para POST. Acepta solo los campos necesarios para alta."""

    class Meta(AdminUserSerializer.Meta):
        fields = ['full_name', 'email', 'role', 'active']
        read_only_fields = []


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    """Serializer específico para PATCH. Solo campos modificables (no email en MVP)."""

    class Meta:
        model = AdminUser
        fields = ['full_name', 'role', 'active']

    def validate_full_name(self, value):
        try:
            return _validate_full_name(value)
        except Exception as e:
            raise serializers.ValidationError(str(e.message_dict if hasattr(e, 'message_dict') else e))

    def validate_role(self, value):
        if value not in VALID_ROLES:
            raise serializers.ValidationError(f'Rol inválido. Debe ser uno de: {VALID_ROLES}')
        return value


class SoftDeleteResponseSerializer(serializers.Serializer):
    """Respuesta para DELETE /api/admin/users/{id}/"""
    id = serializers.UUIDField()
    deactivated_at = serializers.DateTimeField()