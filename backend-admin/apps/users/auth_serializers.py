"""
Serializers del login unificado (ADR-0017).

AdminTokenObtainPairSerializer extiende el serializer estándar de SimpleJWT
para incluir role/email/full_name en el BODY de la respuesta de login, no
solo como claim del JWT — el frontend necesita el rol inmediatamente para
decidir el redirect (D7) sin decodificar el token.
"""
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import AdminUser


def _full_name_for(user) -> str | None:
    """
    ADR-0017 D9: un User puede no tener AdminUser vinculado (creado fuera
    del CRUD, ej. vía shell/tests). full_name es null en ese caso.
    """
    try:
        return user.admin_profile.full_name
    except AdminUser.DoesNotExist:
        return None


class AdminTokenObtainPairSerializer(TokenObtainPairSerializer):
    default_error_messages = {
        'no_active_account': 'Credenciales inválidas',
    }

    def validate(self, attrs):
        data = super().validate(attrs)
        data['role'] = self.user.role
        data['email'] = self.user.email
        data['full_name'] = _full_name_for(self.user)
        return data


class MeSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.CharField()
    full_name = serializers.CharField(allow_null=True)
    username = serializers.CharField()

    @staticmethod
    def from_user(user) -> dict:
        return {
            'email': user.email,
            'role': user.role,
            'full_name': _full_name_for(user),
            'username': user.username,
        }
