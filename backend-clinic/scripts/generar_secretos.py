"""Genera los secretos del stack de producción al primer arranque (DD-OPS-001 D3).

    python scripts/generar_secretos.py /secretos

Lo corre el job `secretos` del compose, una vez antes que nadie. Por cada
servicio escribe una carpeta con un archivo por secreto; cada servicio apunta
BIOMED_SECRETS_DIR a la suya. Los compartidos (el JWT, el secreto interno)
tienen el mismo valor en todas las carpetas que los usan.

- Lo que ya existe no se toca: los secretos sobreviven a un `down`, no a un
  `down -v`.
- Nada sale por la salida estándar: solo los nombres, nunca los valores.
- Cada archivo queda con permisos 600 y del dueño de quien lo lee.
"""
import base64
import os
import secrets
import sys
from pathlib import Path

USUARIO_APP = 10001   # el de las imágenes de clinic, admin y ml
USUARIO_POSTGRES = 70  # el de postgres:17-alpine


def _hex() -> str:
    return secrets.token_hex(32)


def _fernet() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()


def _clave_demo() -> str:
    # La política de backend-admin: 12 o más caracteres, una mayúscula y un dígito.
    return f'Biomed-{secrets.token_urlsafe(12)}-9X'


# Los compartidos se generan una vez y se copian a cada carpeta que los usa.
COMPARTIDOS = {
    'AUTH_ADMIN_JWT_SECRET': _hex,
    'INTERNAL_SERVICE_SECRET': _hex,
    'ADMIN_DB_PASSWORD': _hex,
}

CARPETAS = {
    'clinic': (USUARIO_APP, {
        'DJANGO_SECRET_KEY': _hex,
        'PATIENT_VAULT_KEY': _fernet,
        'AUTH_ADMIN_JWT_SECRET': 'AUTH_ADMIN_JWT_SECRET',
        'INTERNAL_SERVICE_SECRET': 'INTERNAL_SERVICE_SECRET',
    }),
    'admin': (USUARIO_APP, {
        'DJANGO_SECRET_KEY': _hex,
        'AUTH_BRIDGE_SECRET': _hex,
        'TOTP_VAULT_KEY': _fernet,
        'AUTH_ADMIN_JWT_SECRET': 'AUTH_ADMIN_JWT_SECRET',
        'INTERNAL_SERVICE_SECRET': 'INTERNAL_SERVICE_SECRET',
        'POSTGRES_PASSWORD': 'ADMIN_DB_PASSWORD',
        'DEMO_PASSWORD_ADMIN': _clave_demo,
        'DEMO_PASSWORD_ANALISTA': _clave_demo,
        'DEMO_PASSWORD_SUPERVISOR': _clave_demo,
    }),
    'postgres': (USUARIO_POSTGRES, {
        'POSTGRES_PASSWORD': _hex,
        'ADMIN_DB_PASSWORD': 'ADMIN_DB_PASSWORD',
    }),
}


def _escribir(ruta: Path, valor: str, dueno: int | None) -> None:
    ruta.write_text(valor, encoding='utf-8')
    os.chmod(ruta, 0o600)
    if dueno is not None:
        os.chown(ruta, dueno, dueno)


def generar(raiz: Path, cambiar_dueno: bool = True) -> list[str]:
    """Crea lo que falte y devuelve los nombres creados, como `carpeta/SECRETO`."""
    comun = raiz / '.compartidos'
    comun.mkdir(parents=True, exist_ok=True)
    os.chmod(comun, 0o700)
    creados = []
    for nombre, fabrica in COMPARTIDOS.items():
        ruta = comun / nombre
        if not ruta.exists():
            _escribir(ruta, fabrica(), None)
    for carpeta, (dueno, secretos_carpeta) in CARPETAS.items():
        destino = raiz / carpeta
        destino.mkdir(exist_ok=True)
        dueno = dueno if cambiar_dueno else None
        if dueno is not None:
            os.chown(destino, dueno, dueno)
        os.chmod(destino, 0o700)
        for nombre, origen in secretos_carpeta.items():
            ruta = destino / nombre
            if ruta.exists():
                continue
            valor = (comun / origen).read_text(encoding='utf-8') if isinstance(origen, str) else origen()
            _escribir(ruta, valor, dueno)
            creados.append(f'{carpeta}/{nombre}')
    return creados


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__.strip().splitlines()[2].strip(), file=sys.stderr)
        return 2
    creados = generar(Path(argv[1]))
    print(f'secretos nuevos: {len(creados)}' + (f" ({', '.join(creados)})" if creados else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
