"""Tests de SharedJWTAuthentication (SSO, ADR-0020, DD-SSO-001 §6.2).

Cubre: token sin claim email (rechazo), creación/reutilización de
usuario local, sincronización de is_staff/is_superuser a partir del
claim role, y que tiene_opcion() (ADR-0019) sigue funcionando sobre el
User sincronizado sin ningún cambio de su propia lógica.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.samples.auth_bridge import SharedJWTAuthentication
from apps.samples.models_rbac import Grupo, Opcion, PrivilegioGrupo, TipoObjeto, Objeto, UsuarioGrupo
from apps.samples.permissions import tiene_opcion

pytestmark = pytest.mark.django_db

User = get_user_model()


def _token_for(username='nuevo@biomed.umss.bo', role='analista', include_email=True):
    """Genera un RefreshToken 'crudo' (no pasa por get_user_model de este
    proyecto — simula el token que backend-admin firmaría). No usa
    RefreshToken.for_user() con un User existente de backend-clinic
    porque el punto de este test es que el usuario AÚN NO EXISTE acá."""
    dummy_user = User(pk=999999, username='dummy-for-signing')
    dummy_user.pk = None  # RefreshToken.for_user requiere un pk, pero no lo persiste
    token = RefreshToken()
    if include_email:
        token['email'] = username
    token['role'] = role
    return token


class TestGetUser:
    def test_token_sin_email_claim_rechazado(self):
        auth = SharedJWTAuthentication()
        token = _token_for(include_email=False)
        with pytest.raises(Exception) as exc_info:
            auth.get_user(token)
        assert 'email' in str(exc_info.value).lower()

    def test_usuario_nuevo_se_crea_automaticamente(self):
        assert not User.objects.filter(username='nuevo.usuario@biomed.umss.bo').exists()
        auth = SharedJWTAuthentication()
        token = _token_for(username='nuevo.usuario@biomed.umss.bo', role='analista')
        user = auth.get_user(token)
        assert user.username == 'nuevo.usuario@biomed.umss.bo'
        assert User.objects.filter(username='nuevo.usuario@biomed.umss.bo').count() == 1

    def test_usuario_existente_se_reutiliza_no_duplica(self):
        existente = User.objects.create_user(username='ya.existe@biomed.umss.bo', password='x')
        auth = SharedJWTAuthentication()
        token = _token_for(username='ya.existe@biomed.umss.bo', role='analista')
        user = auth.get_user(token)
        assert user.pk == existente.pk
        assert User.objects.filter(username='ya.existe@biomed.umss.bo').count() == 1

    def test_sincroniza_is_staff_is_superuser_admin(self):
        auth = SharedJWTAuthentication()
        token = _token_for(username='rol.admin@biomed.umss.bo', role='admin')
        user = auth.get_user(token)
        assert user.is_staff is True
        assert user.is_superuser is True

    def test_sincroniza_is_staff_supervisor_sin_superuser(self):
        auth = SharedJWTAuthentication()
        token = _token_for(username='rol.supervisor@biomed.umss.bo', role='supervisor')
        user = auth.get_user(token)
        assert user.is_staff is True
        assert user.is_superuser is False

    def test_sincroniza_analista_sin_staff_ni_superuser(self):
        auth = SharedJWTAuthentication()
        token = _token_for(username='rol.analista@biomed.umss.bo', role='analista')
        user = auth.get_user(token)
        assert user.is_staff is False
        assert user.is_superuser is False

    def test_cambio_de_role_se_refleja_en_siguiente_request_sin_recrear_usuario(self):
        auth = SharedJWTAuthentication()
        token1 = _token_for(username='cambia.rol@biomed.umss.bo', role='analista')
        user1 = auth.get_user(token1)
        assert user1.is_staff is False

        token2 = _token_for(username='cambia.rol@biomed.umss.bo', role='admin')
        user2 = auth.get_user(token2)

        assert user2.pk == user1.pk  # misma fila, no se duplicó
        user1.refresh_from_db()
        assert user1.is_staff is True
        assert user1.is_superuser is True


class TestEndpointsLoginClinicEliminados:
    def test_login_clinic_ya_no_existe(self):
        client = APIClient()
        resp = client.post('/api/clinic/auth/login/', {'username': 'x', 'password': 'y'})
        assert resp.status_code == 404

    def test_refresh_clinic_ya_no_existe(self):
        client = APIClient()
        resp = client.post('/api/clinic/auth/refresh/', {'refresh': 'x'})
        assert resp.status_code == 404


class TestIntegracionConRBAC:
    """Confirma que tiene_opcion() (ADR-0019) sigue funcionando igual
    sobre un User sincronizado por SharedJWTAuthentication — el RBAC no
    se toca, pero su fuente de Usuario cambió, hay que confirmar que
    la integración sigue siendo correcta end-to-end."""

    def test_tiene_opcion_funciona_sobre_usuario_sincronizado_por_sso(self):
        tipo = TipoObjeto.objects.create(nombre='TipoSSOTest')
        objeto = Objeto.objects.create(tipo=tipo, nombre='ObjetoSSOTest')
        opcion = Opcion.objects.create(objeto=objeto, codigo='sso.test.accion', nombre='Accion SSO test')

        auth = SharedJWTAuthentication()
        token = _token_for(username='sso.rbac@biomed.umss.bo', role='analista')
        user = auth.get_user(token)

        grupo = Grupo.objects.create(nombre='GrupoSSOTest')
        UsuarioGrupo.objects.filter(usuario=user).delete()
        UsuarioGrupo.objects.create(usuario=user, grupo=grupo)
        PrivilegioGrupo.objects.create(grupo=grupo, opcion=opcion, permitido=True)

        assert tiene_opcion(user, 'sso.test.accion') is True
