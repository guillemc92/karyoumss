"""DD-OPS-001 D3: los secretos del stack se generan una vez, iguales donde se comparten."""
import base64
import functools
import importlib.util
import re
from pathlib import Path

import pytest

_RUTA = Path(__file__).resolve().parents[3] / 'scripts' / 'generar_secretos.py'
_spec = importlib.util.spec_from_file_location('generar_secretos', _RUTA)
gs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gs)


def _leer(raiz, carpeta, nombre):
    return (raiz / carpeta / nombre).read_text(encoding='utf-8')


def test_crea_cada_secreto_de_cada_carpeta(tmp_path):
    creados = gs.generar(tmp_path, cambiar_dueno=False)
    esperados = {f'{c}/{n}' for c, (_, s) in gs.CARPETAS.items() for n in s}
    assert set(creados) == esperados
    for nombre in esperados:
        assert (tmp_path / nombre).read_text(encoding='utf-8')


def test_los_compartidos_valen_lo_mismo_en_cada_servicio(tmp_path):
    gs.generar(tmp_path, cambiar_dueno=False)
    assert _leer(tmp_path, 'clinic', 'AUTH_ADMIN_JWT_SECRET') == _leer(tmp_path, 'admin', 'AUTH_ADMIN_JWT_SECRET')
    assert _leer(tmp_path, 'clinic', 'INTERNAL_SERVICE_SECRET') == _leer(tmp_path, 'admin', 'INTERNAL_SERVICE_SECRET')
    assert _leer(tmp_path, 'admin', 'POSTGRES_PASSWORD') == _leer(tmp_path, 'postgres', 'ADMIN_DB_PASSWORD')


def test_los_propios_de_cada_servicio_son_distintos(tmp_path):
    gs.generar(tmp_path, cambiar_dueno=False)
    assert _leer(tmp_path, 'clinic', 'DJANGO_SECRET_KEY') != _leer(tmp_path, 'admin', 'DJANGO_SECRET_KEY')
    assert _leer(tmp_path, 'postgres', 'POSTGRES_PASSWORD') != _leer(tmp_path, 'postgres', 'ADMIN_DB_PASSWORD')


def test_una_segunda_corrida_no_cambia_nada(tmp_path):
    gs.generar(tmp_path, cambiar_dueno=False)
    antes = {p: p.read_text(encoding='utf-8') for p in tmp_path.rglob('*') if p.is_file()}
    assert gs.generar(tmp_path, cambiar_dueno=False) == []
    assert {p: p.read_text(encoding='utf-8') for p in tmp_path.rglob('*') if p.is_file()} == antes


def test_si_falta_uno_solo_se_crea_ese(tmp_path):
    gs.generar(tmp_path, cambiar_dueno=False)
    jwt = _leer(tmp_path, 'admin', 'AUTH_ADMIN_JWT_SECRET')
    (tmp_path / 'clinic' / 'AUTH_ADMIN_JWT_SECRET').unlink()
    assert gs.generar(tmp_path, cambiar_dueno=False) == ['clinic/AUTH_ADMIN_JWT_SECRET']
    assert _leer(tmp_path, 'clinic', 'AUTH_ADMIN_JWT_SECRET') == jwt


def test_las_claves_fernet_son_32_bytes(tmp_path):
    gs.generar(tmp_path, cambiar_dueno=False)
    for carpeta, nombre in [('clinic', 'PATIENT_VAULT_KEY'), ('admin', 'TOTP_VAULT_KEY')]:
        assert len(base64.urlsafe_b64decode(_leer(tmp_path, carpeta, nombre))) == 32


def test_las_claves_de_la_demo_cumplen_la_politica_de_admin(tmp_path):
    gs.generar(tmp_path, cambiar_dueno=False)
    for nombre in ('DEMO_PASSWORD_ADMIN', 'DEMO_PASSWORD_ANALISTA', 'DEMO_PASSWORD_SUPERVISOR'):
        clave = _leer(tmp_path, 'admin', nombre)
        assert len(clave) >= 12 and re.search('[A-Z]', clave) and re.search('[0-9]', clave)


def test_main_nombra_los_secretos_pero_nunca_imprime_un_valor(tmp_path, capsys, monkeypatch):
    # En Windows no hay chown: se prueba sin cambiar el dueño.
    monkeypatch.setattr(gs, 'generar', functools.partial(gs.generar, cambiar_dueno=False))
    assert gs.main(['x', str(tmp_path)]) == 0
    salida = capsys.readouterr().out
    assert 'admin/DEMO_PASSWORD_ANALISTA' in salida
    for archivo in tmp_path.rglob('*'):
        if archivo.is_file():
            assert archivo.read_text(encoding='utf-8') not in salida


def test_main_sin_carpeta_explica_el_uso(capsys):
    assert gs.main(['x']) == 2
    assert 'generar_secretos.py' in capsys.readouterr().err
