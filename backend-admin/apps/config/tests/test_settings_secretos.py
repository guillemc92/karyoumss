"""`INTERNAL_SERVICE_SECRET` es obligatorio (DD-AUD-001 F3, issue #4).

Hallazgo F12-02: tenía un valor por defecto escrito en el código. Como protege
la llamada interna con la que backend-clinic verifica el MFA de la firma, un
despliegue que olvidara la variable aceptaría un secreto público.

Se importa el settings PRINCIPAL en un proceso nuevo, sin cargar el `.env`
local, que taparía la ausencia que se quiere probar.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[3]          # backend-admin

CODIGO = (
    'import dotenv; dotenv.load_dotenv = lambda *a, **k: None\n'
    'import admin_backend.settings\n'
)

OBLIGATORIAS = {
    'DJANGO_SECRET_KEY': 'k' * 50,
    'AUTH_BRIDGE_SECRET': 'b' * 50,
    'AUTH_ADMIN_JWT_SECRET': 'a' * 50,
    'TOTP_VAULT_KEY': 'A' * 43 + '=',
    'INTERNAL_SERVICE_SECRET': 'i' * 50,
}


def _arrancar(sin: str | None = None) -> subprocess.CompletedProcess:
    entorno = {k: v for k, v in os.environ.items()
               if not k.startswith(('DJANGO_', 'INTERNAL_', 'AUTH_', 'TOTP_', 'POSTGRES_'))}
    entorno.update(OBLIGATORIAS)
    if sin:
        entorno.pop(sin)
    return subprocess.run([sys.executable, '-c', CODIGO], cwd=BASE, env=entorno,
                          capture_output=True, text=True, timeout=120)


def test_con_todo_configurado_arranca():
    r = _arrancar()
    assert r.returncode == 0, r.stderr


def test_sin_internal_service_secret_no_arranca_y_dice_cual_falta():
    r = _arrancar(sin='INTERNAL_SERVICE_SECRET')
    assert r.returncode != 0
    assert 'Missing required env var: INTERNAL_SERVICE_SECRET' in r.stderr
