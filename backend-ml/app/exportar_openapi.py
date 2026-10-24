"""Exporta el contrato OpenAPI de backend-ml (DD-API-001 D3).

    python -m app.exportar_openapi            # escribe backend-ml/openapi.json
    python -m app.exportar_openapi --salida X # en otro sitio (lo usa el CI)

FastAPI genera el contrato a partir de los modelos Pydantic y de las firmas de
los endpoints. Se escribe con las claves ordenadas y un salto de línea final:
exportar dos veces da el mismo archivo, así que el drift del CI solo falla si
alguien cambió la API sin regenerar el contrato.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .main import app

POR_DEFECTO = Path(__file__).resolve().parent.parent / 'openapi.json'


def contrato() -> str:
    return json.dumps(app.openapi(), indent=2, sort_keys=True, ensure_ascii=False) + '\n'


def main(argv: list[str] | None = None) -> Path:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--salida', type=Path, default=POR_DEFECTO)
    args = parser.parse_args(argv)
    args.salida.write_text(contrato(), encoding='utf-8')
    return args.salida


if __name__ == '__main__':  # pragma: no cover
    print(main())
