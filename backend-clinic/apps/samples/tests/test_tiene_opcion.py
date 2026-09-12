"""Tests de tiene_opcion() — el corazón del RBAC jerárquico (ADR-0019,
DD-RBAC-001 §4). Port literal de nodeValue() del módulo C# real
(Security/frmUsuariosEdit.cs).

Cubre la regla de resolución completa: excepción individual absoluta,
deny-overrides entre grupos múltiples, y fail-closed cuando falta seed.
"""
import pytest

from apps.samples.models_rbac import (
    Grupo,
    Objeto,
    Opcion,
    PrivilegioGrupo,
    PrivilegioIndividual,
    TipoObjeto,
    UsuarioGrupo,
)
from apps.samples.permissions import tiene_opcion

pytestmark = pytest.mark.django_db


@pytest.fixture
def opcion_test(db):
    """Una Opcion aislada para estos tests, para no depender del seed
    de producción (que ya corrió en las migraciones)."""
    tipo = TipoObjeto.objects.create(nombre='TipoTest')
    objeto = Objeto.objects.create(tipo=tipo, nombre='ObjetoTest')
    return Opcion.objects.create(objeto=objeto, codigo='test.accion', nombre='Acción de test')


@pytest.fixture
def usuario(db, django_user_model):
    return django_user_model.objects.create_user(username='rbac_user_1', password='x')


def _grupo(nombre):
    grupo, _ = Grupo.objects.get_or_create(nombre=nombre)
    return grupo


class TestFailClosed:
    def test_opcion_inexistente_fail_closed(self, usuario):
        assert tiene_opcion(usuario, 'codigo.que.no.existe') is False

    def test_sin_grupo_sin_privilegio(self, usuario, opcion_test):
        assert tiene_opcion(usuario, opcion_test.codigo) is False

    def test_grupo_asignado_sin_privilegio_definido_para_la_opcion(self, usuario, opcion_test):
        grupo = _grupo('GrupoSinPrivilegio')
        UsuarioGrupo.objects.create(usuario=usuario, grupo=grupo)
        # el grupo existe y el usuario pertenece a él, pero no hay PrivilegioGrupo
        # para esta Opcion -> el queryset de privilegios queda vacío -> False
        assert tiene_opcion(usuario, opcion_test.codigo) is False


class TestResolucionPorGrupo:
    def test_un_grupo_permite(self, usuario, opcion_test):
        grupo = _grupo('GrupoPermite')
        UsuarioGrupo.objects.create(usuario=usuario, grupo=grupo)
        PrivilegioGrupo.objects.create(grupo=grupo, opcion=opcion_test, permitido=True)
        assert tiene_opcion(usuario, opcion_test.codigo) is True

    def test_un_grupo_deniega(self, usuario, opcion_test):
        grupo = _grupo('GrupoDeniega')
        UsuarioGrupo.objects.create(usuario=usuario, grupo=grupo)
        PrivilegioGrupo.objects.create(grupo=grupo, opcion=opcion_test, permitido=False)
        assert tiene_opcion(usuario, opcion_test.codigo) is False

    def test_dos_grupos_ambos_permiten(self, usuario, opcion_test):
        g1 = _grupo('GrupoA')
        g2 = _grupo('GrupoB')
        UsuarioGrupo.objects.create(usuario=usuario, grupo=g1)
        UsuarioGrupo.objects.create(usuario=usuario, grupo=g2)
        PrivilegioGrupo.objects.create(grupo=g1, opcion=opcion_test, permitido=True)
        PrivilegioGrupo.objects.create(grupo=g2, opcion=opcion_test, permitido=True)
        assert tiene_opcion(usuario, opcion_test.codigo) is True

    def test_dos_grupos_uno_permite_uno_deniega_gana_denegacion(self, usuario, opcion_test):
        """Deny-overrides: basta que UN grupo deniegue para bloquear,
        aunque otro grupo del mismo usuario lo permita. Port literal de
        createArrayGrupos() del C# real (consulta con NOT IN)."""
        g_permite = _grupo('GrupoQuePermite')
        g_deniega = _grupo('GrupoQueDeniega')
        UsuarioGrupo.objects.create(usuario=usuario, grupo=g_permite)
        UsuarioGrupo.objects.create(usuario=usuario, grupo=g_deniega)
        PrivilegioGrupo.objects.create(grupo=g_permite, opcion=opcion_test, permitido=True)
        PrivilegioGrupo.objects.create(grupo=g_deniega, opcion=opcion_test, permitido=False)
        assert tiene_opcion(usuario, opcion_test.codigo) is False

    def test_usuario_en_multiples_grupos_admin_y_analista_gana_denegacion(self, usuario, opcion_test):
        """Caso concreto del dominio: un usuario que es Analista (sin
        acceso a una opción crítica) Y también Admin (con acceso) —
        el resultado es SIN acceso, porque deny-overrides no es
        'máximo privilegio'. Confirma que el modelo real NO es lo que
        el primer borrador de ADR-0019 asumía."""
        g_analista = _grupo('AnalistaTest')
        g_admin = _grupo('AdminTest')
        UsuarioGrupo.objects.create(usuario=usuario, grupo=g_analista)
        UsuarioGrupo.objects.create(usuario=usuario, grupo=g_admin)
        PrivilegioGrupo.objects.create(grupo=g_analista, opcion=opcion_test, permitido=False)
        PrivilegioGrupo.objects.create(grupo=g_admin, opcion=opcion_test, permitido=True)
        assert tiene_opcion(usuario, opcion_test.codigo) is False


