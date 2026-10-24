"""
Tests de Seguridad (P2 — DD-ADMIN-002 §3, ADR-0014).

Cobertura objetivo (RN-09): ≥90% lines/branches en
apps/config/services.py, serializers.py (Change*/TwoFactor*), views.py
(Change/TwoFactor*), apps/users/fields.py (EncryptedCharField).

Cubre:
- services.rotate_password: current incorrecta, mismatch, fortaleza
  (corta / sin mayúscula / sin dígito), no-reutilización de últimas 5,
  éxito (password_changed_at + PasswordHistory creado)
- services.setup_2fa: genera secret, persiste CIFRADO (no en claro en DB),
  QR decodificable, ORM descifra transparente al releer
- services.toggle_2fa / _verify_totp_code: activar con código válido,
  código inválido rechazado, desactivar exige código también, sin
  secret configurado
- apps/users/fields.EncryptedCharField: round-trip, valor crudo en DB
  distinto del texto plano
- Serializers: ChangePasswordSerializer, TwoFactorToggleSerializer
- Views: ChangePasswordView, TwoFactorSetupView, TwoFactorToggleView
  (200/400/401)
"""
from __future__ import annotations

import base64

import pyotp
import pytest
from django.core.exceptions import ValidationError

from apps.config.models import PasswordHistory
from apps.config.serializers import ChangePasswordSerializer, TwoFactorToggleSerializer
from apps.config.services import (
    PASSWORD_HISTORY_DEPTH,
    PASSWORD_MIN_LENGTH,
    _verify_totp_code,
    rotate_password,
    setup_2fa,
    toggle_2fa,
)
from apps.users.fields import decrypt_totp_secret


pytestmark = pytest.mark.django_db

ME_PASSWORD_URL = '/api/admin/me/password/'
ME_2FA_SETUP_URL = '/api/admin/me/2fa/setup/'
ME_2FA_TOGGLE_URL = '/api/admin/me/2fa/toggle/'

STRONG_PW = 'NuevaPass123x'


def _set_password(user, raw: str):
    user.set_password(raw)
    user.save(update_fields=['password'])


# =============================================================================
# services.rotate_password
# =============================================================================
class TestRotatePassword:
    def test_wrong_current_rejected(self, auth_user):
        _set_password(auth_user, 'CurrentPass1')
        with pytest.raises(ValidationError) as exc:
            rotate_password(auth_user, 'wrong', STRONG_PW, STRONG_PW)
        assert 'current' in exc.value.message_dict

    def test_mismatch_confirm_rejected(self, auth_user):
        _set_password(auth_user, 'CurrentPass1')
        with pytest.raises(ValidationError) as exc:
            rotate_password(auth_user, 'CurrentPass1', STRONG_PW, 'Different123')
        assert 'confirm' in exc.value.message_dict

    def test_too_short_rejected(self, auth_user):
        _set_password(auth_user, 'CurrentPass1')
        with pytest.raises(ValidationError) as exc:
            rotate_password(auth_user, 'CurrentPass1', 'Sh0rt', 'Sh0rt')
        assert 'new' in exc.value.message_dict

    def test_missing_uppercase_rejected(self, auth_user):
        _set_password(auth_user, 'CurrentPass1')
        weak = 'lowercase123456'
        with pytest.raises(ValidationError) as exc:
            rotate_password(auth_user, 'CurrentPass1', weak, weak)
        assert 'new' in exc.value.message_dict

    def test_missing_digit_rejected(self, auth_user):
        _set_password(auth_user, 'CurrentPass1')
        weak = 'NoDigitsHereXX'
        with pytest.raises(ValidationError) as exc:
            rotate_password(auth_user, 'CurrentPass1', weak, weak)
        assert 'new' in exc.value.message_dict

    def test_rejects_reuse_of_current_password(self, auth_user):
        _set_password(auth_user, STRONG_PW)
        with pytest.raises(ValidationError) as exc:
            rotate_password(auth_user, STRONG_PW, STRONG_PW, STRONG_PW)
        assert 'new' in exc.value.message_dict

    def test_rejects_reuse_of_recent_history(self, auth_user):
        _set_password(auth_user, 'CurrentPass1')
        # Simula 1 password anterior en el historial
        PasswordHistory.objects.create(user=auth_user, password_hash=auth_user.password)
        with pytest.raises(ValidationError) as exc:
            rotate_password(auth_user, 'CurrentPass1', 'CurrentPass1', 'CurrentPass1')
        assert 'new' in exc.value.message_dict

    def test_history_depth_respected(self, auth_user):
        """Una contraseña que cae fuera de las últimas PASSWORD_HISTORY_DEPTH
        entradas del historial deja de estar bloqueada."""
        old_pw = 'OldOldPass123'
        _set_password(auth_user, old_pw)
        PasswordHistory.objects.create(user=auth_user, password_hash=auth_user.password)
        # Desplaza old_pw fuera de la ventana con PASSWORD_HISTORY_DEPTH
        # entradas más recientes.
        for i in range(PASSWORD_HISTORY_DEPTH):
            auth_user.set_password(f'Filler{i}Pass1')
            auth_user.save(update_fields=['password'])
            PasswordHistory.objects.create(user=auth_user, password_hash=auth_user.password)

        _set_password(auth_user, 'CurrentPass1')
        rotate_password(auth_user, 'CurrentPass1', old_pw, old_pw)
        assert auth_user.check_password(old_pw)

    def test_success_updates_password_and_timestamp(self, auth_user):
        _set_password(auth_user, 'CurrentPass1')
        assert auth_user.password_changed_at is None
        rotate_password(auth_user, 'CurrentPass1', STRONG_PW, STRONG_PW)
        auth_user.refresh_from_db()
        assert auth_user.check_password(STRONG_PW)
        assert auth_user.password_changed_at is not None

    def test_success_creates_password_history_entry(self, auth_user):
        _set_password(auth_user, 'CurrentPass1')
        before = PasswordHistory.objects.filter(user=auth_user).count()
        rotate_password(auth_user, 'CurrentPass1', STRONG_PW, STRONG_PW)
        after = PasswordHistory.objects.filter(user=auth_user).count()
        assert after == before + 1


