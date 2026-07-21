"""
Tests unitarios de apps/users/auth_serializers.py (ADR-0017, ADR-0020).
"""
import pytest

from apps.users.auth_serializers import AdminTokenObtainPairSerializer, MeSerializer, _full_name_for
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


class TestAdminTokenObtainPairSerializerGetToken:
    """SSO (ADR-0020): el JWT firmado debe incluir email/role como claims
    propios del token (no solo en el body de la respuesta HTTP), para que
    backend-clinic los lea al validar con el secreto compartido."""

    def test_get_token_incluye_email_y_role_como_claims(self, db, django_user_model):
        user = django_user_model.objects.create_user(
            username='token@biomed.umss.bo', email='token@biomed.umss.bo',
            password='x', role='supervisor',
        )
        token = AdminTokenObtainPairSerializer.get_token(user)
        assert token['email'] == 'token@biomed.umss.bo'
        assert token['role'] == 'supervisor'

    def test_get_token_conserva_claims_default_de_simplejwt(self, db, django_user_model):
        user = django_user_model.objects.create_user(
            username='default@biomed.umss.bo', email='default@biomed.umss.bo',
            password='x', role='admin',
        )
        token = AdminTokenObtainPairSerializer.get_token(user)
        # get_token() de TokenObtainPairSerializer construye un RefreshToken
        # (token_type='refresh'); el access token se deriva de este en
        # validate() vía str(refresh.access_token) — ambos heredan los
        # claims custom porque access_token copia el payload del refresh.
        # Los claims default (token_type, exp, jti) no deben perderse por
        # el override — get_token() llama a super() antes de agregar los suyos.
        assert token['token_type'] == 'refresh'
        assert 'exp' in token
        assert 'jti' in token
        # Confirmar que el access token derivado también lleva los claims custom
        access = token.access_token
        assert access['email'] == 'default@biomed.umss.bo'
        assert access['role'] == 'admin'
        assert access['token_type'] == 'access'
