"""
Tests de AdminUserViewSet (CRUD) + auth_exchange_view + history action.

Cubre FSD-UC-ADMIN-001:
- GET    /api/admin/users/           → list
- POST   /api/admin/users/           → create (solo admin)
- GET    /api/admin/users/{uuid}/    → retrieve
- PATCH  /api/admin/users/{uuid}/    → update (solo admin)
- DELETE /api/admin/users/{uuid}/    → soft-delete (no self)
- GET    /api/admin/users/{uuid}/history/  → audit history
- POST   /api/admin/auth/exchange    → auth bridge
"""
import uuid
from datetime import timedelta

import jwt as pyjwt
import pytest

from apps.users.models import AdminUser


pytestmark = pytest.mark.django_db


LIST_URL = '/api/admin/users/'
DETAIL_FMT = '/api/admin/users/{id}/'
HISTORY_FMT = '/api/admin/users/{id}/history/'
EXCHANGE_URL = '/api/admin/auth/exchange'
STRONG_PW = 'StrongPass1234'


def _detail(u):
    return DETAIL_FMT.format(id=u.pk)


# =============================================================================
# LIST
# =============================================================================
class TestList:
    def test_admin_lists_all_active(self, admin_client, admin_user):
        resp = admin_client.get(LIST_URL)
        assert resp.status_code == 200
        results = resp.json()
        assert isinstance(results, list)
        assert any(r['id'] == str(admin_user.pk) for r in results)

    def test_anon_lists_returns_401(self, anon_client):
        resp = anon_client.get(LIST_URL)
        assert resp.status_code == 401

    def test_list_excludes_soft_deleted(self, admin_client):
        from apps.users.factories import AdminUserFactory
        from apps.users.services import soft_delete_admin_user
        active = AdminUserFactory(email='alive2@biomed.umss.bo')
        dead = AdminUserFactory(email='dead2@biomed.umss.bo')
        soft_delete_admin_user(dead)
        resp = admin_client.get(LIST_URL)
        ids = [r['id'] for r in resp.json()]
        assert str(active.pk) in ids
        assert str(dead.pk) not in ids


