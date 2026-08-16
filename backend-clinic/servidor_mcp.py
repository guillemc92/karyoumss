"""Servidor MCP del laboratorio — el "USB-C" de las herramientas clínicas.

    python servidor_mcp.py                                   # espera por stdio
    npx @modelcontextprotocol/inspector python servidor_mcp.py

## Qué resuelve

Hasta ahora las herramientas viven DENTRO del proceso: `agente_acciones.ejecutar`
las importa. Eso funciona mientras el único cliente sea nuestro agente. En cuanto
aparece otro —el IDE, Claude Desktop, un agente de otro equipo— cada uno tendría
que importar el código de Django, arrastrar sus settings y su base de datos.

MCP estandariza el enchufe: este proceso **publica** las herramientas y cualquier
cliente MCP las **descubre** y las llama por JSON-RPC 2.0. El cliente no sabe que
detrás hay Django, ni qué versión, ni cómo se conecta a la base.

## Lo importante: la lógica NO se toca

Cada `@mcp.tool()` de aquí abajo delega en `agente_acciones.ejecutar`, que a su
vez usa el mismo `CATALOGO` de `tools.py` que responde el endpoint HTTP y el
enrutador. **Una sola definición de cada consulta, tres transportes.** Si esto
fuera una copia, se desincronizaría en la primera semana.

## Solo lectura, y es deliberado

Ninguna herramienta publicada escribe. Un servidor MCP es, por diseño, algo que
clientes ajenos pueden invocar; exponer por ahí la validación de un cromosoma o
la firma de un informe rompería RN-01, que exige una persona identificada. Si
algún día se publica una escritura, el contrato es `confirmado: bool` con el
plan en `confirmado=false` y el `true` puesto por un humano, nunca por el modelo.
"""
import os
import sys
from pathlib import Path

# Django tiene que estar en pie antes de importar nada de apps: el servidor se
# lanza como proceso suelto (stdio), no desde manage.py.
sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_backend.settings')

import django  # noqa: E402

django.setup()

# El SDK renombró la clase entre versiones: `FastMCP` en las antiguas,
# `MCPServer` en las nuevas. Misma API (`.tool()`, `.run()`), así que se prueba
# la que exista en vez de fijar una versión.
try:
    from mcp.server.fastmcp import FastMCP as ServidorMCP  # noqa: E402
except ModuleNotFoundError:                                 # SDK reciente
    from mcp.server.mcpserver.server import MCPServer as ServidorMCP  # noqa: E402

from apps.samples.agente_acciones import ejecutar  # noqa: E402

mcp = ServidorMCP('biomed-clinic')


@mcp.tool()
def cromosomas_para_revision() -> dict:
    """Lista los cromosomas marcados en naranja: los que se clasificaron con
    confianza por debajo del umbral (85%) y que el analista todavia no resolvio.
    Fuente: tabla clinic_chromosomes."""
    return ejecutar('CROMOSOMAS_PARA_REVISION', {})


@mcp.tool()
def casos_pendientes_firma() -> dict:
    """Lista los casos que el analista ya valido y esperan la firma digital del
    Supervisor. Es la ultima etapa antes de reportar.
    Fuente: tabla clinic_samples."""
    return ejecutar('CASOS_PENDIENTES_FIRMA', {})


@mcp.tool()
def casos_reportados() -> dict:
    """Lista los casos ya cerrados y firmados, con su nomenclatura ISCN emitida.
    Fuente: tabla clinic_samples."""
    return ejecutar('CASOS_REPORTADOS', {})


@mcp.tool()
def casos_en_proceso() -> dict:
    """Lista las muestras que el sistema esta analizando ahora mismo: el
    pipeline todavia no termina con ellas. Fuente: tabla clinic_samples."""
    return ejecutar('CASOS_EN_PROCESO', {})


@mcp.tool()
def buscar_documentacion(pregunta: str) -> dict:
    """Busca en la documentacion del laboratorio: el estandar ISCN 2024, las
    decisiones de arquitectura y las reglas de negocio. Para preguntas sobre que
    significa algo, como se calcula, quien puede hacer que, o por que el sistema
    se comporta de cierta forma. Devuelve la respuesta con su fuente citada."""
    return ejecutar('buscar_documentacion', {'pregunta': pregunta})


if __name__ == '__main__':
    # stdio: el cliente lanza este proceso y hablan por stdin/stdout (JSON-RPC).
    mcp.run(transport='stdio')
