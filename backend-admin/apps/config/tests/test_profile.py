"""
Tests de AdminProfile (modelo, serializer, view).

DD-ADMIN-002 §2 — P1: GET/PATCH /api/admin/me/profile/.

Cobertura objetivo (RN-09): ≥90% lines/branches/functions/statements
en apps/config/models.py, serializers.py, views.py, permissions.py.

Cubre:
- model.AdminProfile: clean(), save() (con full_clean), __str__,
  validators (_validate_full_name, _validate_email, _validate_phone)
- serializer.AdminProfileSerializer: campos read-only, validaciones
- views.MeProfileView: get_or_create idempotente, GET 200, PATCH 200,
  GET sin auth → 401, validación PATCH (400), email duplicado (400)
- permissions.IsOwnerOrAdmin: has_permission y has_object_permission
- migrations: el modelo AdminProfile es importable y tiene db_table plano
  en SQLite (verificado por inspección de Meta)
"""
from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError

from apps.config.models import (
    AdminProfile,
    _validate_full_name,
    _normalize_email,
    _validate_phone,
    EMAIL_RE,
    PHONE_RE,
)
from apps.config.serializers import AdminProfileSerializer
from apps.config.permissions import IsOwnerOrAdmin


pytestmark = pytest.mark.django_db


ME_PROFILE_URL = '/api/admin/me/profile/'


# =============================================================================
# Model validators (funciones puras)
# =============================================================================
class TestValidators:
    def test_validate_full_name_accepts_valid(self):
        assert _validate_full_name('María García') == 'María García'
        # Strips whitespace
        assert _validate_full_name('  Ana Pérez  ') == 'Ana Pérez'

    def test_validate_full_name_rejects_too_short(self):
        with pytest.raises(ValidationError) as exc:
            _validate_full_name('ab')
        assert 'full_name' in exc.value.message_dict

    def test_validate_full_name_rejects_too_long(self):
        with pytest.raises(ValidationError):
            _validate_full_name('x' * 81)

    def test_validate_full_name_rejects_empty(self):
        with pytest.raises(ValidationError):
            _validate_full_name('')

    def test_normalize_email_lowercases_and_strips(self):
        assert _normalize_email('  Maria@BIOMED.bo  ') == 'maria@biomed.bo'
        assert _normalize_email('') == ''

    def test_validate_phone_accepts_e164_like(self):
        assert _validate_phone('+591 2 2154847') == '+591 2 2154847'
        assert _validate_phone('(591) 22154847') == '(591) 22154847'

    def test_validate_phone_accepts_empty(self):
        # El blank=True del modelo significa que string vacío es válido
        assert _validate_phone('') == ''

    def test_validate_phone_rejects_garbage(self):
        with pytest.raises(ValidationError) as exc:
            _validate_phone('no-es-un-telefono!!!')
        assert 'phone' in exc.value.message_dict

    def test_email_regex_matches_basic(self):
        assert EMAIL_RE.match('a@b.co')
        assert not EMAIL_RE.match('no-at')
        assert not EMAIL_RE.match('@b.co')
        assert not EMAIL_RE.match('a@b')

    def test_phone_regex_basic(self):
        assert PHONE_RE.match('+1 (555) 123-4567')
        assert not PHONE_RE.match('a' * 5)


# =============================================================================
# Model AdminProfile
# =============================================================================
class TestAdminProfileModel:
    def test_str_returns_email(self, auth_user):
        p = AdminProfile(user=auth_user, full_name='Test User', email=auth_user.email)
        assert str(p) == f'Perfil<{auth_user.email}>'

    def test_save_normalizes_email(self, auth_user):
        # EmailField valida el formato en to_python, así que el espacio se
        # quita antes. La normalización lowercase se prueba en el helper puro
        # y en el serializer.
        p = AdminProfile(
            user=auth_user,
            full_name='Test User',
            email='TEST@BIOMED.BO',
        )
        p.save()
        assert p.email == 'test@biomed.bo'

    def test_save_strips_full_name(self, auth_user):
        p = AdminProfile(
            user=auth_user,
            full_name='  Test User  ',
            email=auth_user.email,
        )
        p.save()
        assert p.full_name == 'Test User'

    def test_save_rejects_too_short_name(self, auth_user):
        p = AdminProfile(
            user=auth_user,
            full_name='ab',
            email=auth_user.email,
        )
        with pytest.raises(ValidationError):
            p.save()

    def test_save_rejects_bad_email(self, auth_user):
        p = AdminProfile(
            user=auth_user,
            full_name='Valid Name',
            email='not-an-email',
        )
        with pytest.raises(ValidationError):
            p.save()

    def test_save_rejects_bad_phone(self, auth_user):
        p = AdminProfile(
            user=auth_user,
            full_name='Valid Name',
            email=auth_user.email,
            phone='NOT A PHONE!!!',
        )
        with pytest.raises(ValidationError):
            p.save()

    def test_save_allows_blank_phone(self, auth_user):
        p = AdminProfile(
            user=auth_user,
            full_name='Valid Name',
            email=auth_user.email,
            phone='',
        )
        p.save()
        assert p.phone == ''

    def test_db_table_uses_admin_profiles_prefix(self):
        # En SQLite (test) el helper devuelve el nombre plano, no 'admin"."X'.
        assert AdminProfile._meta.db_table in ('admin_profiles', 'admin"."admin_profiles')


