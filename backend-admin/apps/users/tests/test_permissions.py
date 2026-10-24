"""
Tests de permissions (IsAdminRole, IsAdminOrSelf).

Verifica la matriz de autorización del bounded context admin:
- Anon: 401
- Autenticado rol no-admin en GET: 200 (lectura permitida)
- Autenticado rol no-admin en POST/PATCH/DELETE: 403
- Admin en cualquier método: 200/201
"""
import pytest
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.users.permissions import IsAdminOrSelf, IsAdminRole


pytestmark = pytest.mark.django_db


def _drf_request(method='GET', user=None):
    """Crea un DRF Request con autenticación forzada (sin pasar por Django middleware)."""
    factory = APIRequestFactory()
    django_req = getattr(factory, method.lower())('/x/')
    if user is not None:
        force_authenticate(django_req, user=user)
    from rest_framework.request import Request
    return Request(django_req)


class TestIsAdminRole:
    def test_anon_denied(self):
        from django.contrib.auth.models import AnonymousUser
        perm = IsAdminRole()
        req = _drf_request('GET', user=AnonymousUser())
        assert perm.has_permission(req, view=None) is False

    def test_admin_get_allowed(self, auth_user):
        perm = IsAdminRole()
        req = _drf_request('GET', user=auth_user)
        assert perm.has_permission(req, view=None) is True

    def test_admin_post_allowed(self, auth_user):
        perm = IsAdminRole()
        req = _drf_request('POST', user=auth_user)
        assert perm.has_permission(req, view=None) is True

    def test_supervisor_get_allowed(self, supervisor_user):
        """SAFE_METHODS: cualquier autenticado puede leer."""
        perm = IsAdminRole()
        req = _drf_request('GET', user=supervisor_user)
        assert perm.has_permission(req, view=None) is True

    def test_supervisor_post_denied(self, supervisor_user):
        perm = IsAdminRole()
        req = _drf_request('POST', user=supervisor_user)
        assert perm.has_permission(req, view=None) is False

    def test_supervisor_delete_denied(self, supervisor_user):
        perm = IsAdminRole()
        req = _drf_request('DELETE', user=supervisor_user)
        assert perm.has_permission(req, view=None) is False

    def test_analista_patch_denied(self, analyst_user):
        perm = IsAdminRole()
        req = _drf_request('PATCH', user=analyst_user)
        assert perm.has_permission(req, view=None) is False


class TestIsAdminOrSelf:
    """Tests del permiso a nivel objeto (no a nivel request)."""

    def test_admin_can_edit_any_object(self, auth_user, supervisor_admin_user):
        perm = IsAdminOrSelf()
        req = _drf_request('PATCH', user=auth_user)
        assert perm.has_object_permission(req, view=None, obj=supervisor_admin_user) is True

    def test_non_admin_cannot_edit_other_user(self, supervisor_user, analyst_user):
        perm = IsAdminOrSelf()
        req = _drf_request('PATCH', user=supervisor_user)
        # Obj con user_id distinto al del request → False
        class FakeObj:
            user_id = analyst_user.id + 999
        assert perm.has_object_permission(req, view=None, obj=FakeObj()) is False

    def test_non_admin_can_edit_self(self, supervisor_user):
        perm = IsAdminOrSelf()
        req = _drf_request('PATCH', user=supervisor_user)
        class FakeObj:
            user_id = supervisor_user.id
        assert perm.has_object_permission(req, view=None, obj=FakeObj()) is True

    def test_non_admin_no_user_id_attribute_denied(self, supervisor_user):
        perm = IsAdminOrSelf()
        req = _drf_request('PATCH', user=supervisor_user)
        class FakeObjNoUserId:
            pass
        assert perm.has_object_permission(req, view=None, obj=FakeObjNoUserId()) is False

    def test_anon_denied(self):
        from django.contrib.auth.models import AnonymousUser
        perm = IsAdminOrSelf()
        req = _drf_request('GET', user=AnonymousUser())
        class FakeObj:
            user_id = 1
        assert perm.has_object_permission(req, view=None, obj=FakeObj()) is False