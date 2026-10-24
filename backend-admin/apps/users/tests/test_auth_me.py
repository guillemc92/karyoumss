"""
Tests de GET /api/auth/me/ (ADR-0017, SPEC-010 UC-A-004).
"""
import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

LOGIN_URL = '/api/auth/login/'
ME_URL = '/api/auth/me/'


@pytest.fixture
def access_token(db, django_user_model):
    django_user_model.objects.create_user(
        username='me@biomed.umss.bo', email='me@biomed.umss.bo',
        password='correcta12345', role='supervisor',
    )
    resp = APIClient().post(
        LOGIN_URL, {'email': 'me@biomed.umss.bo', 'password': 'correcta12345'}, format='json',
    )
    return resp.json()['access']


class TestMe:
    def test_me_requires_auth(self):
        resp = APIClient().get(ME_URL)
        assert resp.status_code == 401

    def test_me_returns_current_user_data(self, access_token):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        resp = client.get(ME_URL)
        assert resp.status_code == 200
        data = resp.json()
        assert data['email'] == 'me@biomed.umss.bo'
        assert data['role'] == 'supervisor'
        assert data['full_name'] is None
        assert data['username'] == 'me@biomed.umss.bo'

    def test_me_rejects_invalid_token(self):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION='Bearer not-a-real-token')
        resp = client.get(ME_URL)
        assert resp.status_code == 401
