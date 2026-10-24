"""Tests de los modelos RBAC y del seed de la migración 0004 (ADR-0019,
DD-RBAC-001 §5). Verifica que el seed reproduce exactamente ADR-0018 —
regla de oro: ningún usuario existente pierde ni gana acceso el día 1.
"""
import pytest
from django.db import IntegrityError

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


class TestSeedJerarquia:
    """El seed corre en la migración 0004 (aplicada globalmente por
    pytest-django antes de cualquier test), así que estos tests
    verifican el estado post-seed, no ejecutan el seed ellos mismos."""

    def test_seed_crea_las_6_opciones_esperadas(self):
        codigos = set(Opcion.objects.values_list('codigo', flat=True))
        esperados = {
            'sample.create', 'sample.list', 'sample.view',
            'sample.edit', 'sample.delete', 'sample.process',
        }
        assert esperados.issubset(codigos)

    def test_seed_crea_los_3_grupos_esperados(self):
        nombres = set(Grupo.objects.values_list('nombre', flat=True))
        assert {'Analista', 'Supervisor', 'Admin'}.issubset(nombres)

    def test_seed_matriz_reproduce_adr0018(self):
        """sample.delete solo permitido para Admin — el resto de
        opciones permitidas para los 3 grupos, igual que ADR-0018 D3."""
        delete = Opcion.objects.get(codigo='sample.delete')
        permisos = {
            pg.grupo.nombre: pg.permitido
            for pg in PrivilegioGrupo.objects.filter(opcion=delete).select_related('grupo')
        }
        assert permisos == {'Analista': False, 'Supervisor': False, 'Admin': True}

    def test_seed_resto_de_opciones_permitidas_para_los_3_grupos(self):
        for codigo in ('sample.create', 'sample.list', 'sample.view', 'sample.edit', 'sample.process'):
            opcion = Opcion.objects.get(codigo=codigo)
            permisos = list(PrivilegioGrupo.objects.filter(opcion=opcion).values_list('permitido', flat=True))
            assert all(permisos), f'{codigo} debería estar permitido para los 3 grupos'
            assert len(permisos) == 3


class TestSeedUsuariosExistentes:
    """Los usuarios creados en tests via conftest.py (analyst_user,
    supervisor_user, admin_user) se crean DESPUÉS de la migración de
    seed — por eso su asignación de grupo viene del signal
    (asignar_grupo_analista_por_defecto), no del seed de migración.
    Ver DD-RBAC-001 §5.4."""

    def test_signal_asigna_analista_a_usuario_nuevo_sin_staff(self, django_user_model):
        user = django_user_model.objects.create_user(username='nuevo_sin_staff', password='x')
        grupos = set(UsuarioGrupo.objects.filter(usuario=user).values_list('grupo__nombre', flat=True))
        assert grupos == {'Analista'}

    def test_signal_no_reasigna_si_ya_tiene_grupo(self, django_user_model):
        """Un admin puede reasignar manualmente el grupo de un usuario
        después de creado; el signal no debe pisar esa reasignación en
        saves posteriores (solo actúa en created=True)."""
        user = django_user_model.objects.create_user(username='reasignado', password='x')
        UsuarioGrupo.objects.filter(usuario=user).delete()
        grupo_admin, _ = Grupo.objects.get_or_create(nombre='Admin')
        UsuarioGrupo.objects.create(usuario=user, grupo=grupo_admin)

        user.first_name = 'Actualizado'
        user.save()  # created=False en este segundo save

        grupos = set(UsuarioGrupo.objects.filter(usuario=user).values_list('grupo__nombre', flat=True))
        assert grupos == {'Admin'}


