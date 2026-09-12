"""
Tests de POST /api/auth/login/ (ADR-0017, SPEC-010 UC-A-001/UC-A-002/UC-A-003).
"""
import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

LOGIN_URL = '/api/auth/login/'


@pytest.fixture
def login_user(db, django_user_model):
    user = django_user_model.objects.create_user(
        username='login@biomed.umss.bo',
        email='login@biomed.umss.bo',
        password='correcta12345',
        role='admin',
    )
    return user


class TestLoginSuccess:
    def test_login_returns_access_refresh_role_email(self, login_user):
        resp = APIClient().post(
            LOGIN_URL, {'email': login_user.email, 'password': 'correcta12345'}, format='json',
        )
        assert resp.status_code == 200
        data = resp.json()
        assert 'access' in data and 'refresh' in data
        assert data['role'] == 'admin'
        assert data['email'] == login_user.email

    def test_login_full_name_null_without_admin_profile(self, login_user):
        # login_user no tiene AdminUser vinculado (creado directo con create_user)
        resp = APIClient().post(
            LOGIN_URL, {'email': login_user.email, 'password': 'correcta12345'}, format='json',
        )
        assert resp.json()['full_name'] is None

    def test_login_full_name_present_with_admin_profile(self, db, django_user_model):
        from apps.users.models import AdminUser
        user = django_user_model.objects.create_user(
            username='conperfil@biomed.umss.bo', email='conperfil@biomed.umss.bo',
            password='correcta12345', role='supervisor',
        )
        AdminUser.objects.create(user=user, full_name='Sara Supervisor', email=user.email,
                                  role='supervisor', active=True)
        resp = APIClient().post(
            LOGIN_URL, {'email': user.email, 'password': 'correcta12345'}, format='json',
        )
        assert resp.json()['full_name'] == 'Sara Supervisor'

    def test_login_analista_role(self, db, django_user_model):
        user = django_user_model.objects.create_user(
            username='ana@biomed.umss.bo', email='ana@biomed.umss.bo',
            password='correcta12345', role='analista',
        )
        resp = APIClient().post(
            LOGIN_URL, {'email': user.email, 'password': 'correcta12345'}, format='json',
        )
        assert resp.json()['role'] == 'analista'


class TestLoginFailure:
    def test_wrong_password_401(self, login_user):
        resp = APIClient().post(
            LOGIN_URL, {'email': login_user.email, 'password': 'incorrecta'}, format='json',
        )
        assert resp.status_code == 401
        assert resp.json()['detail'] == 'Credenciales inválidas'

    def test_nonexistent_email_401_same_message(self, login_user):
        resp = APIClient().post(
            LOGIN_URL, {'email': 'no-existe@biomed.umss.bo', 'password': 'x'}, format='json',
        )
        assert resp.status_code == 401
        assert resp.json()['detail'] == 'Credenciales inválidas'

    def test_inactive_user_401(self, login_user):
        login_user.is_active = False
        login_user.save(update_fields=['is_active'])
        resp = APIClient().post(
            LOGIN_URL, {'email': login_user.email, 'password': 'correcta12345'}, format='json',
        )
        assert resp.status_code == 401

    def test_missing_password_400(self, login_user):
        resp = APIClient().post(LOGIN_URL, {'email': login_user.email}, format='json')
        assert resp.status_code == 400
