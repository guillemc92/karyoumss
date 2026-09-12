"""Tests del Django Admin del RBAC (ADR-0019, DD-RBAC-001 §6).

Cubre los métodos calculados (list_display) de cada ModelAdmin, en
particular el resaltado de PrivilegioIndividualAdmin.efecto_real, que
es la pieza de robustez operativa pedida explícitamente ("de aquí
empieza la navegación para todo el sistema").
"""
import pytest
from django.contrib.admin.sites import AdminSite

from apps.samples.admin import (
    GrupoAdmin,
    ObjetoAdmin,
    PrivilegioGrupoAdmin,
    PrivilegioIndividualAdmin,
    TipoObjetoAdmin,
)
from apps.samples.models_rbac import (
    Grupo,
    Objeto,
    Opcion,
    PrivilegioGrupo,
    PrivilegioIndividual,
    TipoObjeto,
    UsuarioGrupo,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def site():
    return AdminSite()


@pytest.fixture
def opcion(db):
    tipo = TipoObjeto.objects.create(nombre='TipoAdmin')
    objeto = Objeto.objects.create(tipo=tipo, nombre='ObjetoAdmin')
    return Opcion.objects.create(objeto=objeto, codigo='admin.test', nombre='Test Admin')


class TestTipoObjetoAdmin:
    def test_objetos_count(self, site):
        tipo = TipoObjeto.objects.create(nombre='ConObjetos')
        Objeto.objects.create(tipo=tipo, nombre='O1')
        Objeto.objects.create(tipo=tipo, nombre='O2')
        admin_instance = TipoObjetoAdmin(TipoObjeto, site)
        assert admin_instance.objetos_count(tipo) == 2


class TestObjetoAdmin:
    def test_opciones_count(self, site, opcion):
        admin_instance = ObjetoAdmin(Objeto, site)
        assert admin_instance.opciones_count(opcion.objeto) == 1


class TestGrupoAdmin:
    def test_usuarios_count(self, site, django_user_model):
        grupo = Grupo.objects.create(nombre='GrupoConUsuarios')
        user = django_user_model.objects.create_user(username='admin_test_1', password='x')
        UsuarioGrupo.objects.filter(usuario=user).delete()
        UsuarioGrupo.objects.create(usuario=user, grupo=grupo)
        admin_instance = GrupoAdmin(Grupo, site)
        assert admin_instance.usuarios_count(grupo) == 1

    def test_privilegios_count_solo_cuenta_permitidos(self, site, opcion):
        grupo = Grupo.objects.create(nombre='GrupoConPrivilegios')
        PrivilegioGrupo.objects.create(grupo=grupo, opcion=opcion, permitido=True)
        admin_instance = GrupoAdmin(Grupo, site)
        assert admin_instance.privilegios_count(grupo) == 1


class TestPrivilegioGrupoAdmin:
    def test_permitido_badge_si(self, site, opcion):
        grupo = Grupo.objects.create(nombre='GrupoBadgeSi')
        pg = PrivilegioGrupo.objects.create(grupo=grupo, opcion=opcion, permitido=True)
        admin_instance = PrivilegioGrupoAdmin(PrivilegioGrupo, site)
        html = admin_instance.permitido_badge(pg)
        assert 'green' in html
        assert 'SI' in html

    def test_permitido_badge_no(self, site, opcion):
        grupo = Grupo.objects.create(nombre='GrupoBadgeNo')
        pg = PrivilegioGrupo.objects.create(grupo=grupo, opcion=opcion, permitido=False)
        admin_instance = PrivilegioGrupoAdmin(PrivilegioGrupo, site)
        html = admin_instance.permitido_badge(pg)
        assert 'red' in html
        assert 'NO' in html


class TestPrivilegioIndividualAdmin:
    def test_permitido_display_sin_excepcion(self, site, opcion, django_user_model):
        user = django_user_model.objects.create_user(username='admin_test_2', password='x')
        pi = PrivilegioIndividual.objects.create(usuario=user, opcion=opcion, permitido=None)
        admin_instance = PrivilegioIndividualAdmin(PrivilegioIndividual, site)
        assert admin_instance.permitido_display(pi) == 'Sin excepción'

    def test_permitido_display_forzado_si(self, site, opcion, django_user_model):
        user = django_user_model.objects.create_user(username='admin_test_3', password='x')
        pi = PrivilegioIndividual.objects.create(usuario=user, opcion=opcion, permitido=True)
        admin_instance = PrivilegioIndividualAdmin(PrivilegioIndividual, site)
        assert 'SI' in admin_instance.permitido_display(pi)

    def test_permitido_display_forzado_no(self, site, opcion, django_user_model):
        user = django_user_model.objects.create_user(username='admin_test_4', password='x')
        pi = PrivilegioIndividual.objects.create(usuario=user, opcion=opcion, permitido=False)
        admin_instance = PrivilegioIndividualAdmin(PrivilegioIndividual, site)
        assert 'NO' in admin_instance.permitido_display(pi)

    def test_efecto_real_sin_excepcion_usa_grupo(self, site, opcion, django_user_model):
        user = django_user_model.objects.create_user(username='admin_test_5', password='x')
        pi = PrivilegioIndividual.objects.create(usuario=user, opcion=opcion, permitido=None)
        admin_instance = PrivilegioIndividualAdmin(PrivilegioIndividual, site)
        html = admin_instance.efecto_real(pi)
        assert 'usa grupo' in html

    def test_efecto_real_difiere_del_grupo_resalta_rojo(self, site, opcion, django_user_model):
        """El caso clave de robustez operativa: un admin ve en rojo
        cuando la excepción individual contradice lo que el grupo del
        usuario indicaría."""
        user = django_user_model.objects.create_user(username='admin_test_6', password='x')
        grupo = Grupo.objects.create(nombre='GrupoQueDeniegaParaEfectoReal')
        UsuarioGrupo.objects.filter(usuario=user).delete()
        UsuarioGrupo.objects.create(usuario=user, grupo=grupo)
        PrivilegioGrupo.objects.create(grupo=grupo, opcion=opcion, permitido=False)
        pi = PrivilegioIndividual.objects.create(usuario=user, opcion=opcion, permitido=True)

        admin_instance = PrivilegioIndividualAdmin(PrivilegioIndividual, site)
        html = admin_instance.efecto_real(pi)
        assert 'DIFIERE' in html
        assert 'color: red' in html

    def test_efecto_real_coincide_con_grupo_resalta_azul(self, site, opcion, django_user_model):
        user = django_user_model.objects.create_user(username='admin_test_7', password='x')
        grupo = Grupo.objects.create(nombre='GrupoQuePermiteParaEfectoReal')
        UsuarioGrupo.objects.filter(usuario=user).delete()
        UsuarioGrupo.objects.create(usuario=user, grupo=grupo)
        PrivilegioGrupo.objects.create(grupo=grupo, opcion=opcion, permitido=True)
        pi = PrivilegioIndividual.objects.create(usuario=user, opcion=opcion, permitido=True)

        admin_instance = PrivilegioIndividualAdmin(PrivilegioIndividual, site)
        html = admin_instance.efecto_real(pi)
        assert 'coincide' in html
        assert 'color: blue' in html
