"""
Tests de serializers (AdminUserSerializer, AdminUserCreateSerializer, AdminUserUpdateSerializer).

Cubre validaciones de input y round-trip con la DB:
- validate_full_name: 3-80 chars
- validate_email: normaliza a lowercase
- validate_role: solo valores válidos
- validate: unicidad case-insensitive
- create: asigna created_by desde request.user si existe AdminUser
"""
import pytest

from apps.users.serializers import (
    AdminUserCreateSerializer,
    AdminUserSerializer,
    AdminUserUpdateSerializer,
    SoftDeleteResponseSerializer,
)


pytestmark = pytest.mark.django_db


def _ctx(user=None):
    """Helper para construir contexto con request DRF (no WSGI) autenticado."""
    from rest_framework.test import APIRequestFactory, force_authenticate
    from rest_framework.request import Request
    factory = APIRequestFactory()
    django_req = factory.post('/x/')
    if user is not None:
        force_authenticate(django_req, user=user)
    return {'request': Request(django_req)}


class TestAdminUserSerializerFields:
    def test_includes_expected_fields(self):
        ser = AdminUserSerializer()
        names = ser.fields.keys()
        for expected in ('id', 'full_name', 'email', 'role', 'active',
                         'created_at', 'updated_at', 'deactivated_at', 'created_by'):
            assert expected in names

    def test_readonly_fields(self):
        ser = AdminUserSerializer()
        for ro in ('id', 'created_at', 'updated_at', 'deactivated_at', 'created_by'):
            assert ser.fields[ro].read_only is True


class TestValidateFullName:
    def test_valid_full_name_passes(self):
        ser = AdminUserSerializer()
        assert ser.validate_full_name('Lucía Vargas') == 'Lucía Vargas'

    def test_strips_whitespace(self):
        ser = AdminUserSerializer()
        assert ser.validate_full_name('  Lucía  ') == 'Lucía'

    def test_short_name_raises(self):
        ser = AdminUserSerializer()
        with pytest.raises(Exception):
            ser.validate_full_name('ab')

    def test_long_name_raises(self):
        ser = AdminUserSerializer()
        with pytest.raises(Exception):
            ser.validate_full_name('x' * 81)


class TestValidateEmail:
    def test_lowercases(self):
        ser = AdminUserSerializer()
        assert ser.validate_email('UPPER@biomed.umss.bo') == 'upper@biomed.umss.bo'

    def test_strips_whitespace(self):
        ser = AdminUserSerializer()
        assert ser.validate_email('  spaced@biomed.umss.bo  ') == 'spaced@biomed.umss.bo'


class TestValidateRole:
    def test_valid_role(self):
        ser = AdminUserSerializer()
        assert ser.validate_role('admin') == 'admin'

    def test_invalid_role_raises(self):
        ser = AdminUserSerializer()
        with pytest.raises(Exception):
            ser.validate_role('hacker')


class TestValidateUniqueness:
    def test_duplicate_email_raises(self):
        from apps.users.factories import AdminUserFactory
        AdminUserFactory(email='dup@biomed.umss.bo')
        ser = AdminUserSerializer(context=_ctx())
        with pytest.raises(Exception):
            ser.validate({'email': 'dup@biomed.umss.bo', 'full_name': 'X', 'role': 'analista'})

    def test_duplicate_case_insensitive_raises(self):
        from apps.users.factories import AdminUserFactory
        AdminUserFactory(email='dup@biomed.umss.bo')
        ser = AdminUserSerializer(context=_ctx())
        with pytest.raises(Exception):
            ser.validate({'email': 'DUP@biomed.umss.bo', 'full_name': 'X', 'role': 'analista'})

    def test_self_excluded_from_uniqueness_check(self):
        from apps.users.factories import AdminUserFactory
        existing = AdminUserFactory(email='self@biomed.umss.bo')
        ser = AdminUserSerializer(context=_ctx(), instance=existing)
        # No debe lanzar porque self se excluye
        result = ser.validate({'email': 'self@biomed.umss.bo', 'full_name': 'Otro', 'role': 'analista'})
        assert result['email'] == 'self@biomed.umss.bo'


class TestCreateWithActor:
    def test_assigns_created_by_from_request_user(self, auth_user):
        from apps.users.models import AdminUser
        AdminUser.objects.create(user=auth_user, full_name='Actor', email=auth_user.email,
                                 role='admin', active=True)
        ser = AdminUserCreateSerializer(data={
            'full_name': 'Nuevo',
            'email': 'nuevo@biomed.umss.bo',
            'role': 'analista',
            'password': 'StrongPass1234',
        }, context=_ctx(user=auth_user))
        assert ser.is_valid(), ser.errors
        instance = ser.save()
        assert instance.created_by is not None
        assert instance.created_by.user == auth_user

    def test_no_actor_if_request_user_has_no_adminuser(self, auth_user):
        """Si el request.user está autenticado pero no tiene AdminUser, created_by=None."""
        ser = AdminUserCreateSerializer(data={
            'full_name': 'Bootstrap',
            'email': 'bootstrap@biomed.umss.bo',
            'role': 'admin',
            'password': 'StrongPass1234',
        }, context=_ctx(user=auth_user))
        assert ser.is_valid(), ser.errors
        instance = ser.save()
        assert instance.created_by is None


class TestCreateSerializer:
    def test_create_serializer_restricted_fields(self):
        ser = AdminUserCreateSerializer()
        # Solo los campos del alta, no id/created_at/etc
        names = set(ser.fields.keys())
        assert names == {'full_name', 'email', 'role', 'active', 'password'}


class TestUpdateSerializer:
    def test_update_serializer_fields(self):
        ser = AdminUserUpdateSerializer()
        assert set(ser.fields.keys()) == {'full_name', 'role', 'active'}

    def test_update_serializer_validates_full_name(self):
        ser = AdminUserUpdateSerializer()
        with pytest.raises(Exception):
            ser.validate_full_name('ab')

    def test_update_serializer_validates_role(self):
        ser = AdminUserUpdateSerializer()
        with pytest.raises(Exception):
            ser.validate_role('hacker')


class TestSoftDeleteResponseSerializer:
    def test_serializes_correctly(self):
        from django.utils import timezone
        ser = SoftDeleteResponseSerializer(data={
            'id': '00000000-0000-0000-0000-000000000001',
            'deactivated_at': timezone.now().isoformat(),
        })
        assert ser.is_valid(), ser.errors
        assert 'id' in ser.validated_data
        assert 'deactivated_at' in ser.validated_data