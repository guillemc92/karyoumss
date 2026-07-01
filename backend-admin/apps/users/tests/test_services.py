"""
Tests de servicios puros (apps/users/services.py).

No tocan HTTP ni DRF — solo la lógica de negocio.
Cubren RN-09 ≥90% del archivo services.py.
"""
import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.users.factories import AdminUserFactory, UserFactory
from apps.users.services import (
    can_delete_user,
    create_admin_user,
    soft_delete_admin_user,
    update_admin_user,
    validate_email_format,
)


pytestmark = pytest.mark.django_db


class TestCreateAdminUser:
    def test_creates_with_valid_data(self):
        u = create_admin_user(
            full_name='Lucía Vargas',
            email='lucia@biomed.umss.bo',
            role='supervisor',
            active=True,
        )
        assert u.pk is not None
        assert u.email == 'lucia@biomed.umss.bo'
        assert u.role == 'supervisor'
        assert u.active is True

    def test_normalizes_email_to_lowercase(self):
        u = create_admin_user(
            full_name='Carlos Pinto',
            email='  Carlos.Pinto@BIOMED.umss.bo  ',
            role='analista',
        )
        assert u.email == 'carlos.pinto@biomed.umss.bo'

    def test_strips_full_name_whitespace(self):
        u = create_admin_user(
            full_name='  María López  ',
            email='maria@biomed.umss.bo',
            role='analista',
        )
        assert u.full_name == 'María López'

    def test_defaults_active_to_true(self):
        u = create_admin_user(
            full_name='Test Default',
            email='td@biomed.umss.bo',
            role='analista',
        )
        assert u.active is True

    def test_assigns_created_by(self):
        creator = AdminUserFactory(email='creator@biomed.umss.bo')
        u = create_admin_user(
            full_name='Hijo de Creator',
            email='hijo@biomed.umss.bo',
            role='analista',
            created_by=creator,
        )
        assert u.created_by_id == creator.pk

    def test_rejects_short_full_name(self):
        with pytest.raises(ValidationError):
            create_admin_user(
                full_name='ab',
                email='short@biomed.umss.bo',
                role='analista',
            )

    def test_rejects_long_full_name(self):
        with pytest.raises(ValidationError):
            create_admin_user(
                full_name='x' * 81,
                email='long@biomed.umss.bo',
                role='analista',
            )

    def test_rejects_invalid_role(self):
        with pytest.raises(ValidationError) as exc:
            create_admin_user(
                full_name='Bad Role',
                email='badrole@biomed.umss.bo',
                role='hacker',
            )
        assert 'rol' in str(exc.value).lower() or 'role' in str(exc.value).lower()

    def test_rejects_duplicate_email(self):
        AdminUserFactory(email='dup@biomed.umss.bo')
        with pytest.raises(ValidationError) as exc:
            create_admin_user(
                full_name='Duplicado',
                email='dup@biomed.umss.bo',
                role='analista',
            )
        assert 'email' in str(exc.value).lower()


class TestUpdateAdminUser:
    def test_updates_full_name(self):
        u = AdminUserFactory(full_name='Original')
        update_admin_user(u, full_name='Actualizado')
        u.refresh_from_db()
        assert u.full_name == 'Actualizado'

    def test_updates_role(self):
        u = AdminUserFactory(role='analista')
        update_admin_user(u, role='supervisor')
        u.refresh_from_db()
        assert u.role == 'supervisor'

    def test_updates_active(self):
        u = AdminUserFactory(active=True)
        update_admin_user(u, active=False)
        u.refresh_from_db()
        assert u.active is False

    def test_deactivating_sets_deactivated_at(self):
        u = AdminUserFactory(active=True)
        assert u.deactivated_at is None
        update_admin_user(u, active=False)
        u.refresh_from_db()
        assert u.deactivated_at is not None

    def test_reactivating_clears_deactivated_at(self):
        u = AdminUserFactory(active=False, deactivated_at=timezone.now())
        update_admin_user(u, active=True)
        u.refresh_from_db()
        assert u.deactivated_at is None

    def test_no_op_returns_same_instance(self):
        u = AdminUserFactory()
        result = update_admin_user(u)
        assert result.pk == u.pk

    def test_rejects_invalid_role(self):
        u = AdminUserFactory(role='analista')
        with pytest.raises(ValidationError):
            update_admin_user(u, role='hacker')

    def test_rejects_short_full_name(self):
        u = AdminUserFactory()
        with pytest.raises(ValidationError):
            update_admin_user(u, full_name='ab')


class TestSoftDelete:
    def test_soft_delete_sets_deactivated_at(self):
        u = AdminUserFactory(active=True)
        assert u.deactivated_at is None
        soft_delete_admin_user(u)
        u.refresh_from_db()
        assert u.active is False
        assert u.deactivated_at is not None

    def test_soft_delete_idempotent_raises(self):
        from django.utils import timezone
        u = AdminUserFactory(active=False, deactivated_at=timezone.now())
        with pytest.raises(ValidationError) as exc:
            soft_delete_admin_user(u)
        assert 'desactivado' in str(exc.value).lower()

    def test_soft_delete_deactivates_associated_user(self):
        u = AdminUserFactory(active=True)
        user = u.user
        assert user.is_active is True
        soft_delete_admin_user(u)
        user.refresh_from_db()
        assert user.is_active is False

    def test_soft_delete_without_user_does_not_fail(self):
        u = AdminUserFactory(active=True)
        u.user = None
        u.save()
        # no debe lanzar
        soft_delete_admin_user(u)
        u.refresh_from_db()
        assert u.active is False


class TestCanDeleteUser:
    def test_returns_true_when_current_user_id_none(self):
        u = AdminUserFactory()
        assert can_delete_user(u, None) is True

    def test_returns_true_for_different_users(self):
        u = AdminUserFactory()
        assert can_delete_user(u, current_user_id=999) is True

    def test_returns_false_for_self(self):
        u = AdminUserFactory()
        # AdminUser.user_id es el FK al User; si current_user.id == u.user_id
        # entonces NO puede desactivarse a sí mismo.
        current_user = u.user
        assert can_delete_user(u, current_user.id) is False


class TestValidateEmailFormat:
    def test_valid_email_passes(self):
        result = validate_email_format('test@biomed.umss.bo')
        assert result == 'test@biomed.umss.bo'

    def test_uppercase_normalized(self):
        result = validate_email_format('UPPER@biomed.umss.bo')
        assert result == 'upper@biomed.umss.bo'

    def test_whitespace_trimmed(self):
        result = validate_email_format('  spaced@biomed.umss.bo  ')
        assert result == 'spaced@biomed.umss.bo'

    def test_invalid_format_raises(self):
        with pytest.raises(ValidationError):
            validate_email_format('not-an-email')

    def test_empty_raises(self):
        with pytest.raises(ValidationError):
            validate_email_format('')

    def test_none_raises(self):
        with pytest.raises(ValidationError):
            validate_email_format(None)