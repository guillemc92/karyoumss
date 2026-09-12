"""
Tests de POST /api/auth/logout/ y POST /api/auth/refresh/ (ADR-0017, SPEC-010 UC-A-004).
"""
import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

LOGIN_URL = '/api/auth/login/'
LOGOUT_URL = '/api/auth/logout/'
REFRESH_URL = '/api/auth/refresh/'


@pytest.fixture
def tokens(db, django_user_model):
    django_user_model.objects.create_user(
        username='logout@biomed.umss.bo', email='logout@biomed.umss.bo',
        password='correcta12345', role='admin',
    )
    resp = APIClient().post(
        LOGIN_URL, {'email': 'logout@biomed.umss.bo', 'password': 'correcta12345'}, format='json',
    )
    return resp.json()


class TestLogout:
    def test_logout_requires_auth(self, tokens):
        resp = APIClient().post(LOGOUT_URL, {'refresh': tokens['refresh']}, format='json')
        assert resp.status_code == 401

    def test_logout_blacklists_refresh(self, tokens):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        resp = client.post(LOGOUT_URL, {'refresh': tokens['refresh']}, format='json')
        assert resp.status_code == 205

    def test_refresh_fails_after_logout(self, tokens):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        client.post(LOGOUT_URL, {'refresh': tokens['refresh']}, format='json')

        resp = APIClient().post(REFRESH_URL, {'refresh': tokens['refresh']}, format='json')
        assert resp.status_code == 401

    def test_logout_missing_refresh_400(self, tokens):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        resp = client.post(LOGOUT_URL, {}, format='json')
        assert resp.status_code == 400

    def test_logout_invalid_refresh_400(self, tokens):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        resp = client.post(LOGOUT_URL, {'refresh': 'not-a-real-token'}, format='json')
        assert resp.status_code == 400

    def test_logout_twice_second_is_400(self, tokens):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        first = client.post(LOGOUT_URL, {'refresh': tokens['refresh']}, format='json')
        second = client.post(LOGOUT_URL, {'refresh': tokens['refresh']}, format='json')
        assert first.status_code == 205
        assert second.status_code == 400


class TestRefresh:
    def test_refresh_returns_new_access(self, tokens):
        resp = APIClient().post(REFRESH_URL, {'refresh': tokens['refresh']}, format='json')
        assert resp.status_code == 200
        assert 'access' in resp.json()

    def test_refresh_rotates_refresh_token(self, tokens):
        resp = APIClient().post(REFRESH_URL, {'refresh': tokens['refresh']}, format='json')
        assert resp.json()['refresh'] != tokens['refresh']
