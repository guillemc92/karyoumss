"""Crea los usuarios de la demo del stack de producción (DD-OPS-001 D6).

    python manage.py sembrar_stack

Un usuario por rol. La contraseña de cada uno sale de su variable, o del archivo
del mismo nombre en BIOMED_SECRETS_DIR, que el job `secretos` del compose
genera al primer arranque. Si el usuario ya existe, no se toca: correrlo en
cada `up` es seguro.
"""
from django.core.management.base import BaseCommand, CommandError

from admin_backend.entorno import env
from apps.users.models import AdminUser
from apps.users.services import create_admin_user

USUARIOS = [
    ('admin', 'admin@biomed.local', 'Administración Demo', 'DEMO_PASSWORD_ADMIN'),
    ('analista', 'analista@biomed.local', 'Analista Demo', 'DEMO_PASSWORD_ANALISTA'),
    ('supervisor', 'supervisor@biomed.local', 'Supervisión Demo', 'DEMO_PASSWORD_SUPERVISOR'),
]


class Command(BaseCommand):
    help = 'Crea los usuarios de la demo (uno por rol) si no existen.'

    def handle(self, *args, **options):
        for rol, email, nombre, variable in USUARIOS:
            if AdminUser.objects.filter(email=email).exists():
                self.stdout.write(f'{email}: ya existe, no se toca')
                continue
            clave = env(variable)
            if not clave:
                raise CommandError(f'Falta la contraseña de {email}: defina {variable} '
                                   'o genérela con el job secretos del compose.')
            create_admin_user(full_name=nombre, email=email, role=rol, password=clave)
            self.stdout.write(f'{email}: creado con el rol {rol}')
