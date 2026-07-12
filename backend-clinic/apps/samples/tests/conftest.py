import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


@pytest.fixture
def analyst_user(db):
    return User.objects.create_user(username='dra_garcia', password='testpass123')


@pytest.fixture
def supervisor_user(db):
    user = User.objects.create_user(username='sup_lopez', password='testpass123')
    user.is_staff = True
    user.save()
    return user


@pytest.fixture
def admin_user(db):
    """ADR-0018: admin = is_staff + is_superuser."""
    user = User.objects.create_user(username='admin_rojas', password='testpass123')
    user.is_staff = True
    user.is_superuser = True
    user.save()
    return user


@pytest.fixture
def api_client():
    return APIClient()


def auth_client(user):
    client = APIClient()
    token = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
    return client


@pytest.fixture
def analyst_client(analyst_user):
    return auth_client(analyst_user)


@pytest.fixture
def supervisor_client(supervisor_user):
    return auth_client(supervisor_user)


@pytest.fixture
def admin_client(admin_user):
    return auth_client(admin_user)
