"""Secretos obligatorios y DEBUG apagado por defecto (DD-AUD-001 F3, issue #4).

Hallazgo F12-02 de la auditoría 12-factor: `DJANGO_SECRET_KEY` e
`INTERNAL_SERVICE_SECRET` tenían un valor por defecto escrito en el código. Un
despliegue que olvidara la variable arrancaba con un secreto que conoce
cualquiera con acceso al repositorio. Y el clínico arrancaba con `DEBUG=True`.

Cada prueba importa `settings` en un proceso nuevo, con un entorno controlado y
**sin cargar el `.env` local**: si lo cargara, los valores del desarrollador
taparían justo la ausencia que se quiere probar.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[3]          # backend-clinic

CODIGO = (
    'import dotenv; dotenv.load_dotenv = lambda *a, **k: None\n'
    'import clinic_backend.settings as s\n'
    'print("DEBUG=" + str(s.DEBUG))\n'
)

OBLIGATORIAS = {
    'DJANGO_SECRET_KEY': 'k' * 50,
    'INTERNAL_SERVICE_SECRET': 'i' * 50,
    'AUTH_ADMIN_JWT_SECRET': 'a' * 50,
    'PATIENT_VAULT_KEY': 'A' * 43 + '=',
}


def _arrancar(sin: str | None = None, **extra: str) -> subprocess.CompletedProcess:
    entorno = {k: v for k, v in os.environ.items()
               if not k.startswith(('DJANGO_', 'INTERNAL_', 'AUTH_', 'PATIENT_', 'CLINIC_'))}
    entorno.update(OBLIGATORIAS)
    entorno.update(extra)
    if sin:
        entorno.pop(sin)
    return subprocess.run([sys.executable, '-c', CODIGO], cwd=BASE, env=entorno,
                          capture_output=True, text=True, timeout=120)


def test_con_todo_configurado_arranca():
    r = _arrancar()
    assert r.returncode == 0, r.stderr


@pytest.mark.parametrize('variable', ['DJANGO_SECRET_KEY', 'INTERNAL_SERVICE_SECRET'])
def test_sin_el_secreto_no_arranca_y_dice_cual_falta(variable):
    r = _arrancar(sin=variable)
    assert r.returncode != 0
    assert f'Missing required env var: {variable}' in r.stderr


def test_debug_apagado_si_no_se_pide():
    assert 'DEBUG=False' in _arrancar().stdout


def test_debug_encendido_solo_si_se_pide():
    assert 'DEBUG=True' in _arrancar(DJANGO_DEBUG='True').stdout
