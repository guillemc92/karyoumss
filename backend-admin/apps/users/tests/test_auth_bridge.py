"""
Tests de auth_bridge.py (F0).

Cubre el flujo de canje de un JWT FastAPI por un DRF Token:
- Happy path: JWT válido firma correcta, claim role válido, claims requeridos
- JWT expirado
- JWT con firma incorrecta
- JWT sin claims requeridos
- JWT con rol inválido (no en AUTH_BRIDGE_VALID_ROLES)
- Re-entry: User existente, sincroniza role si cambió
- Genera email lowercase
"""
from datetime import timedelta

import jwt as pyjwt
import pytest

from apps.users.auth_bridge import exchange_fastapi_jwt
from apps.users.models import User


pytestmark = pytest.mark.django_db


def _make_jwt(payload: dict, secret: str = None, algorithm: str = 'HS256'):
    from django.conf import settings
    return pyjwt.encode(
        payload,
        secret or settings.AUTH_BRIDGE_SECRET,
        algorithm=algorithm,
    )


def _valid_payload(**overrides):
    from django.utils import timezone
    defaults = {
        'sub': 'test@biomed.umss.bo',
        'email': 'test@biomed.umss.bo',
        'role': 'admin',
        'exp': timezone.now() + timedelta(hours=1),
    }
    defaults.update(overrides)
    return defaults


class TestExchangeHappyPath:
    def test_creates_user_and_token(self, settings):
        payload = _valid_payload(email='new@biomed.umss.bo', role='admin')
        token_str = _make_jwt(payload)
        token, decoded = exchange_fastapi_jwt(token_str)
        assert token is not None
        assert token.key  # DRF Token tiene .key
        assert decoded['email'] == 'new@biomed.umss.bo'
        assert decoded['role'] == 'admin'
        # User fue creado
        assert User.objects.filter(email='new@biomed.umss.bo').exists()

    def test_returns_existing_token_for_existing_user(self, auth_user):
        """Si el User ya existe, devuelve su Token (no crea uno nuevo)."""
        from rest_framework.authtoken.models import Token
        existing_token = Token.objects.create(user=auth_user)
        payload = _valid_payload(
            email=auth_user.email,
            role='admin',
        )
        token_str = _make_jwt(payload)
        token, _ = exchange_fastapi_jwt(token_str)
        assert token.key == existing_token.key

    def test_email_lowercased(self):
        payload = _valid_payload(email='UPPERCASE@BIOMED.UMSS.BO', role='analista')
        token_str = _make_jwt(payload)
        _, decoded = exchange_fastapi_jwt(token_str)
        # El payload NO se modifica (viene firmado); pero el User creado debe ser lowercase.
        assert User.objects.filter(email='uppercase@biomed.umss.bo').exists()

    def test_role_synced_on_existing_user(self, supervisor_user):
        """Si el User ya existía con role distinto, sincroniza al role del JWT."""
        payload = _valid_payload(email=supervisor_user.email, role='admin')
        token_str = _make_jwt(payload)
        exchange_fastapi_jwt(token_str)
        supervisor_user.refresh_from_db()
        assert supervisor_user.role == 'admin'


class TestExchangeFailures:
    def test_expired_signature_raises(self):
        from django.utils import timezone
        payload = _valid_payload(exp=timezone.now() - timedelta(minutes=1))
        token_str = _make_jwt(payload)
        with pytest.raises(pyjwt.ExpiredSignatureError):
            exchange_fastapi_jwt(token_str)

    def test_wrong_signature_raises(self):
        payload = _valid_payload()
        token_str = _make_jwt(payload, secret='wrong-secret-' + 'a' * 60)
        with pytest.raises(pyjwt.InvalidSignatureError):
            exchange_fastapi_jwt(token_str)

    def test_missing_required_claim_raises(self):
        payload = {
            'sub': 'test@biomed.umss.bo',
            'email': 'test@biomed.umss.bo',
            # sin 'role' ni 'exp'
        }
        token_str = _make_jwt(payload)
        with pytest.raises(pyjwt.MissingRequiredClaimError):
            exchange_fastapi_jwt(token_str)

    def test_invalid_role_raises(self):
        payload = _valid_payload(role='hacker')
        token_str = _make_jwt(payload)
        with pytest.raises(pyjwt.InvalidTokenError) as exc:
            exchange_fastapi_jwt(token_str)
        assert 'rol' in str(exc.value).lower()

    def test_algorithm_confusion_raises(self):
        """Si el JWT usa un algoritmo no permitido, falla."""
        payload = _valid_payload()
        # Firma con HS512 no está en AUTH_BRIDGE_ALGORITHM (HS256)
        token_str = _make_jwt(payload, algorithm='HS512')
        with pytest.raises(pyjwt.InvalidAlgorithmError):
            exchange_fastapi_jwt(token_str)


class TestTokenReuse:
    def test_returns_same_token_on_subsequent_calls(self):
        """exchange_fastapi_jwt es idempotente: mismo email → mismo token."""
        payload = _valid_payload(email='stable@biomed.umss.bo', role='admin')
        token_str = _make_jwt(payload)
        token1, _ = exchange_fastapi_jwt(token_str)
        token2, _ = exchange_fastapi_jwt(token_str)
        assert token1.key == token2.key

    def test_different_emails_different_tokens(self):
        t1, _ = exchange_fastapi_jwt(_make_jwt(_valid_payload(email='a@biomed.umss.bo')))
        t2, _ = exchange_fastapi_jwt(_make_jwt(_valid_payload(email='b@biomed.umss.bo')))
        assert t1.key != t2.key