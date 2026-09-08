"""Tests unitarios de apps/samples/permissions.py (ADR-0018)."""
import pytest

from apps.samples.permissions import IsAdminRole, IsClinicRole, IsOwnerOrStaff, role_for_user

pytestmark = pytest.mark.django_db


class TestRoleForUser:
    def test_analista(self, analyst_user):
        assert role_for_user(analyst_user) == 'analista'

    def test_supervisor(self, supervisor_user):
        assert role_for_user(supervisor_user) == 'supervisor'

    def test_admin(self, admin_user):
        assert role_for_user(admin_user) == 'admin'


class _Req:
    def __init__(self, user):
        self.user = user


class TestIsClinicRole:
    def test_authenticated_allowed(self, analyst_user):
        assert IsClinicRole().has_permission(_Req(analyst_user), None) is True

    def test_anonymous_denied(self):
        class Anon:
            is_authenticated = False
        assert IsClinicRole().has_permission(_Req(Anon()), None) is False


class TestIsAdminRole:
    def test_admin_allowed(self, admin_user):
        assert IsAdminRole().has_permission(_Req(admin_user), None) is True

    def test_supervisor_denied(self, supervisor_user):
        assert IsAdminRole().has_permission(_Req(supervisor_user), None) is False

    def test_analista_denied(self, analyst_user):
        assert IsAdminRole().has_permission(_Req(analyst_user), None) is False


class TestIsOwnerOrStaff:
    def test_owner_allowed(self, analyst_user):
        class Obj:
            analyst_id = analyst_user.id
        assert IsOwnerOrStaff().has_object_permission(_Req(analyst_user), None, Obj()) is True

    def test_non_owner_denied(self, analyst_user, django_user_model):
        other = django_user_model.objects.create_user(username='other', password='x')

        class Obj:
            analyst_id = other.id
        assert IsOwnerOrStaff().has_object_permission(_Req(analyst_user), None, Obj()) is False

    def test_supervisor_sees_any(self, supervisor_user, django_user_model):
        other = django_user_model.objects.create_user(username='other2', password='x')

        class Obj:
            analyst_id = other.id
        assert IsOwnerOrStaff().has_object_permission(_Req(supervisor_user), None, Obj()) is True
