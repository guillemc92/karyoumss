"""La apertura y el cierre REALES de la sesion MCP.

`test_mcp_conexion.py` sustituye `_abrir` y `_cerrar` enteros —y hace bien: lo
que prueba es el hilo y el bucle de eventos, no el arranque del subproceso—. El
efecto lateral es que las dos corrutinas que hablan con el SDK no se ejecutan
nunca.

Aqui se ejecutan de verdad, con el doble puesto en la **frontera del SDK**
(`stdio_client`, `ClientSession`). No se lanza el servidor: arrancarlo levanta
Django entero y tardaria segundos por test.

## Lo que se asegura

1. Que el servidor se lanza con `sys.executable` y no con «python». En Windows,
   con el venv activo, «python» seria otro interprete: el servidor arrancaria
   sin las dependencias y el agente via MCP fallaria solo en produccion.
2. Que se llama a `initialize()`. Sin ese apreton de manos la sesion existe pero
   no sirve, y el fallo aparece despues, en `tools/list`, lejos de la causa.
3. Que el cierre deshace en orden inverso y tolera que no haya nada abierto —si
   `_abrir` fallo a la mitad, `__exit__` llama a `_cerrar` igual.
"""
import asyncio
import sys

import pytest

from apps.samples.mcp_conexion import SERVIDOR, ConexionMCP


class SesionFalsa:
    """Doble de `ClientSession`: registra el apreton de manos y los canales."""

    def __init__(self, lectura, escritura):
        self.canales = (lectura, escritura)
        self.inicializada = False
        self.salidas = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        self.salidas.append('sesion')
        return False

    async def initialize(self):
        self.inicializada = True


class StdioFalso:
    """Doble del gestor de contexto que lanza el subproceso."""

    def __init__(self, parametros):
        self.parametros = parametros
        self.salidas = []

    async def __aenter__(self):
        return ('canal_lectura', 'canal_escritura')

    async def __aexit__(self, *a):
        self.salidas.append('stdio')
        return False


@pytest.fixture
def sdk(monkeypatch):
    """Sustituye el SDK y devuelve lo que se construyo, para inspeccionarlo."""
    import mcp
    import mcp.client.stdio

    registro = {'orden': []}

    def stdio_client(parametros):
        registro['parametros'] = parametros
        stdio = StdioFalso(parametros)
        stdio.salidas = registro['orden']
        registro['stdio'] = stdio
        return stdio

    def client_session(lectura, escritura):
        sesion = SesionFalsa(lectura, escritura)
        sesion.salidas = registro['orden']
        registro['sesion'] = sesion
        return sesion

    monkeypatch.setattr(mcp.client.stdio, 'stdio_client', stdio_client)
    monkeypatch.setattr(mcp, 'ClientSession', client_session)
    return registro


def abrir(conexion):
    """Corre la corrutina real en un bucle de usar y tirar."""
    asyncio.run(conexion._abrir())


# --- la apertura ------------------------------------------------------------

def test_el_servidor_se_lanza_con_el_interprete_de_este_entorno(sdk):
    """`sys.executable`, no «python».

    Con el venv activo, «python» resolveria al interprete del sistema: el
    servidor arrancaria sin Django ni las dependencias y el agente via MCP
    fallaria solo en produccion, cuando alguien pidiera `mcp: true`.
    """
    abrir(ConexionMCP())

    assert sdk['parametros'].command == sys.executable
    assert sdk['parametros'].env is None


def test_se_le_pasa_el_guion_del_servidor_y_ese_fichero_existe():
    """`SERVIDOR` es una ruta calculada con `parents[2]`. Si alguien moviera el
    modulo de sitio o renombrara el guion, la ruta seguiria construyendose sin
    error y el fallo apareceria al lanzar el subproceso, ya en ejecucion."""
    assert SERVIDOR.name == 'servidor_mcp.py'
    assert SERVIDOR.is_file(), 'el guion del servidor MCP no esta donde se espera'


def test_los_argumentos_llevan_la_ruta_del_servidor(sdk):
    conexion = ConexionMCP()
    abrir(conexion)
    assert sdk['parametros'].args == [str(conexion.servidor)]


def test_la_sesion_queda_inicializada_y_con_los_canales_del_subproceso(sdk):
    """Sin `initialize()` la sesion existe pero no sirve: el fallo saldria
    despues, en `tools/list`, lejos de donde esta la causa."""
    conexion = ConexionMCP()
    abrir(conexion)

    assert conexion._sesion is sdk['sesion']
    assert conexion._sesion.inicializada is True
    assert conexion._sesion.canales == ('canal_lectura', 'canal_escritura')


def test_abrir_guarda_los_dos_gestores_para_poder_cerrarlos(sdk):
    """Se guardan `_cm_stdio` y `_cm_sesion` porque el cierre no es automatico:
    la sesion vive en otro hilo y nadie sale del `async with` por su cuenta."""
    conexion = ConexionMCP()
    abrir(conexion)

    assert conexion._cm_stdio is sdk['stdio']
    assert conexion._cm_sesion is sdk['sesion']


# --- el cierre --------------------------------------------------------------

def test_cerrar_deshace_en_orden_inverso(sdk):
    """Primero la sesion, despues el transporte. Al reves se cerraria el canal
    por debajo de una sesion que todavia esta despidiendose."""
    conexion = ConexionMCP()
    abrir(conexion)

    asyncio.run(conexion._cerrar())

    assert sdk['orden'] == ['sesion', 'stdio']


def test_cerrar_sin_haber_abierto_no_revienta():
    """`__exit__` llama a `_cerrar` pase lo que pase — tambien si `_abrir` se
    quedo a medias. Un AttributeError aqui enmascararia el error de verdad."""
    asyncio.run(ConexionMCP()._cerrar())      # no debe lanzar


def test_cerrar_a_medias_cierra_lo_que_si_se_abrio(sdk):
    """Si el transporte se abrio pero la sesion no, hay que cerrar el
    transporte: si no, queda un subproceso huerfano por cada intento fallido."""
    conexion = ConexionMCP()
    abrir(conexion)
    conexion._cm_sesion = None                # como si hubiera fallado ahi

    asyncio.run(conexion._cerrar())

    assert sdk['orden'] == ['stdio']