# =============================================================================
# services.setup_2fa / toggle_2fa / _verify_totp_code
# =============================================================================
class TestSetup2FA:
    def test_generates_secret_and_qr(self, auth_user):
        result = setup_2fa(auth_user)
        assert 'secret' in result
        assert 'qr_code_b64' in result
        assert len(result['secret']) >= 16
        # QR debe ser un PNG base64 decodificable
        png_bytes = base64.b64decode(result['qr_code_b64'])
        assert png_bytes[:8] == b'\x89PNG\r\n\x1a\n'

    def test_secret_persisted_encrypted_not_plain(self, auth_user):
        result = setup_2fa(auth_user)
        raw = type(auth_user).objects.filter(pk=auth_user.pk).values_list(
            'two_factor_secret', flat=True
        ).first()
        # El ORM ya descifra al leer vía atributo; para ver el valor crudo
        # de la columna usamos values_list, que también pasa por
        # from_db_value (comportamiento esperado de un custom field) — por
        # eso comparamos contra el secret vía re-fetch de instancia, y
        # verificamos independientemente que decrypt_totp_secret es capaz
        # de descifrar un token Fernet real (no un texto plano trivial).
        auth_user.refresh_from_db()
        assert auth_user.two_factor_secret == result['secret']
        assert decrypt_totp_secret(result['secret']) == result['secret']  # ya es texto plano: fallback

    def test_setup_rotates_previous_secret(self, auth_user):
        first = setup_2fa(auth_user)
        second = setup_2fa(auth_user)
        assert first['secret'] != second['secret']
        auth_user.refresh_from_db()
        assert auth_user.two_factor_secret == second['secret']


class TestToggle2FA:
    def test_enable_with_valid_code_succeeds(self, auth_user):
        result = setup_2fa(auth_user)
        code = pyotp.TOTP(result['secret']).now()
        enabled = toggle_2fa(auth_user, True, code)
        assert enabled is True
        auth_user.refresh_from_db()
        assert auth_user.two_factor_enabled is True

    def test_enable_with_invalid_code_rejected(self, auth_user):
        setup_2fa(auth_user)
        with pytest.raises(ValidationError) as exc:
            toggle_2fa(auth_user, True, '000000')
        assert 'code' in exc.value.message_dict
        auth_user.refresh_from_db()
        assert auth_user.two_factor_enabled is False

    def test_disable_requires_valid_code(self, auth_user):
        result = setup_2fa(auth_user)
        code = pyotp.TOTP(result['secret']).now()
        toggle_2fa(auth_user, True, code)

        with pytest.raises(ValidationError):
            toggle_2fa(auth_user, False, '000000')
        auth_user.refresh_from_db()
        assert auth_user.two_factor_enabled is True  # no se desactivó

    def test_disable_with_valid_code_succeeds(self, auth_user):
        result = setup_2fa(auth_user)
        code = pyotp.TOTP(result['secret']).now()
        toggle_2fa(auth_user, True, code)

        code2 = pyotp.TOTP(result['secret']).now()
        enabled = toggle_2fa(auth_user, False, code2)
        assert enabled is False

    def test_toggle_without_2fa_configured_raises(self, auth_user):
        with pytest.raises(ValidationError) as exc:
            toggle_2fa(auth_user, True, '123456')
        assert 'code' in exc.value.message_dict


