"""
Conftest raíz de pytest para backend-admin (F6).

Carga Django, expone fixtures reutilizables en todos los tests:
- admin_client: APIClient autenticado como admin (rol=admin)
- supervisor_client: APIClient autenticado como supervisor (para verificar 403)
- admin_user: AdminUser de dominio
- auth_user: Django auth User (para token)
- admin_token: DRF Token del admin user

Convención de naming:
- `apps/users/test_*.py` cubre models/services/views/permissions/auth_bridge/serializers
- `apps/audit/test_*.py`  cubre audit endpoints
- `conftest.py` global solo expone fixtures; tests específicos pueden tener su
  propio conftest.py para fixtures locales.
"""
from __future__ import annotations

import pytest
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient


@pytest.fixture(autouse=True)
def _enable_db_access(db):
    """
    django.test pytest-django provee `db` para acceso a DB. autouse=True hace
    que todos los tests tengan acceso sin declararlo. db isolation entre tests
    está activado por default (cada test corre en una transacción revertida).
    """
    return db


@pytest.fixture
def auth_user(db, django_user_model):
    """Django auth User con rol admin — usado para DRF Token."""
    return django_user_model.objects.create_user(
        username='admin@biomed.umss.bo',
        email='admin@biomed.umss.bo',
        password='test-pass-not-used',
        role='admin',
        is_staff=True,
    )


@pytest.fixture
def supervisor_user(db, django_user_model):
    """Django auth User con rol supervisor — usado para verificar 403 en mutaciones."""
    return django_user_model.objects.create_user(
        username='supervisor@biomed.umss.bo',
        email='supervisor@biomed.umss.bo',
        password='test-pass-not-used',
        role='supervisor',
    )


@pytest.fixture
def analyst_user(db, django_user_model):
    """Django auth User con rol analista."""
    return django_user_model.objects.create_user(
        username='analista@biomed.umss.bo',
        email='analista@biomed.umss.bo',
        password='test-pass-not-used',
        role='analista',
    )


@pytest.fixture
def admin_user(db, auth_user):
    """AdminUser de dominio vinculado al auth user admin."""
    from apps.users.models import AdminUser
    return AdminUser.objects.create(
        user=auth_user,
        full_name='Admin Principal',
        email=auth_user.email,
        role='admin',
        active=True,
    )


@pytest.fixture
def supervisor_admin_user(db, supervisor_user):
    """AdminUser de dominio vinculado al supervisor."""
    from apps.users.models import AdminUser
    return AdminUser.objects.create(
        user=supervisor_user,
        full_name='Sara Supervisor',
        email=supervisor_user.email,
        role='supervisor',
        active=True,
    )


@pytest.fixture
def admin_token(auth_user):
    """DRF Token del admin user."""
    token, _ = Token.objects.get_or_create(user=auth_user)
    return token


@pytest.fixture
def supervisor_token(supervisor_user):
    token, _ = Token.objects.get_or_create(user=supervisor_user)
    return token


@pytest.fixture
def admin_client(admin_token):
    """APIClient autenticado como admin (rol=admin)."""
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Token {admin_token.key}')
    return client


@pytest.fixture
def supervisor_client(supervisor_token):
    """APIClient autenticado como supervisor (para tests 403)."""
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Token {supervisor_token.key}')
    return client


@pytest.fixture
def anon_client():
    """APIClient sin autenticación (para tests 401)."""
    return APIClient()


@pytest.fixture
def auth_bridge_payload():
    """
    Factory de payloads JWT válidos para el auth_bridge.

    Uso:
        payload = auth_bridge_payload(email='test@biomed.umss.bo', role='admin')
        token = encode_jwt(payload)  # ver helpers en apps/users/test_auth_bridge.py
    """
    from datetime import datetime, timedelta, timezone

    def _make(email: str = 'test@biomed.umss.bo', role: str = 'admin',
              exp_delta: timedelta = timedelta(hours=1),
              extra_claims: dict | None = None) -> dict:
        payload = {
            'sub': email,
            'email': email,
            'role': role,
            'exp': datetime.now(tz=timezone.utc) + exp_delta,
        }
        if extra_claims:
            payload.update(extra_claims)
        return payload

    return _make


@pytest.fixture
def encode_jwt(settings):
    """
    Factory que codifica un payload a JWT firmado con el secret del settings de test.

    Uso:
        token = encode_jwt(auth_bridge_payload())
    """
    import jwt

    def _encode(payload: dict, secret: str | None = None) -> str:
        return jwt.encode(payload, secret or settings.AUTH_BRIDGE_SECRET,
                         algorithm=settings.AUTH_BRIDGE_ALGORITHM)
    return _encode