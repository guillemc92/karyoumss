"""Demo 1 de M8 — issue #4: sin el secreto, el servicio no arranca.

    backend-clinic/.venv/Scripts/python.exe scripts/demo_m8_secretos.py

Arranca la configuración de backend-clinic en un proceso nuevo, con un entorno
controlado y SIN leer el `.env` local (que taparía la ausencia que se quiere
mostrar). Tres casos:

1. Con todo configurado: arranca, y DEBUG queda apagado si no se pide.
2. Sin DJANGO_SECRET_KEY: antes arrancaba con una clave escrita en el código.
3. Sin INTERNAL_SERVICE_SECRET: antes arrancaba con un secreto público.

No imprime ningún valor secreto: los del caso 1 son valores de demostración.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

CLINIC = Path(__file__).resolve().parents[1] / 'backend-clinic'
CODIGO = ('import dotenv; dotenv.load_dotenv = lambda *a, **k: None\n'
          'import clinic_backend.settings as s\n'
          'print(f"arranca - DEBUG={s.DEBUG}")\n')
DEMO = {'DJANGO_SECRET_KEY': 'demo-' + 'k' * 50, 'INTERNAL_SERVICE_SECRET': 'demo-' + 'i' * 50,
        'AUTH_ADMIN_JWT_SECRET': 'demo-' + 'a' * 50, 'PATIENT_VAULT_KEY': 'A' * 43 + '='}


def arrancar(titulo: str, quitar: str | None = None) -> None:
    entorno = {k: v for k, v in os.environ.items()
               if not k.startswith(('DJANGO_', 'INTERNAL_', 'AUTH_', 'PATIENT_', 'CLINIC_'))}
    entorno.update(DEMO)
    if quitar:
        entorno.pop(quitar)
    r = subprocess.run([sys.executable, '-c', CODIGO], cwd=CLINIC, env=entorno,
                       capture_output=True, text=True, timeout=120)
    salida = r.stdout.strip() if r.returncode == 0 else r.stderr.strip().splitlines()[-1]
    marca = 'OK  ' if r.returncode == 0 else 'NO ARRANCA'
    print(f'{titulo:<38} → {marca}  {salida}')


if __name__ == '__main__':
    arrancar('1. Con todo configurado')
    arrancar('2. Sin DJANGO_SECRET_KEY', 'DJANGO_SECRET_KEY')
    arrancar('3. Sin INTERNAL_SERVICE_SECRET', 'INTERNAL_SERVICE_SECRET')