class TestConstraints:
    def test_unique_objeto_opcion_nombre(self):
        tipo = TipoObjeto.objects.create(nombre='T1')
        objeto = Objeto.objects.create(tipo=tipo, nombre='O1')
        Opcion.objects.create(objeto=objeto, codigo='c1', nombre='dup')
        with pytest.raises(IntegrityError):
            Opcion.objects.create(objeto=objeto, codigo='c2', nombre='dup')

    def test_unique_opcion_codigo(self):
        tipo = TipoObjeto.objects.create(nombre='T2')
        objeto = Objeto.objects.create(tipo=tipo, nombre='O2')
        Opcion.objects.create(objeto=objeto, codigo='codigo_unico', nombre='n1')
        with pytest.raises(IntegrityError):
            Opcion.objects.create(objeto=objeto, codigo='codigo_unico', nombre='n2')

    def test_unique_grupo_opcion(self):
        tipo = TipoObjeto.objects.create(nombre='T3')
        objeto = Objeto.objects.create(tipo=tipo, nombre='O3')
        opcion = Opcion.objects.create(objeto=objeto, codigo='c3', nombre='n3')
        grupo = Grupo.objects.create(nombre='GrupoUnico')
        PrivilegioGrupo.objects.create(grupo=grupo, opcion=opcion, permitido=True)
        with pytest.raises(IntegrityError):
            PrivilegioGrupo.objects.create(grupo=grupo, opcion=opcion, permitido=False)

    def test_unique_usuario_grupo(self, django_user_model):
        user = django_user_model.objects.create_user(username='dup_grupo_user', password='x')
        grupo = Grupo.objects.create(nombre='GrupoDupTest')
        UsuarioGrupo.objects.create(usuario=user, grupo=grupo)
        with pytest.raises(IntegrityError):
            UsuarioGrupo.objects.create(usuario=user, grupo=grupo)

    def test_unique_usuario_opcion_individual(self, django_user_model):
        tipo = TipoObjeto.objects.create(nombre='T4')
        objeto = Objeto.objects.create(tipo=tipo, nombre='O4')
        opcion = Opcion.objects.create(objeto=objeto, codigo='c4', nombre='n4')
        user = django_user_model.objects.create_user(username='dup_individual_user', password='x')
        PrivilegioIndividual.objects.create(usuario=user, opcion=opcion, permitido=True)
        with pytest.raises(IntegrityError):
            PrivilegioIndividual.objects.create(usuario=user, opcion=opcion, permitido=False)


class TestStrRepresentations:
    """Cobertura de los __str__ (triviales pero cuentan para RN-09)."""

    def test_tipo_objeto_str(self):
        assert str(TipoObjeto.objects.create(nombre='X')) == 'X'

    def test_objeto_str(self):
        tipo = TipoObjeto.objects.create(nombre='T')
        assert str(Objeto.objects.create(tipo=tipo, nombre='Y')) == 'Y'

    def test_opcion_str(self):
        tipo = TipoObjeto.objects.create(nombre='T')
        objeto = Objeto.objects.create(tipo=tipo, nombre='O')
        opcion = Opcion.objects.create(objeto=objeto, codigo='cod.x', nombre='Nombre X')
        assert 'cod.x' in str(opcion)

    def test_grupo_str(self):
        assert str(Grupo.objects.create(nombre='G')) == 'G'

    def test_privilegio_grupo_str(self):
        tipo = TipoObjeto.objects.create(nombre='T')
        objeto = Objeto.objects.create(tipo=tipo, nombre='O')
        opcion = Opcion.objects.create(objeto=objeto, codigo='cod.y', nombre='n')
        grupo = Grupo.objects.create(nombre='G2')
        pg = PrivilegioGrupo.objects.create(grupo=grupo, opcion=opcion, permitido=True)
        assert 'cod.y' in str(pg)

    def test_usuario_grupo_str(self, django_user_model):
        user = django_user_model.objects.create_user(username='str_test_user', password='x')
        grupo = Grupo.objects.create(nombre='G3')
        ug = UsuarioGrupo.objects.filter(usuario=user).first() or UsuarioGrupo.objects.create(usuario=user, grupo=grupo)
        assert str(user) in str(ug) or 'str_test_user' in str(ug)

    def test_privilegio_individual_str(self, django_user_model):
        tipo = TipoObjeto.objects.create(nombre='T')
        objeto = Objeto.objects.create(tipo=tipo, nombre='O')
        opcion = Opcion.objects.create(objeto=objeto, codigo='cod.z', nombre='n')
        user = django_user_model.objects.create_user(username='str_individual_user', password='x')
        pi = PrivilegioIndividual.objects.create(usuario=user, opcion=opcion, permitido=True)
        assert 'cod.z' in str(pi)