# =============================================================================
# CREATE
# =============================================================================
class TestCreate:
    def test_admin_creates_user(self, admin_client, admin_user):
        resp = admin_client.post(LIST_URL, data={
            'full_name': 'Nuevo Usuario',
            'email': 'nuevo@biomed.umss.bo',
            'role': 'analista',
            'password': STRONG_PW,
        }, format='json')
        assert resp.status_code == 201
        data = resp.json()
        assert data['email'] == 'nuevo@biomed.umss.bo'
        assert data['full_name'] == 'Nuevo Usuario'
        assert 'password' not in data
        assert AdminUser.objects.filter(email='nuevo@biomed.umss.bo').exists()

    def test_created_user_can_login(self, admin_client, admin_user):
        """Bug corregido 2026-07-23: un usuario creado por el CRUD debe
        poder loguearse de verdad con la password provista."""
        resp = admin_client.post(LIST_URL, data={
            'full_name': 'Puede Loguearse',
            'email': 'puedeloguearse@biomed.umss.bo',
            'role': 'analista',
            'password': STRONG_PW,
        }, format='json')
        assert resp.status_code == 201

        login_resp = admin_client.post('/api/auth/login/', data={
            'email': 'puedeloguearse@biomed.umss.bo',
            'password': STRONG_PW,
        }, format='json')
        assert login_resp.status_code == 200
        assert 'access' in login_resp.json()

    def test_create_without_password_returns_400(self, admin_client, admin_user):
        resp = admin_client.post(LIST_URL, data={
            'full_name': 'Sin Password',
            'email': 'sinpassword@biomed.umss.bo',
            'role': 'analista',
        }, format='json')
        assert resp.status_code == 400
        assert 'password' in resp.json()

    def test_create_with_weak_password_returns_400(self, admin_client, admin_user):
        resp = admin_client.post(LIST_URL, data={
            'full_name': 'Weak Password',
            'email': 'weakpassword@biomed.umss.bo',
            'role': 'analista',
            'password': 'weak',
        }, format='json')
        assert resp.status_code == 400
        assert 'password' in resp.json()

    def test_anon_creates_returns_401(self, anon_client):
        resp = anon_client.post(LIST_URL, data={
            'full_name': 'X', 'email': 'x@biomed.umss.bo', 'role': 'analista',
        }, format='json')
        assert resp.status_code == 401

    def test_supervisor_creates_returns_403(self, supervisor_client):
        resp = supervisor_client.post(LIST_URL, data={
            'full_name': 'X', 'email': 'sup-created@biomed.umss.bo', 'role': 'analista',
        }, format='json')
        assert resp.status_code == 403

    def test_duplicate_email_returns_400(self, admin_client):
        """Duplicado → ValidationError → 400 (servicio no diferencia)."""
        AdminUser.objects.create(full_name='Existing', email='dup-create@biomed.umss.bo',
                                  role='analista', active=True)
        resp = admin_client.post(LIST_URL, data={
            'full_name': 'Dup', 'email': 'dup-create@biomed.umss.bo', 'role': 'analista',
            'password': STRONG_PW,
        }, format='json')
        assert resp.status_code == 400

    def test_short_name_returns_400(self, admin_client):
        resp = admin_client.post(LIST_URL, data={
            'full_name': 'ab', 'email': 'short@biomed.umss.bo', 'role': 'analista',
            'password': STRONG_PW,
        }, format='json')
        assert resp.status_code == 400

    def test_invalid_role_returns_400(self, admin_client):
        resp = admin_client.post(LIST_URL, data={
            'full_name': 'Hacker', 'email': 'h@biomed.umss.bo', 'role': 'hacker',
            'password': STRONG_PW,
        }, format='json')
        assert resp.status_code == 400


# =============================================================================
# RETRIEVE
# =============================================================================
class TestRetrieve:
    def test_admin_retrieves(self, admin_client, admin_user):
        resp = admin_client.get(_detail(admin_user))
        assert resp.status_code == 200
        assert resp.json()['id'] == str(admin_user.pk)

    def test_not_found_returns_404(self, admin_client):
        random_uuid = uuid.uuid4()
        resp = admin_client.get(DETAIL_FMT.format(id=random_uuid))
        assert resp.status_code == 404


# =============================================================================
# UPDATE (PATCH)
# =============================================================================
class TestUpdate:
    def test_admin_updates_full_name(self, admin_client, admin_user):
        resp = admin_client.patch(_detail(admin_user), data={
            'full_name': 'Nuevo Nombre',
        }, format='json')
        assert resp.status_code == 200
        admin_user.refresh_from_db()
        assert admin_user.full_name == 'Nuevo Nombre'

    def test_admin_updates_role(self, admin_client, admin_user):
        resp = admin_client.patch(_detail(admin_user), data={
            'role': 'supervisor',
        }, format='json')
        assert resp.status_code == 200
        admin_user.refresh_from_db()
        assert admin_user.role == 'supervisor'

    def test_admin_deactivates(self, admin_client, admin_user):
        resp = admin_client.patch(_detail(admin_user), data={
            'active': False,
        }, format='json')
        assert resp.status_code == 200
        admin_user.refresh_from_db()
        assert admin_user.active is False
        assert admin_user.deactivated_at is not None

    def test_supervisor_patch_returns_403(self, supervisor_client, supervisor_admin_user):
        resp = supervisor_client.patch(_detail(supervisor_admin_user), data={
            'full_name': 'Hack',
        }, format='json')
        assert resp.status_code == 403


