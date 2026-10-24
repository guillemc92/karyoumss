"""Tests del endpoint interno de verificación MFA (ADR-0023 D3, DD-SUP-002).

backend-clinic delega acá la verificación TOTP de la firma del Supervisor.
Autenticado por secreto de servicio (X-Internal-Secret), no por JWT.
"""
import pyotp
import pytest
from django.conf import settings
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

URL = '/api/internal/mfa/verify/'
SECRET = settings.INTERNAL_SERVICE_SECRET


@pytest.fixture
def client():
    return APIClient()


def _enroll(user):
    user.two_factor_secret = pyotp.random_base32()
    user.two_factor_enabled = True
    user.save(update_fields=['two_factor_secret', 'two_factor_enabled'])
    return user.two_factor_secret


class TestInternalMfaVerify:
    def test_valid_code_returns_valid_true(self, client, supervisor_user):
        secret = _enroll(supervisor_user)
        code = pyotp.TOTP(secret).now()
        resp = client.post(URL, {'email': supervisor_user.email, 'code': code}, format='json', HTTP_X_INTERNAL_SECRET=SECRET)
        assert resp.status_code == 200
        assert resp.data == {'valid': True, 'enrolled': True}

    def test_invalid_code_returns_valid_false(self, client, supervisor_user):
        _enroll(supervisor_user)
        resp = client.post(URL, {'email': supervisor_user.email, 'code': '000000'}, format='json', HTTP_X_INTERNAL_SECRET=SECRET)
        assert resp.status_code == 200
        assert resp.data == {'valid': False, 'enrolled': True}

    def test_user_without_2fa_reports_not_enrolled(self, client, supervisor_user):
        resp = client.post(URL, {'email': supervisor_user.email, 'code': '123456'}, format='json', HTTP_X_INTERNAL_SECRET=SECRET)
        assert resp.status_code == 200
        assert resp.data == {'valid': False, 'enrolled': False}

    def test_unknown_user_returns_not_enrolled(self, client):
        resp = client.post(URL, {'email': 'ghost@x.com', 'code': '123456'}, format='json', HTTP_X_INTERNAL_SECRET=SECRET)
        assert resp.status_code == 200
        assert resp.data == {'valid': False, 'enrolled': False}

    def test_wrong_service_secret_forbidden(self, client, supervisor_user):
        _enroll(supervisor_user)
        resp = client.post(URL, {'email': supervisor_user.email, 'code': '123456'}, format='json', HTTP_X_INTERNAL_SECRET='wrong')
        assert resp.status_code == 403

    def test_missing_service_secret_forbidden(self, client, supervisor_user):
        resp = client.post(URL, {'email': supervisor_user.email, 'code': '123456'}, format='json')
        assert resp.status_code == 403