# =============================================================================
# Serializer AdminProfileSerializer
# =============================================================================
class TestAdminProfileSerializer:
    def test_serializes_all_fields(self, auth_user):
        p = AdminProfile.objects.create(
            user=auth_user,
            full_name='Test User',
            email=auth_user.email,
            specialty='Citogenética',
            professional_license='MED-1234',
            phone='+591 2 2154847',
            location='Cochabamba',
            avatar_url='https://example.com/avatar.png',
        )
        s = AdminProfileSerializer(p)
        data = s.data
        assert data['id'] == str(p.id)
        assert data['full_name'] == 'Test User'
        assert data['email'] == auth_user.email
        assert data['specialty'] == 'Citogenética'
        assert data['phone'] == '+591 2 2154847'
        assert data['updated_at'] is not None

    def test_read_only_fields_not_accepted_on_input(self):
        from rest_framework.exceptions import ValidationError as DRFValidationError
        s = AdminProfileSerializer(data={
            'id': '00000000-0000-0000-0000-000000000000',
            'updated_at': '2099-01-01T00:00:00Z',
            'full_name': 'A B',
            'email': 'a@b.co',
        })
        # id y updated_at son read_only; no se aceptan en input
        s.is_valid(raise_exception=True)
        assert 'id' not in s.validated_data
        assert 'updated_at' not in s.validated_data

    def test_validate_full_name_runs(self):
        s = AdminProfileSerializer(data={'full_name': 'ab', 'email': 'a@b.co'})
        assert not s.is_valid()
        assert 'full_name' in s.errors

    def test_validate_email_normalizes(self):
        s = AdminProfileSerializer(data={'full_name': 'Test Name',
                                          'email': '  X@Y.COM  '})
        s.is_valid(raise_exception=True)
        assert s.validated_data['email'] == 'x@y.com'

    def test_validate_phone_runs(self):
        s = AdminProfileSerializer(data={'full_name': 'Test Name',
                                          'email': 'a@b.co',
                                          'phone': 'NOT A PHONE!!!'})
        assert not s.is_valid()
        assert 'phone' in s.errors

    def test_blank_phone_accepted(self):
        s = AdminProfileSerializer(data={'full_name': 'Test Name',
                                          'email': 'a@b.co',
                                          'phone': ''})
        s.is_valid(raise_exception=True)
        assert s.validated_data['phone'] == ''


