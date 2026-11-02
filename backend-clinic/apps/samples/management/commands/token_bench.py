"""Token del usuario del banco para k6 (DD-E3-001 D7).

    python manage.py token_bench --salida /k6data/token.txt

Firma un JWT de acceso, igual que lo haría backend-admin (ADR-0020), con el
`AUTH_ADMIN_JWT_SECRET` de ESTE entorno. En el banco, ese secreto lo genera
`bench/e3/correr.sh` al azar en cada corrida y desaparece con `down -v`. Por eso
el token no sirve fuera del banco y no queda ningún secreto en el repo.
"""
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from rest_framework_simplejwt.tokens import AccessToken

from .sembrar_bench import USUARIO_BENCH


class Command(BaseCommand):
    help = 'JWT del usuario del banco E3, firmado con el secreto del entorno.'

    def add_arguments(self, parser):
        parser.add_argument('--salida', type=Path, required=True)

    def handle(self, *args, salida, **opts):
        usuario = get_user_model().objects.get(username=USUARIO_BENCH)
        token = AccessToken.for_user(usuario)
        token['email'] = USUARIO_BENCH
        token['role'] = 'analista'
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_text(str(token), encoding='utf-8')
        self.stdout.write(f'token del banco en {salida}')
