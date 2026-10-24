"""SSO (ADR-0020) — SharedJWTAuthentication valida el JWT firmado por
backend-admin (mismo secreto, AUTH_ADMIN_JWT_SECRET) y sincroniza el
User local de backend-clinic a partir de los claims {email, role}.

Mismo patrón que backend-admin/apps/users/auth_bridge.py (exchange F0),
en la dirección inversa: aquí no hay un endpoint de exchange explícito,
la sincronización ocurre transparentemente en cada request autenticado
vía get_user() (override de JWTAuthentication). No modifica
role_for_user()/tiene_opcion() (ADR-0018/0019) — solo cambia de dónde
sale el User sobre el que esas funciones operan.
"""
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken


class SharedJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        email = validated_token.get('email')
        role = validated_token.get('role')
        if not email:
            raise InvalidToken('Token sin claim email — no es un token válido de backend-admin')

        User = get_user_model()
        user, _created = User.objects.get_or_create(
            username=email, defaults={'email': email},
        )
        is_staff = role in ('supervisor', 'admin')
        is_superuser = role == 'admin'
        if user.is_staff != is_staff or user.is_superuser != is_superuser:
            user.is_staff = is_staff
            user.is_superuser = is_superuser
            user.save(update_fields=['is_staff', 'is_superuser'])
        return user
