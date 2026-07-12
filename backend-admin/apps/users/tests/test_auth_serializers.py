"""
Tests unitarios de apps/users/auth_serializers.py (ADR-0017).
"""
import pytest

from apps.users.auth_serializers import MeSerializer, _full_name_for
from apps.users.models import AdminUser

pytestmark = pytest.mark.django_db


class TestFullNameFor:
    def test_returns_full_name_when_admin_profile_exists(self, db, django_user_model):
        user = django_user_model.objects.create_user(
            username='p@biomed.umss.bo', email='p@biomed.umss.bo', password='x', role='admin',
        )
        AdminUser.objects.create(user=user, full_name='Perfil Completo', email=user.email,
                                  role='admin', active=True)
        assert _full_name_for(user) == 'Perfil Completo'

    def test_returns_none_when_no_admin_profile(self, db, django_user_model):
        user = django_user_model.objects.create_user(
            username='sinperfil@biomed.umss.bo', email='sinperfil@biomed.umss.bo',
            password='x', role='analista',
        )
        assert _full_name_for(user) is None


class TestMeSerializer:
    def test_from_user_shape(self, db, django_user_model):
        user = django_user_model.objects.create_user(
            username='shape@biomed.umss.bo', email='shape@biomed.umss.bo',
            password='x', role='analista',
        )
        data = MeSerializer.from_user(user)
        assert set(data.keys()) == {'email', 'role', 'full_name', 'username'}
        assert data['email'] == 'shape@biomed.umss.bo'
        assert data['role'] == 'analista'