class TestExcepcionIndividual:
    def test_excepcion_true_sobre_grupo_false(self, usuario, opcion_test):
        """La excepción individual gana SIEMPRE, incluso para dar
        acceso que el grupo niega."""
        grupo = _grupo('GrupoDeniegaExcepcion')
        UsuarioGrupo.objects.create(usuario=usuario, grupo=grupo)
        PrivilegioGrupo.objects.create(grupo=grupo, opcion=opcion_test, permitido=False)
        PrivilegioIndividual.objects.create(usuario=usuario, opcion=opcion_test, permitido=True)
        assert tiene_opcion(usuario, opcion_test.codigo) is True

    def test_excepcion_false_sobre_grupo_true(self, usuario, opcion_test):
        """La excepción individual gana SIEMPRE, incluso para quitar
        acceso que el grupo concede."""
        grupo = _grupo('GrupoPermiteExcepcion')
        UsuarioGrupo.objects.create(usuario=usuario, grupo=grupo)
        PrivilegioGrupo.objects.create(grupo=grupo, opcion=opcion_test, permitido=True)
        PrivilegioIndividual.objects.create(usuario=usuario, opcion=opcion_test, permitido=False)
        assert tiene_opcion(usuario, opcion_test.codigo) is False

    def test_excepcion_none_usa_grupo(self, usuario, opcion_test):
        """permitido=None explícito (el default del modelo) se
        comporta exactamente igual que "sin excepción" — usa el
        resultado combinado de grupos."""
        grupo = _grupo('GrupoConExcepcionNone')
        UsuarioGrupo.objects.create(usuario=usuario, grupo=grupo)
        PrivilegioGrupo.objects.create(grupo=grupo, opcion=opcion_test, permitido=True)
        PrivilegioIndividual.objects.create(usuario=usuario, opcion=opcion_test, permitido=None)
        assert tiene_opcion(usuario, opcion_test.codigo) is True

    def test_excepcion_sin_ningun_grupo(self, usuario, opcion_test):
        """La excepción individual gana incluso si el usuario no
        pertenece a ningún grupo — no depende de que exista un
        resultado de grupo previo."""
        PrivilegioIndividual.objects.create(usuario=usuario, opcion=opcion_test, permitido=True)
        assert tiene_opcion(usuario, opcion_test.codigo) is True
