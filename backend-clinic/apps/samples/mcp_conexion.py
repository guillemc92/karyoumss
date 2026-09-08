"""Puente entre el bucle del agente y el servidor MCP (fase 5).

El bucle de `agente.py` recibe `(schemas, ejecutar)` y no sabe de dónde salen.
Hasta ahora se los daba `agente_acciones` por import directo. Este módulo se los
da **descubriéndolos por protocolo**: el agente deja de importar las
herramientas y pasa a preguntarle al servidor qué existe.

    local  : schemas=agente_acciones.schemas()   ejecutar=agente_acciones.ejecutar
    vía MCP: schemas=conexion.descubrir_tools()  ejecutar=conexion.ejecutar_tool

**El bucle no cambia ni una línea.** Ese era el objetivo del desacople.

## La traducción es trivial, y esa es la gracia

MCP devuelve `{name, description, inputSchema}`; el tool calling de OpenAI
espera `{type:'function', function:{name, description, parameters}}`. Es el
**mismo JSON Schema con otro envoltorio** — por eso el estándar funciona sin que
nadie tenga que ponerse de acuerdo en nada más.

## Por qué hay un hilo con su propio bucle de eventos

El SDK de MCP es asíncrono y nuestro agente es síncrono. Abrir y cerrar una
sesión por cada llamada sería lo simple, pero cada apertura **relanza el proceso
del servidor**, que a su vez arranca Django entero: varios segundos por acción,
y el agente hace varias.

Así que la sesión se abre una vez y vive en un hilo con su propio bucle de
eventos, al que se le envían las corrutinas desde el hilo síncrono. Se usa como
gestor de contexto para garantizar que el subproceso se cierra siempre.
"""
from __future__ import annotations

import asyncio
import json
import sys
import threading
from pathlib import Path
from typing import Any

SERVIDOR = Path(__file__).resolve().parents[2] / 'servidor_mcp.py'
TIMEOUT_S = 300.0


class McpError(Exception):
    """El servidor MCP no responde o devolvió algo inutilizable."""


VACIO = {'type': 'object', 'properties': {}, 'required': []}


def _a_formato_openai(tool: Any) -> dict:
    """MCP -> tool calling. Mismo schema, otro envoltorio.

    El SDK nombra el campo `inputSchema` en unas versiones e `input_schema` en
    otras. Se prueban ambos en vez de fijar una versión — mismo criterio que con
    `FastMCP`/`MCPServer` en el servidor.
    """
    esquema = (getattr(tool, 'inputSchema', None)
               or getattr(tool, 'input_schema', None)
               or VACIO)
    return {
        'type': 'function',
        'function': {
            'name': tool.name,
            'description': (tool.description or '').strip(),
            'parameters': esquema,
        },
    }


class ConexionMCP:
    """Sesión MCP viva, usable desde código síncrono.

        with ConexionMCP() as conexion:
            schemas = conexion.descubrir_tools()
            resultado = conexion.ejecutar_tool('casos_reportados', {})
    """

    def __init__(self, servidor: Path = SERVIDOR, timeout: float = TIMEOUT_S):
        self.servidor = servidor
        self.timeout = timeout
        self._loop: asyncio.AbstractEventLoop | None = None
        self._hilo: threading.Thread | None = None
        self._sesion = None
        self._cm_stdio = None
        self._cm_sesion = None

    # --- ciclo de vida -------------------------------------------------------

    def __enter__(self) -> ConexionMCP:
        self._loop = asyncio.new_event_loop()
        self._hilo = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._hilo.start()
        self._esperar(self._abrir())
        return self

    def __exit__(self, *_) -> None:
        try:
            self._esperar(self._cerrar())
        except Exception:                            # noqa: BLE001
            pass                                     # cerrar no debe enmascarar
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._hilo:
            self._hilo.join(timeout=10)

    def _esperar(self, corutina):
        """Envía una corrutina al hilo del bucle y espera su resultado."""
        if self._loop is None:
            raise McpError('la conexión no está abierta')
        futuro = asyncio.run_coroutine_threadsafe(corutina, self._loop)
        try:
            return futuro.result(timeout=self.timeout)
        except Exception as exc:                     # noqa: BLE001
            raise McpError(str(exc)) from exc

    async def _abrir(self) -> None:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        parametros = StdioServerParameters(
            command=sys.executable, args=[str(self.servidor)], env=None,
        )
        self._cm_stdio = stdio_client(parametros)
        lectura, escritura = await self._cm_stdio.__aenter__()
        self._cm_sesion = ClientSession(lectura, escritura)
        self._sesion = await self._cm_sesion.__aenter__()
        await self._sesion.initialize()

    async def _cerrar(self) -> None:
        if self._cm_sesion is not None:
            await self._cm_sesion.__aexit__(None, None, None)
        if self._cm_stdio is not None:
            await self._cm_stdio.__aexit__(None, None, None)

    # --- lo que el bucle necesita -------------------------------------------

    def descubrir_tools(self) -> list[dict]:
        """`tools/list` traducido al formato que espera el bucle."""
        r = self._esperar(self._sesion.list_tools())
        return [_a_formato_openai(t) for t in r.tools]

    def ejecutar_tool(self, nombre: str, argumentos: dict) -> dict:
        """`tools/call`. Devuelve siempre un dict — un error es una observación
        útil para que el modelo rectifique, no un motivo para tumbar el bucle."""
        try:
            r = self._esperar(self._sesion.call_tool(nombre, argumentos or {}))
        except McpError as exc:
            return {'error': f'la herramienta «{nombre}» falló: {exc}'}

        # El contenido viene como bloques de texto; los tools devuelven JSON.
        textos = [getattr(c, 'text', '') for c in getattr(r, 'content', [])]
        crudo = '\n'.join(t for t in textos if t)
        try:
            return json.loads(crudo)
        except (json.JSONDecodeError, TypeError):
            return {'resultado': crudo}
