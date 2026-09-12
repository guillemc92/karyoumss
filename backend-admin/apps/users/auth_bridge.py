"""
Auth bridge (F0) — canjea FastAPI JWT por Django Token.

Ver docs/AUTH_BRIDGE.md para el flujo completo.
"""

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework.authtoken.models import Token


def exchange_fastapi_jwt(fastapi_jwt: str) -> tuple[Token, dict]:
    """
    Valida el JWT de FastAPI con el secret compartido, busca/crea User en Django,
    y devuelve un DRF Token.

    Raises:
        jwt.InvalidTokenError: JWT inválido, expirado, o firma incorrecta.
        jwt.MissingRequiredClaimError: JWT sin claims requeridos.

    Returns:
        (token, payload) tuple. payload contiene los claims del JWT FastAPI.
    """
    payload = jwt.decode(
        fastapi_jwt,
        settings.AUTH_BRIDGE_SECRET,
        algorithms=[settings.AUTH_BRIDGE_ALGORITHM],
        options={'require': settings.AUTH_BRIDGE_REQUIRED_CLAIMS},
    )

    if payload.get('role') not in settings.AUTH_BRIDGE_VALID_ROLES:
        raise jwt.InvalidTokenError(f"Rol inválido en JWT: {payload.get('role')}")

    User = get_user_model()
    email = payload['email'].strip().lower()

    with transaction.atomic():
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': email,
                'role': payload['role'],
                'is_active': True,
            },
        )
        # Si ya existía, sincronizar role por si cambió en FastAPI
        if not created and user.role != payload['role']:
            user.role = payload['role']
            user.save(update_fields=['role'])

        # Crear/actualizar AdminUser de dominio (no bloquear el exchange si falla
        # el seed del dominio — el exchange sigue siendo válido aunque el usuario
        # sea solo de auth; el admin puede luego darlo de alta manualmente).
        from .models import AdminUser
        domain_user, domain_created = AdminUser.objects.get_or_create(
            user=user,
            defaults={
                'full_name': _derive_full_name_from_email(email),
                'email': email,
                'role': payload['role'],
                'active': True,
            },
        )
        if not domain_created and domain_user.role != payload['role']:
            domain_user.role = payload['role']
            domain_user.save(update_fields=['role'])

    token, _ = Token.objects.get_or_create(user=user)
    return token, payload


def _derive_full_name_from_email(email: str) -> str:
    """
    Genera un full_name a partir del email cuando AdminUser se crea vía exchange
    y no tenemos un nombre real (el JWT FastAPI no lo trae por defecto).
    Convención: la parte local del email capitalizada + padding a 3 chars mínimo
    para satisfacer la validación de _validate_full_name (3-80 chars).
    """
    local = email.split('@', 1)[0]
    # Reemplaza separadores comunes por espacios y capitaliza cada palabra.
    pretty = ' '.join(part for part in local.replace('.', ' ').replace('_', ' ').split() if part)
    pretty = pretty.title() if pretty else 'Usuario Biomed'
    # Padding defensivo (la validación exige 3-80 chars).
    # Caso borde: emails como "a@x" → "A" (1 char). Usamos 'Biomed' como sufijo
    # para llegar a 3+ sin perder el prefijo derivado.
    if len(pretty) < 3:
        pretty = f'{pretty} Biomed'.strip()
    return pretty.ljust(3)[:80]