"""Lectura de la configuración del entorno (DD-OPS-001 D3).

Orden: la variable de entorno; si no está, el archivo con su nombre en
`BIOMED_SECRETS_DIR` (los secretos que el stack genera al primer arranque);
si tampoco, el valor por defecto. Un secreto obligatorio sin ninguna de las
tres fuentes sigue haciendo fallar el arranque (issue #4).
"""
import os
from pathlib import Path


def _de_archivo(key: str) -> str | None:
    carpeta = os.environ.get('BIOMED_SECRETS_DIR')
    if not carpeta:
        return None
    ruta = Path(carpeta) / key
    return ruta.read_text(encoding='utf-8').strip() if ruta.is_file() else None


def env(key: str, default=None, required=False):
    val = os.environ.get(key)
    if val is None:
        val = _de_archivo(key)
    if val is None:
        val = default
    if required and val is None:
        raise RuntimeError(f"Missing required env var: {key}")
    return val
