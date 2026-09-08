"""Migración de datos (no de schema) — ADR-0019 D7, DD-RBAC-001 §5.

Regla de oro: el día del despliegue, ningún usuario existente pierde
ni gana acceso respecto al comportamiento actual de ADR-0018. Se
siembran 3 cosas:

1. La jerarquía TipoObjeto→Objeto→Opción (§5.1).
2. Los 3 Grupo (Analista/Supervisor/Admin) + UsuarioGrupo derivado de
   is_staff/is_superuser, replicando ADR-0018 exactamente (§5.2).
3. La matriz PrivilegioGrupo idéntica a ADR-0018 D3 / SPEC-008 §6 (§5.3).

reverse_code hace el rollback simétrico (borra lo sembrado por code),
requerido porque esta es una migración de datos real, no solo de
schema — sin reverse_code, un `migrate samples 0003` fallaría.
"""
from django.conf import settings
from django.db import migrations

JERARQUIA = {
    'Formulario': {
        'Muestras': [
            ('sample.create', 'Crear muestra'),
            ('sample.list', 'Listar muestras'),
            ('sample.view', 'Ver detalle de muestra'),
            ('sample.edit', 'Editar muestra'),
            ('sample.delete', 'Eliminar muestra (soft-delete)'),
            ('sample.process', 'Disparar procesamiento IA'),
        ],
    },
}

# Matriz idéntica a ADR-0018 D3 / SPEC-008 §6 — NO tocar sin ADR nuevo.
MATRIZ_PRIVILEGIOS = {
    'sample.create': {'Analista': True, 'Supervisor': True, 'Admin': True},
    'sample.list': {'Analista': True, 'Supervisor': True, 'Admin': True},
    'sample.view': {'Analista': True, 'Supervisor': True, 'Admin': True},
    'sample.edit': {'Analista': True, 'Supervisor': True, 'Admin': True},
    'sample.delete': {'Analista': False, 'Supervisor': False, 'Admin': True},
    'sample.process': {'Analista': True, 'Supervisor': True, 'Admin': True},
}


def seed_jerarquia_opciones(apps, schema_editor):
    TipoObjeto = apps.get_model('samples', 'TipoObjeto')
    Objeto = apps.get_model('samples', 'Objeto')
    Opcion = apps.get_model('samples', 'Opcion')

    for tipo_nombre, objetos in JERARQUIA.items():
        tipo, _ = TipoObjeto.objects.get_or_create(nombre=tipo_nombre)
        for objeto_nombre, opciones in objetos.items():
            objeto, _ = Objeto.objects.get_or_create(tipo=tipo, nombre=objeto_nombre)
            for codigo, nombre in opciones:
                Opcion.objects.get_or_create(
                    objeto=objeto, codigo=codigo, defaults={'nombre': nombre},
                )


def seed_grupos_y_usuarios(apps, schema_editor):
    User = apps.get_model(settings.AUTH_USER_MODEL)
    Grupo = apps.get_model('samples', 'Grupo')
    UsuarioGrupo = apps.get_model('samples', 'UsuarioGrupo')

    g_analista, _ = Grupo.objects.get_or_create(nombre='Analista')
    g_supervisor, _ = Grupo.objects.get_or_create(nombre='Supervisor')
    g_admin, _ = Grupo.objects.get_or_create(nombre='Admin')

    for user in User.objects.all():
        if user.is_superuser:
            grupo = g_admin
        elif user.is_staff:
            grupo = g_supervisor
        else:
            grupo = g_analista
        UsuarioGrupo.objects.get_or_create(usuario=user, grupo=grupo)


def seed_privilegios_grupo(apps, schema_editor):
    Grupo = apps.get_model('samples', 'Grupo')
    Opcion = apps.get_model('samples', 'Opcion')
    PrivilegioGrupo = apps.get_model('samples', 'PrivilegioGrupo')

    grupos = {g.nombre: g for g in Grupo.objects.all()}
    for codigo, permisos_por_grupo in MATRIZ_PRIVILEGIOS.items():
        opcion = Opcion.objects.get(codigo=codigo)
        for grupo_nombre, permitido in permisos_por_grupo.items():
            PrivilegioGrupo.objects.get_or_create(
                grupo=grupos[grupo_nombre], opcion=opcion, defaults={'permitido': permitido},
            )


def seed_forward(apps, schema_editor):
    seed_jerarquia_opciones(apps, schema_editor)
    seed_grupos_y_usuarios(apps, schema_editor)
    seed_privilegios_grupo(apps, schema_editor)


def seed_reverse(apps, schema_editor):
    PrivilegioGrupo = apps.get_model('samples', 'PrivilegioGrupo')
    UsuarioGrupo = apps.get_model('samples', 'UsuarioGrupo')
    Grupo = apps.get_model('samples', 'Grupo')
    Opcion = apps.get_model('samples', 'Opcion')
    Objeto = apps.get_model('samples', 'Objeto')
    TipoObjeto = apps.get_model('samples', 'TipoObjeto')

    PrivilegioGrupo.objects.all().delete()
    UsuarioGrupo.objects.all().delete()
    Grupo.objects.filter(nombre__in=['Analista', 'Supervisor', 'Admin']).delete()
    Opcion.objects.filter(codigo__in=MATRIZ_PRIVILEGIOS.keys()).delete()
    Objeto.objects.filter(nombre='Muestras').delete()
    TipoObjeto.objects.filter(nombre='Formulario').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('samples', '0003_rbac_jerarquico'),
    ]

    operations = [
        migrations.RunPython(seed_forward, seed_reverse),
    ]
