"""Migración de datos — ADR-0023 D5, DD-SUP-002 §3.5.

Siembra la opción RBAC `case.sign` (firma MFA del Supervisor): Supervisor y
Admin SÍ, Analista NO (segregación RN-06). Idempotente + reverse simétrico.
"""
from django.db import migrations

OBJETO = 'Firma'
TIPO = 'Formulario'
OPCION = ('case.sign', 'Firmar el reporte con MFA (Supervisor)')
MATRIZ = {'Analista': False, 'Supervisor': True, 'Admin': True}


def seed_forward(apps, schema_editor):
    TipoObjeto = apps.get_model('samples', 'TipoObjeto')
    Objeto = apps.get_model('samples', 'Objeto')
    Opcion = apps.get_model('samples', 'Opcion')
    Grupo = apps.get_model('samples', 'Grupo')
    PrivilegioGrupo = apps.get_model('samples', 'PrivilegioGrupo')

    tipo, _ = TipoObjeto.objects.get_or_create(nombre=TIPO)
    objeto, _ = Objeto.objects.get_or_create(tipo=tipo, nombre=OBJETO)
    codigo, nombre = OPCION
    opcion, _ = Opcion.objects.get_or_create(objeto=objeto, codigo=codigo, defaults={'nombre': nombre})

    grupos = {g.nombre: g for g in Grupo.objects.all()}
    for grupo_nombre, permitido in MATRIZ.items():
        grupo = grupos.get(grupo_nombre)
        if grupo is None:
            continue
        PrivilegioGrupo.objects.get_or_create(grupo=grupo, opcion=opcion, defaults={'permitido': permitido})


def seed_reverse(apps, schema_editor):
    Opcion = apps.get_model('samples', 'Opcion')
    Objeto = apps.get_model('samples', 'Objeto')
    PrivilegioGrupo = apps.get_model('samples', 'PrivilegioGrupo')

    codigo, _ = OPCION
    for opcion in Opcion.objects.filter(codigo=codigo):
        PrivilegioGrupo.objects.filter(opcion=opcion).delete()
        opcion.delete()
    Objeto.objects.filter(nombre=OBJETO).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('samples', '0011_sample_signed_at_sample_signed_by_signlockout'),
    ]

    operations = [
        migrations.RunPython(seed_forward, seed_reverse),
    ]