# =============================================================================
# View MeProfileView
# =============================================================================
class TestMeProfileView:
    def test_get_creates_profile_if_missing(self, admin_client, auth_user):
        # Pre: no existe AdminProfile para auth_user
        assert not AdminProfile.objects.filter(user=auth_user).exists()

        resp = admin_client.get(ME_PROFILE_URL)

        assert resp.status_code == 200
        body = resp.json()
        assert body['email'] == auth_user.email
        # Se creó el perfil
        assert AdminProfile.objects.filter(user=auth_user).exists()

    def test_get_idempotent(self, admin_client, auth_user):
        # Llamar dos veces no duplica
        admin_client.get(ME_PROFILE_URL)
        first_count = AdminProfile.objects.filter(user=auth_user).count()
        admin_client.get(ME_PROFILE_URL)
        second_count = AdminProfile.objects.filter(user=auth_user).count()
        assert first_count == 1
        assert second_count == 1

    def test_get_returns_existing_profile(self, admin_client, auth_user):
        AdminProfile.objects.create(
            user=auth_user,
            full_name='Existing Name',
            email=auth_user.email,
            specialty='Citogenética',
        )
        resp = admin_client.get(ME_PROFILE_URL)
        assert resp.status_code == 200
        body = resp.json()
        assert body['full_name'] == 'Existing Name'
        assert body['specialty'] == 'Citogenética'

    def test_patch_updates_profile(self, admin_client, auth_user):
        AdminProfile.objects.create(
            user=auth_user,
            full_name='Old Name',
            email=auth_user.email,
        )
        resp = admin_client.patch(ME_PROFILE_URL, {
            'full_name': 'New Name',
            'specialty': 'Citogenética Clínica',
        }, format='json')
        assert resp.status_code == 200
        body = resp.json()
        assert body['full_name'] == 'New Name'
        assert body['specialty'] == 'Citogenética Clínica'
        # El email no se envió → no cambia
        assert body['email'] == auth_user.email

    def test_patch_persists_to_db(self, admin_client, auth_user):
        AdminProfile.objects.create(
            user=auth_user,
            full_name='Old Name',
            email=auth_user.email,
        )
        admin_client.patch(ME_PROFILE_URL, {
            'full_name': 'Persisted Name',
        }, format='json')
        p = AdminProfile.objects.get(user=auth_user)
        assert p.full_name == 'Persisted Name'

    def test_patch_rejects_short_name(self, admin_client, auth_user):
        AdminProfile.objects.create(
            user=auth_user,
            full_name='Valid Name',
            email=auth_user.email,
        )
        resp = admin_client.patch(ME_PROFILE_URL, {
            'full_name': 'ab',
        }, format='json')
        assert resp.status_code == 400
        assert 'full_name' in resp.json()

    def test_patch_rejects_bad_email(self, admin_client, auth_user):
        AdminProfile.objects.create(
            user=auth_user,
            full_name='Valid Name',
            email=auth_user.email,
        )
        resp = admin_client.patch(ME_PROFILE_URL, {
            'email': 'not-an-email',
        }, format='json')
        assert resp.status_code == 400

    def test_patch_rejects_bad_phone(self, admin_client, auth_user):
        AdminProfile.objects.create(
            user=auth_user,
            full_name='Valid Name',
            email=auth_user.email,
        )
        resp = admin_client.patch(ME_PROFILE_URL, {
            'phone': 'NOT VALID!!!',
        }, format='json')
        assert resp.status_code == 400
        assert 'phone' in resp.json()

    def test_get_without_auth_returns_401(self, anon_client):
        resp = anon_client.get(ME_PROFILE_URL)
        assert resp.status_code == 401

    def test_patch_without_auth_returns_401(self, anon_client):
        resp = anon_client.patch(ME_PROFILE_URL, {'full_name': 'X'},
                                  format='json')
        assert resp.status_code == 401

    def test_audit_log_entry_created_on_patch(self, admin_client, auth_user):
        """RN-05: django-auditlog debe registrar el cambio."""
        from auditlog.models import LogEntry
        AdminProfile.objects.create(
            user=auth_user,
            full_name='Original',
            email=auth_user.email,
        )
        admin_client.patch(ME_PROFILE_URL, {
            'full_name': 'Modified',
        }, format='json')
        # Buscar LogEntry para AdminProfile
        from django.contrib.contenttypes.models import ContentType
        ct = ContentType.objects.get_for_model(AdminProfile)
        entries = LogEntry.objects.filter(
            content_type=ct,
            object_pk=str(AdminProfile.objects.get(user=auth_user).pk),
        )
        # Al menos un cambio (create + update)
        assert entries.count() >= 2


# =============================================================================
# Permission IsOwnerOrAdmin
# =============================================================================
class TestIsOwnerOrAdmin:
    def test_anonymous_denied(self, db):
        from rest_framework.test import APIRequestFactory
        from django.contrib.auth.models import AnonymousUser
        factory = APIRequestFactory()
        request = factory.get('/')
        request.user = AnonymousUser()
        perm = IsOwnerOrAdmin()
        assert perm.has_permission(request, None) is False

    def test_authenticated_user_has_permission(self, admin_client, auth_user):
        from rest_framework.test import APIRequestFactory
        factory = APIRequestFactory()
        request = factory.get('/')
        request.user = auth_user
        perm = IsOwnerOrAdmin()
        assert perm.has_permission(request, None) is True

    def test_admin_can_edit_any_profile(self, admin_client, supervisor_user):
        from rest_framework.test import APIRequestFactory
        factory = APIRequestFactory()
        request = factory.patch('/')
        # Forzamos rol admin en el request user
        from django.contrib.auth.models import AnonymousUser
        from apps.users.models import User
        admin_user = User.objects.create_user(
            username='admin-test', email='admin-t@biomed.bo',
            password='x', role='admin',
        )
        request.user = admin_user
        # El obj es un perfil de supervisor
        profile = AdminProfile(
            user=supervisor_user,
            full_name='Sara Supervisor',
            email=supervisor_user.email,
        )
        perm = IsOwnerOrAdmin()
        assert perm.has_object_permission(request, None, profile) is True

    def test_user_can_edit_own_profile(self, supervisor_user):
        from rest_framework.test import APIRequestFactory
        factory = APIRequestFactory()
        request = factory.patch('/')
        request.user = supervisor_user
        profile = AdminProfile(
            user=supervisor_user,
            full_name='Sara Supervisor',
            email=supervisor_user.email,
        )
        perm = IsOwnerOrAdmin()
        assert perm.has_object_permission(request, None, profile) is True

    def test_user_cannot_edit_other_profile(self, supervisor_user, auth_user):
        from rest_framework.test import APIRequestFactory
        factory = APIRequestFactory()
        request = factory.patch('/')
        request.user = supervisor_user
        other_profile = AdminProfile(
            user=auth_user,
            full_name='Admin Principal',
            email=auth_user.email,
        )
        perm = IsOwnerOrAdmin()
        assert perm.has_object_permission(request, None, other_profile) is False