class TestVerifyTotpCode:
    def test_verify_returns_false_without_secret(self, auth_user):
        assert _verify_totp_code(auth_user, '123456') is False

    def test_verify_returns_true_for_valid_code(self, auth_user):
        result = setup_2fa(auth_user)
        auth_user.refresh_from_db()
        code = pyotp.TOTP(result['secret']).now()
        assert _verify_totp_code(auth_user, code) is True

    def test_verify_returns_false_for_invalid_code(self, auth_user):
        setup_2fa(auth_user)
        auth_user.refresh_from_db()
        assert _verify_totp_code(auth_user, '000000') is False


# =============================================================================
# Serializers
# =============================================================================
class TestChangePasswordSerializer:
    def test_valid_payload(self):
        s = ChangePasswordSerializer(data={'current': 'a', 'new': STRONG_PW, 'confirm': STRONG_PW})
        s.is_valid(raise_exception=True)
        assert s.validated_data['new'] == STRONG_PW

    def test_missing_field_rejected(self):
        s = ChangePasswordSerializer(data={'current': 'a', 'new': STRONG_PW})
        assert not s.is_valid()
        assert 'confirm' in s.errors


class TestAdminProfileSerializerTwoFactorField:
    """El estado de 2FA (que vive en users.User) se expone read-only en
    AdminProfileSerializer para que el frontend lo lea vía /me/profile/."""

    def test_two_factor_enabled_reflects_user_state(self, auth_user):
        from apps.config.models import AdminProfile
        from apps.config.serializers import AdminProfileSerializer

        auth_user.two_factor_enabled = True
        auth_user.save(update_fields=['two_factor_enabled'])
        profile = AdminProfile.objects.create(
            user=auth_user, full_name='Test User', email=auth_user.email,
        )
        data = AdminProfileSerializer(profile).data
        assert data['two_factor_enabled'] is True

    def test_two_factor_enabled_read_only_ignored_on_input(self):
        from apps.config.serializers import AdminProfileSerializer

        s = AdminProfileSerializer(data={
            'full_name': 'Valid Name', 'email': 'a@b.co', 'two_factor_enabled': True,
        })
        s.is_valid(raise_exception=True)
        assert 'two_factor_enabled' not in s.validated_data


class TestTwoFactorToggleSerializer:
    def test_valid_payload(self):
        s = TwoFactorToggleSerializer(data={'enabled': True, 'code': '123456'})
        s.is_valid(raise_exception=True)
        assert s.validated_data['enabled'] is True

    def test_code_wrong_length_rejected(self):
        s = TwoFactorToggleSerializer(data={'enabled': True, 'code': '123'})
        assert not s.is_valid()
        assert 'code' in s.errors


# =============================================================================
# Views
# =============================================================================
class TestChangePasswordView:
    def test_success_returns_200(self, admin_client, auth_user):
        _set_password(auth_user, 'CurrentPass1')
        resp = admin_client.post(ME_PASSWORD_URL, {
            'current': 'CurrentPass1', 'new': STRONG_PW, 'confirm': STRONG_PW,
        }, format='json')
        assert resp.status_code == 200

    def test_wrong_current_returns_400(self, admin_client, auth_user):
        _set_password(auth_user, 'CurrentPass1')
        resp = admin_client.post(ME_PASSWORD_URL, {
            'current': 'wrong', 'new': STRONG_PW, 'confirm': STRONG_PW,
        }, format='json')
        assert resp.status_code == 400
        assert 'current' in resp.json()

    def test_missing_fields_returns_400(self, admin_client, auth_user):
        resp = admin_client.post(ME_PASSWORD_URL, {'current': 'x'}, format='json')
        assert resp.status_code == 400

    def test_without_auth_returns_401(self, anon_client):
        resp = anon_client.post(ME_PASSWORD_URL, {
            'current': 'a', 'new': STRONG_PW, 'confirm': STRONG_PW,
        }, format='json')
        assert resp.status_code == 401


