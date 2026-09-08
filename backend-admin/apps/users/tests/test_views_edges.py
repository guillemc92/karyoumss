"""
Tests de edge-cases de views: ramas de excepción y branches de get_serializer_class.

Objetivo: llevar `views.py` por encima del 90% de cobertura.
- test_update_full → get_serializer_class → AdminUserUpdateSerializer branch
- test_partial_update_invalid_role → ValidationError → 400
- test_create_admin_no_actor_branch → actor=None cuando el User autenticado no tiene AdminUser
"""
import pytest

from apps.users.models import AdminUser


pytestmark = pytest.mark.django_db


LIST_URL = '/api/admin/users/'
DETAIL_FMT = '/api/admin/users/{id}/'
STRONG_PW = 'StrongPass1234'


class TestUpdateSerializerBranch:
    def test_partial_update_uses_update_serializer(self, admin_client, admin_user):
        """Cuando action=partial_update, get_serializer_class devuelve UpdateSerializer."""
        resp = admin_client.patch(DETAIL_FMT.format(id=admin_user.pk), data={
            'full_name': 'Solo Update Serializer',
        }, format='json')
        assert resp.status_code == 200
        admin_user.refresh_from_db()
        assert admin_user.full_name == 'Solo Update Serializer'

    def test_full_update_path(self, admin_client, admin_user):
        """PUT (full update) → también usa UpdateSerializer."""
        resp = admin_client.put(DETAIL_FMT.format(id=admin_user.pk), data={
            'full_name': 'Full Update Test',
            'role': 'supervisor',
            'active': True,
        }, format='json')
        assert resp.status_code == 200
        admin_user.refresh_from_db()
        assert admin_user.full_name == 'Full Update Test'
        assert admin_user.role == 'supervisor'


class TestPartialUpdateFailures:
    def test_partial_update_invalid_role(self, admin_client, admin_user):
        resp = admin_client.patch(DETAIL_FMT.format(id=admin_user.pk), data={
            'role': 'hacker',
        }, format='json')
        assert resp.status_code == 400

    def test_partial_update_invalid_full_name(self, admin_client, admin_user):
        resp = admin_client.patch(DETAIL_FMT.format(id=admin_user.pk), data={
            'full_name': 'ab',
        }, format='json')
        assert resp.status_code == 400


class TestCreateNoActorBranch:
    def test_create_when_actor_has_no_adminuser(self, admin_client):
        """Si request.user es admin pero no tiene AdminUser propio, created_by=None.

        Branch de _get_actor_admin_user → actor=None en línea 60-61 de views.py.
        """
        resp = admin_client.post(LIST_URL, data={
            'full_name': 'Bootstrap Admin',
            'email': 'bootstrap-admin@biomed.umss.bo',
            'role': 'analista',
            'password': STRONG_PW,
        }, format='json')
        assert resp.status_code == 201
        u = AdminUser.objects.get(email='bootstrap-admin@biomed.umss.bo')
        assert u.created_by is None


class TestCreateErrorBranches:
    def test_create_returns_detail_on_unexpected_validation(self, admin_client, admin_user):
        """Disparar ruta 'detail' línea 79 views.py: ValidationError genérico."""
        # full_name muy corto → ValidationError → cae al except genérico
        resp = admin_client.post(LIST_URL, data={
            'full_name': 'X' * 200,  # >80 chars
            'email': 'too-long@biomed.umss.bo',
            'role': 'analista',
            'password': STRONG_PW,
        }, format='json')
        # El serializer capturará validate_full_name; pero si pasa, el service raise.
        assert resp.status_code in (400,)

    def test_create_returns_dict_when_validation_has_message_dict(self, admin_client, admin_user, monkeypatch):
        """Si el service raise ValidationError con message_dict, devuelve ese dict.

        Branch de `hasattr(e, 'message_dict')` en views.py:74-75.
        """
        from django.core.exceptions import ValidationError as DjangoValidationError
        from apps.users import views as users_views

        original = users_views.create_admin_user
        def boom(**kwargs):
            raise DjangoValidationError({'full_name': ['Muy corto', 'Muy largo']})
        monkeypatch.setattr(users_views, 'create_admin_user', boom)

        resp = admin_client.post(LIST_URL, data={
            'full_name': 'Edge Case',
            'email': 'edge@biomed.umss.bo',
            'role': 'analista',
            'password': STRONG_PW,
        }, format='json')
        assert resp.status_code == 400
        # El body es el dict del message_dict
        body = resp.json()
        assert 'full_name' in body

    def test_create_returns_409_on_email_duplicado_string(self, admin_client, monkeypatch):
        """Branch de 'Email ya registrado' string en views.py:76-78."""
        from apps.users import views as users_views

        original = users_views.create_admin_user
        def boom(**kwargs):
            raise Exception('Email ya registrado por error simulado')
        monkeypatch.setattr(users_views, 'create_admin_user', boom)

        resp = admin_client.post(LIST_URL, data={
            'full_name': 'Edge 409',
            'email': 'edge409@biomed.umss.bo',
            'role': 'analista',
            'password': STRONG_PW,
        }, format='json')
        assert resp.status_code == 409


class TestPartialUpdateErrorBranches:
    def test_partial_update_validation_error_400(self, admin_client, admin_user, monkeypatch):
        """Branch línea 95-97 views.py."""
        from apps.users import views as users_views

        def boom(*args, **kwargs):
            from django.core.exceptions import ValidationError
            raise ValidationError('Error de validación simulado')
        monkeypatch.setattr(users_views, 'update_admin_user', boom)

        resp = admin_client.patch(DETAIL_FMT.format(id=admin_user.pk), data={
            'full_name': 'Patch Edge',
        }, format='json')
        assert resp.status_code == 400


class TestDestroyErrorBranches:
    def test_destroy_validation_error_400(self, admin_client, supervisor_admin_user, monkeypatch):
        """Branch línea 114-118 views.py: ValidationError genérico (no 'ya está desactivado')."""
        from apps.users import views as users_views

        def boom(*args, **kwargs):
            from django.core.exceptions import ValidationError
            raise ValidationError('Error genérico de validación')
        monkeypatch.setattr(users_views, 'soft_delete_admin_user', boom)

        resp = admin_client.delete(DETAIL_FMT.format(id=supervisor_admin_user.pk))
        assert resp.status_code == 400
