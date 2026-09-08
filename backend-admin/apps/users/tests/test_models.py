"""
Tests del modelo AdminUser: branches de clean(), reactivate().

Objetivo: llevar models.py por encima del 90%.
- test_reactivate_resets_deactivated_at → cubre models.py:233-242
- test_clean_rejects_invalid_role → cubre models.py:210-211
"""
from django.core.exceptions import ValidationError
from django.utils import timezone

import pytest

from apps.users.factories import AdminUserFactory
from apps.users.models import AdminUser


pytestmark = pytest.mark.django_db


class TestReactivate:
    def test_reactivate_resets_deactivated_at(self):
        u = AdminUserFactory(active=False, deactivated_at=timezone.now())
        u.reactivate()
        u.refresh_from_db()
        assert u.active is True
        assert u.deactivated_at is None

    def test_reactivate_also_reactivates_user(self):
        from apps.users.factories import UserFactory
        user = UserFactory(email='reactivate@biomed.umss.bo', is_active=False)
        u = AdminUserFactory(email='reactivate@biomed.umss.bo', user=user,
                              active=False, deactivated_at=timezone.now())
        u.reactivate()
        user.refresh_from_db()
        assert user.is_active is True

    def test_reactivate_already_active_raises(self):
        u = AdminUserFactory(active=True)
        with pytest.raises(ValidationError):
            u.reactivate()


class TestCleanMethod:
    def test_clean_rejects_invalid_role(self):
        u = AdminUserFactory()
        u.role = 'hacker'
        with pytest.raises(ValidationError):
            u.full_clean()

    def test_clean_normalizes_email(self):
        u = AdminUserFactory()
        u.email = 'UPPER@biomed.umss.bo'
        u.full_clean()
        assert u.email == 'upper@biomed.umss.bo'

    def test_clean_normalizes_full_name(self):
        u = AdminUserFactory()
        u.full_name = '  Spaces Here  '
        u.full_clean()
        assert u.full_name == 'Spaces Here'

    def test_clean_rejects_short_name(self):
        u = AdminUserFactory()
        u.full_name = 'ab'
        with pytest.raises(ValidationError):
            u.full_clean()


class TestVendorAwareDbTable:
    def test_default_db_table_in_sqlite_is_plain(self):
        from apps.users.models import _admin_schema_table
        # En settings_test.py el ENGINE es sqlite3 → nombre plano
        assert _admin_schema_table('users_user') == 'users_user'
        assert _admin_schema_table('admin_users') == 'admin_users'

    def test_postgres_engine_returns_schema_qualified(self):
        """Si forzamos motor postgres, _admin_schema_table devuelve nombre con schema."""
        from django.test import override_settings
        with override_settings(DATABASES={
            'default': {'ENGINE': 'django.db.backends.postgresql'}
        }):
            from apps.users.models import _admin_schema_table
            assert 'admin' in _admin_schema_table('users_user')