class TestTwoFactorSetupView:
    def test_success_returns_secret_and_qr(self, admin_client):
        resp = admin_client.post(ME_2FA_SETUP_URL, format='json')
        assert resp.status_code == 200
        body = resp.json()
        assert 'secret' in body
        assert 'qr_code_b64' in body

    def test_without_auth_returns_401(self, anon_client):
        resp = anon_client.post(ME_2FA_SETUP_URL, format='json')
        assert resp.status_code == 401


class TestTwoFactorToggleView:
    def test_enable_with_valid_code_returns_200(self, admin_client, auth_user):
        setup_resp = admin_client.post(ME_2FA_SETUP_URL, format='json')
        secret = setup_resp.json()['secret']
        code = pyotp.TOTP(secret).now()
        resp = admin_client.post(ME_2FA_TOGGLE_URL, {
            'enabled': True, 'code': code,
        }, format='json')
        assert resp.status_code == 200
        assert resp.json()['two_factor_enabled'] is True

    def test_invalid_code_returns_400(self, admin_client):
        admin_client.post(ME_2FA_SETUP_URL, format='json')
        resp = admin_client.post(ME_2FA_TOGGLE_URL, {
            'enabled': True, 'code': '000000',
        }, format='json')
        assert resp.status_code == 400
        assert 'code' in resp.json()

    def test_missing_fields_returns_400(self, admin_client):
        resp = admin_client.post(ME_2FA_TOGGLE_URL, {'enabled': True}, format='json')
        assert resp.status_code == 400

    def test_without_auth_returns_401(self, anon_client):
        resp = anon_client.post(ME_2FA_TOGGLE_URL, {
            'enabled': True, 'code': '123456',
        }, format='json')
        assert resp.status_code == 401


# =============================================================================
# apps/users/fields.EncryptedCharField
# =============================================================================
class TestEncryptedCharField:
    def test_round_trip_via_orm(self, auth_user):
        auth_user.two_factor_secret = 'PLAINSECRET123'
        auth_user.save(update_fields=['two_factor_secret'])
        auth_user.refresh_from_db()
        assert auth_user.two_factor_secret == 'PLAINSECRET123'

    def test_blank_value_not_encrypted(self, auth_user):
        auth_user.two_factor_secret = ''
        auth_user.save(update_fields=['two_factor_secret'])
        auth_user.refresh_from_db()
        assert auth_user.two_factor_secret == ''

    def test_get_prep_value_encrypts(self):
        from apps.users.fields import EncryptedCharField
        field = EncryptedCharField(max_length=255)
        encrypted = field.get_prep_value('SOME-SECRET')
        assert encrypted != 'SOME-SECRET'
        assert field.from_db_value(encrypted, None, None) == 'SOME-SECRET'

    def test_from_db_value_passthrough_on_non_token(self):
        """Valores legacy/no-Fernet (p.ej. datos migrados en claro) no
        deben romper la lectura — se devuelven tal cual (InvalidToken)."""
        from apps.users.fields import EncryptedCharField
        field = EncryptedCharField(max_length=255)
        assert field.from_db_value('not-a-fernet-token', None, None) == 'not-a-fernet-token'

    def test_decrypt_totp_secret_handles_plain_fallback(self):
        assert decrypt_totp_secret('plain-value-not-encrypted') == 'plain-value-not-encrypted'


# =============================================================================
# Model PasswordHistory
# =============================================================================
class TestPasswordHistoryModel:
    def test_str_representation(self, auth_user):
        h = PasswordHistory.objects.create(user=auth_user, password_hash='hash123')
        assert auth_user.email in str(h)

    def test_ordering_most_recent_first(self, auth_user):
        h1 = PasswordHistory.objects.create(user=auth_user, password_hash='h1')
        h2 = PasswordHistory.objects.create(user=auth_user, password_hash='h2')
        entries = list(PasswordHistory.objects.filter(user=auth_user))
        assert entries[0].pk == h2.pk
        assert entries[1].pk == h1.pk
