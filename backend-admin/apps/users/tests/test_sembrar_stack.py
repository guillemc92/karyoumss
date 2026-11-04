"""DD-OPS-001 D6: los usuarios de la demo se crean una vez y pueden entrar."""
import pytest
from django.core.management import CommandError, call_command

from apps.users.models import AdminUser, User
from apps.users.management.commands.sembrar_stack import USUARIOS

CLAVES = {variable: f'Demo-{rol}-2026X' for rol, _, _, variable in USUARIOS}


@pytest.fixture
def claves(monkeypatch):
    for variable, clave in CLAVES.items():
        monkeypatch.setenv(variable, clave)


@pytest.mark.django_db
def test_crea_un_usuario_por_rol_que_puede_entrar(claves):
    call_command('sembrar_stack')
    for rol, email, _, variable in USUARIOS:
        cuenta = AdminUser.objects.get(email=email)
        assert cuenta.role == rol
        assert cuenta.user.check_password(CLAVES[variable])
        assert cuenta.user.is_staff == (rol == 'admin')


@pytest.mark.django_db
def test_una_segunda_corrida_no_cambia_nada(claves, monkeypatch):
    call_command('sembrar_stack')
    monkeypatch.setenv('DEMO_PASSWORD_ANALISTA', 'Otra-clave-2026X')
    call_command('sembrar_stack')
    assert AdminUser.objects.count() == 3
    assert User.objects.get(email='analista@biomed.local').check_password(
        CLAVES['DEMO_PASSWORD_ANALISTA'])


@pytest.mark.django_db
def test_sin_la_contrasena_falla_con_un_mensaje_claro(claves, monkeypatch):
    monkeypatch.delenv('DEMO_PASSWORD_SUPERVISOR')
    monkeypatch.delenv('BIOMED_SECRETS_DIR', raising=False)
    with pytest.raises(CommandError, match='DEMO_PASSWORD_SUPERVISOR'):
        call_command('sembrar_stack')
