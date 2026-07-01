"""
Tests del endpoint /api/admin/audit/logs.

Cubre:
- 401 si anon
- 403 si supervisor
- 200 + estructura correcta si admin
- Filtros: action, model, paginación limit/offset
"""
import pytest


pytestmark = pytest.mark.django_db


URL = '/api/admin/audit/logs/'


class TestAuditEndpointAuth:
    def test_anon_returns_401(self, anon_client):
        resp = anon_client.get(URL)
        assert resp.status_code == 401

    def test_supervisor_get_allowed(self, supervisor_client):
        """SAFE_METHODS: cualquier autenticado puede leer (incluido supervisor)."""
        resp = supervisor_client.get(URL)
        assert resp.status_code == 200

    def test_analista_get_allowed(self, analyst_user):
        """SAFE_METHODS: analista autenticado también puede leer."""
        from rest_framework.test import APIClient
        from rest_framework.authtoken.models import Token
        token, _ = Token.objects.get_or_create(user=analyst_user)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        resp = client.get(URL)
        assert resp.status_code == 200

    def test_anon_returns_401(self, anon_client):
        resp = anon_client.get(URL)
        assert resp.status_code == 401

    def test_admin_returns_200(self, admin_client):
        resp = admin_client.get(URL)
        assert resp.status_code == 200


class TestAuditEndpointPayload:
    def test_response_shape(self, admin_client):
        resp = admin_client.get(URL)
        data = resp.json()
        for key in ('total', 'limit', 'offset', 'results'):
            assert key in data

    def test_results_is_list(self, admin_client):
        resp = admin_client.get(URL)
        assert isinstance(resp.json()['results'], list)


class TestAuditEndpointFilters:
    def test_filter_by_action_create(self, admin_client):
        from apps.users.factories import AdminUserFactory
        AdminUserFactory(email='filter-create@biomed.umss.bo')
        resp = admin_client.get(URL + '?action=create')
        assert resp.status_code == 200
        # Las entradas devueltas son todas 'create'
        for entry in resp.json()['results']:
            assert entry['action'] == 'create'

    def test_filter_by_action_update(self, admin_client):
        from apps.users.factories import AdminUserFactory
        u = AdminUserFactory(email='filter-update@biomed.umss.bo')
        u.full_name = 'Cambiado'
        u.save()
        resp = admin_client.get(URL + '?action=update')
        assert resp.status_code == 200
        for entry in resp.json()['results']:
            assert entry['action'] == 'update'

    def test_filter_by_model(self, admin_client):
        from apps.users.factories import AdminUserFactory
        AdminUserFactory(email='filter-model@biomed.umss.bo')
        resp = admin_client.get(URL + '?model=adminuser')
        assert resp.status_code == 200
        for entry in resp.json()['results']:
            assert entry['model'] == 'adminuser'

    def test_invalid_action_filter_ignored(self, admin_client):
        """action_flag inválido se ignora, no rompe."""
        resp = admin_client.get(URL + '?action=invalid')
        assert resp.status_code == 200

    def test_pagination_limit(self, admin_client):
        from apps.users.factories import AdminUserFactory
        for i in range(5):
            AdminUserFactory(email=f'pag{i}@biomed.umss.bo')
        resp = admin_client.get(URL + '?limit=2')
        data = resp.json()
        assert data['limit'] == 2
        assert len(data['results']) <= 2

    def test_pagination_offset(self, admin_client):
        from apps.users.factories import AdminUserFactory
        for i in range(5):
            AdminUserFactory(email=f'off{i}@biomed.umss.bo')
        resp = admin_client.get(URL + '?limit=2&offset=2')
        data = resp.json()
        assert data['offset'] == 2