# =============================================================================
# DELETE (soft-delete)
# =============================================================================
class TestSoftDelete:
    def test_admin_soft_deletes_other_user(self, admin_client, supervisor_admin_user):
        resp = admin_client.delete(_detail(supervisor_admin_user))
        assert resp.status_code == 200
        supervisor_admin_user.refresh_from_db()
        assert supervisor_admin_user.active is False
        assert supervisor_admin_user.deactivated_at is not None

    def test_admin_cannot_delete_self(self, admin_client, admin_user):
        """Regla: no auto-desactivación."""
        resp = admin_client.delete(_detail(admin_user))
        assert resp.status_code == 403
        admin_user.refresh_from_db()
        assert admin_user.active is True  # sigue activo

    def test_supervisor_delete_returns_403(self, supervisor_client, supervisor_admin_user):
        resp = supervisor_client.delete(_detail(supervisor_admin_user))
        assert resp.status_code == 403

    def test_double_delete_returns_404(self, admin_client, supervisor_admin_user):
        """El segundo delete devuelve 404 porque el queryset lista solo activos (soft-deleted se ocultan)."""
        admin_client.delete(_detail(supervisor_admin_user))
        resp = admin_client.delete(_detail(supervisor_admin_user))
        assert resp.status_code == 404


# =============================================================================
# HISTORY
# =============================================================================
class TestHistory:
    def test_admin_gets_history(self, admin_client, admin_user):
        admin_user.full_name = 'Con Historia'
        admin_user.save()
        resp = admin_client.get(HISTORY_FMT.format(id=admin_user.pk))
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_history_entries_have_required_fields(self, admin_client, admin_user):
        admin_user.full_name = 'Test'
        admin_user.save()
        resp = admin_client.get(HISTORY_FMT.format(id=admin_user.pk))
        for entry in resp.json():
            for key in ('timestamp', 'action', 'actor', 'changes'):
                assert key in entry


# =============================================================================
# AUTH EXCHANGE
# =============================================================================
class TestAuthExchange:
    def test_missing_bearer_returns_401(self, anon_client):
        resp = anon_client.post(EXCHANGE_URL, format='json')
        assert resp.status_code == 401
        assert 'Bearer' in resp.json()['error']

    def test_invalid_jwt_returns_401(self, anon_client):
        resp = anon_client.post(
            EXCHANGE_URL,
            HTTP_AUTHORIZATION='Bearer invalid-jwt',
            format='json',
        )
        assert resp.status_code == 401

    def test_expired_jwt_returns_401(self, anon_client, encode_jwt, auth_bridge_payload):
        from django.utils import timezone
        payload = auth_bridge_payload(
            email='exp@biomed.umss.bo',
            exp_delta=timedelta(minutes=-1),
        )
        token = encode_jwt(payload)
        resp = anon_client.post(
            EXCHANGE_URL,
            HTTP_AUTHORIZATION=f'Bearer {token}',
            format='json',
        )
        assert resp.status_code == 401
        assert 'expired' in resp.json()['error'].lower()

    def test_valid_jwt_returns_token(self, anon_client, encode_jwt, auth_bridge_payload):
        payload = auth_bridge_payload(email='exchange@biomed.umss.bo', role='admin')
        token = encode_jwt(payload)
        resp = anon_client.post(
            EXCHANGE_URL,
            HTTP_AUTHORIZATION=f'Bearer {token}',
            format='json',
        )
        assert resp.status_code == 200
        data = resp.json()
        assert 'token' in data
        assert data['role'] == 'admin'
        assert data['email'] == 'exchange@biomed.umss.bo'
        # El token realmente funciona para autenticarse después
        from rest_framework.test import APIClient
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Token {data["token"]}')
        me = client.get(LIST_URL)
        assert me.status_code == 200

    def test_jwt_with_invalid_role_returns_401(self, anon_client, encode_jwt, auth_bridge_payload):
        payload = auth_bridge_payload(email='hacker@biomed.umss.bo', role='hacker')
        token = encode_jwt(payload)
        resp = anon_client.post(
            EXCHANGE_URL,
            HTTP_AUTHORIZATION=f'Bearer {token}',
            format='json',
        )
        assert resp.status_code == 401