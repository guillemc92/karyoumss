import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.samples.models_rbac import Grupo, UsuarioGrupo

User = get_user_model()


def _set_grupo_rbac(user, nombre_grupo):
    """El signal asignar_grupo_analista_por_defecto (DD-RBAC-001 §5.4)
    pone a todo usuario nuevo en 'Analista' al crearse. Los fixtures de
    supervisor/admin necesitan el grupo RBAC correcto (no solo
    is_staff/is_superuser) para que HasOpcion se comporte igual que
    ADR-0018 en los tests de regresión."""
    UsuarioGrupo.objects.filter(usuario=user).delete()
    grupo, _ = Grupo.objects.get_or_create(nombre=nombre_grupo)
    UsuarioGrupo.objects.create(usuario=user, grupo=grupo)


@pytest.fixture
def analyst_user(db):
    return User.objects.create_user(username='dra_garcia', password='testpass123')


@pytest.fixture
def supervisor_user(db):
    user = User.objects.create_user(username='sup_lopez', password='testpass123')
    user.is_staff = True
    user.save()
    _set_grupo_rbac(user, 'Supervisor')
    return user


@pytest.fixture
def admin_user(db):
    """ADR-0018: admin = is_staff + is_superuser."""
    user = User.objects.create_user(username='admin_rojas', password='testpass123')
    user.is_staff = True
    user.is_superuser = True
    user.save()
    _set_grupo_rbac(user, 'Admin')
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
