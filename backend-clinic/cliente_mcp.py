"""Cliente MCP — descubre y llama las herramientas que publica servidor_mcp.py.

    python cliente_mcp.py                 # lista lo publicado
    python cliente_mcp.py CASOS_REPORTADOS

Sirve para dos cosas:

1. **Probar el servidor** sin montar un agente encima: si esto lista las cinco
   herramientas y ejecuta una, el transporte funciona.
2. **Demostrar el desacoplamiento**, que es el argumento de MCP. Este fichero
   NO importa Django, ni `tools.py`, ni sabe que detrás hay una base de datos:
   lanza el servidor como subproceso y habla JSON-RPC por stdio. Es exactamente
   lo que haria Claude Desktop o un agente de otro equipo.

Salida en ASCII (consola Windows cp1252).
"""
import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVIDOR = Path(__file__).resolve().parent / 'servidor_mcp.py'


async def _sesion():
    """Lanza el servidor como subproceso y abre la sesion MCP."""
    parametros = StdioServerParameters(
        command=sys.executable,
        args=[str(SERVIDOR)],
        env=None,
    )
    return stdio_client(parametros)


async def listar() -> list:
    async with await _sesion() as (lectura, escritura):
        async with ClientSession(lectura, escritura) as sesion:
            await sesion.initialize()
            r = await sesion.list_tools()
            return r.tools


async def llamar(nombre: str, argumentos: dict) -> str:
    async with await _sesion() as (lectura, escritura):
        async with ClientSession(lectura, escritura) as sesion:
            await sesion.initialize()
            r = await sesion.call_tool(nombre, argumentos or {})
            partes = []
            for c in r.content:
                partes.append(getattr(c, 'text', str(c)))
            return '\n'.join(partes)


async def main() -> int:
    if len(sys.argv) > 1:
        nombre = sys.argv[1]
        args = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
        print(f'Llamando {nombre}({args}) via MCP...')
        salida = await llamar(nombre, args)
        print(salida[:1500])
        return 0

    print('Descubriendo herramientas publicadas por servidor_mcp.py...')
    herramientas = await listar()
    print(f'\n{len(herramientas)} herramientas via JSON-RPC:\n')
    for t in herramientas:
        primera = (t.description or '').strip().splitlines()[0]
        print(f'  {t.name:28} {primera[:60]}')
    print('\nEste cliente NO importa Django ni tools.py: solo habla el protocolo.')
    return 0


if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
