"""Tests del puente entre el bucle del agente y el servidor MCP.

Este módulo sostiene la afirmación central del nivel 4: que el agente
**descubre** las herramientas por protocolo en vez de importarlas, y que el
bucle no cambia ni una línea al hacerlo. Estaba al 0% de cobertura.

Lo que se fija aquí es la **traducción** y el **contrato de errores**, que es
donde un fallo pasaría inadvertido: si `ejecutar_tool` lanzara en vez de
devolver un dict, un fallo de una herramienta tumbaría al agente entero en vez
de darle al modelo la oportunidad de rectificar.

No se levanta el servidor real: arrancar el subproceso levanta Django entero y
tarda segundos. El arranque de verdad se ejercita a mano con `cliente_mcp.py`,
que es la fase 4 de la consigna.
"""
import json

import pytest

from apps.samples.mcp_conexion import (
    VACIO,
    ConexionMCP,
    McpError,
    _a_formato_openai,
)


class ToolMCP:
    """Lo que devuelve `tools/list`: nombre, descripción y JSON Schema."""

    def __init__(self, name, description, esquema=None, campo='inputSchema'):
        self.name, self.description = name, description
        if esquema is not None:
            setattr(self, campo, esquema)


ESQUEMA = {'type': 'object', 'properties': {'chn_code': {'type': 'string'}},
           'required': ['chn_code']}


class TestTraduccionDeSchema:
    """MCP y el tool calling usan el MISMO JSON Schema con otro envoltorio."""

    def test_envuelve_el_schema_sin_tocarlo(self):
        d = _a_formato_openai(ToolMCP('buscar', 'Busca un caso.', ESQUEMA))

        assert d['type'] == 'function'
        assert d['function']['name'] == 'buscar'
        # El schema pasa TAL CUAL: si se transformara, el modelo recibiría un
        # contrato distinto del que publica el servidor.
        assert d['function']['parameters'] is ESQUEMA

    def test_acepta_inputSchema_y_input_schema(self):
        # El SDK cambia el nombre del campo entre versiones. Se prueban ambos en
        # vez de fijar una version.
        for campo in ('inputSchema', 'input_schema'):
            d = _a_formato_openai(ToolMCP('t', 'd', ESQUEMA, campo=campo))

            assert d['function']['parameters'] is ESQUEMA, campo

    def test_sin_schema_declara_un_objeto_vacio_valido(self):
        # Una herramienta sin argumentos sigue necesitando un schema: sin él, el
        # SDK del modelo rechaza la declaración.
        d = _a_formato_openai(ToolMCP('sin_args', 'No lleva argumentos.'))

        assert d['function']['parameters'] == VACIO

    def test_la_descripcion_se_limpia_porque_ES_el_prompt(self):
        # Es lo único que el modelo lee para decidir si usa la herramienta.
        d = _a_formato_openai(ToolMCP('t', '  Lista los casos.\n  ', ESQUEMA))

        assert d['function']['description'] == 'Lista los casos.'

    def test_una_descripcion_vacia_no_rompe_la_traduccion(self):
        assert _a_formato_openai(ToolMCP('t', None, ESQUEMA))['function']['description'] == ''


# --------------------------------------------------------------------------
# Doble de la sesión MCP: se prueba el puente, no el SDK.
# --------------------------------------------------------------------------
class SesionFalsa:
    def __init__(self, tools=(), contenido=None, revienta=False):
        self._tools = list(tools)
        self._contenido = contenido
        self._revienta = revienta
        self.llamadas = []

    def list_tools(self):
        return type('R', (), {'tools': self._tools})()

    def call_tool(self, nombre, argumentos):
        self.llamadas.append((nombre, argumentos))
        if self._revienta:
            # DEVUELVE el fallo en vez de lanzarlo: en el codigo real
            # `call_tool` entrega una corrutina y la excepcion aparece al
            # esperarla, dentro de `_esperar`. Un doble que lanza antes de
            # tiempo probaria un camino que no existe.
            return RuntimeError('el servidor se cayó')
        return type('R', (), {'content': self._contenido or []})()


def bloque(texto):
    return type('B', (), {'text': texto})()


@pytest.fixture
def conexion():
    """Conexión con el bucle de eventos cortocircuitado: `_esperar` resuelve
    directamente lo que devuelva el doble."""
    def montar(sesion):
        c = ConexionMCP()
        c._sesion = sesion

        def _esperar(valor):
            """Cortocircuita el bucle de eventos conservando su contrato: lo
            que falla al esperarse sale como `McpError`."""
            if isinstance(valor, Exception):
                raise McpError(str(valor))
            return valor

        c._esperar = _esperar
        return c
    return montar


class TestDescubrimiento:
    def test_traduce_todo_lo_que_publica_el_servidor(self, conexion):
        c = conexion(SesionFalsa([ToolMCP('a', 'A.', ESQUEMA),
                                  ToolMCP('b', 'B.', ESQUEMA)]))

        schemas = c.descubrir_tools()

        assert [s['function']['name'] for s in schemas] == ['a', 'b']

    def test_un_servidor_sin_herramientas_da_lista_vacia_no_error(self, conexion):
        assert conexion(SesionFalsa([])).descubrir_tools() == []


class TestEjecucion:
    def test_devuelve_el_JSON_que_produjo_la_herramienta(self, conexion):
        datos = {'herramienta': 'CASOS_REPORTADOS', 'n': 2}
        c = conexion(SesionFalsa(contenido=[bloque(json.dumps(datos))]))

        assert c.ejecutar_tool('casos_reportados', {}) == datos

    def test_pasa_el_nombre_y_los_argumentos_al_servidor(self, conexion):
        sesion = SesionFalsa(contenido=[bloque('{}')])

        conexion(sesion).ejecutar_tool('buscar', {'chn_code': 'CHN-1'})

        assert sesion.llamadas == [('buscar', {'chn_code': 'CHN-1'})]

    def test_sin_argumentos_manda_un_dict_vacio_no_None(self, conexion):
        sesion = SesionFalsa(contenido=[bloque('{}')])

        conexion(sesion).ejecutar_tool('casos_reportados', None)

        assert sesion.llamadas == [('casos_reportados', {})]

    def test_junta_los_bloques_de_texto(self, conexion):
        # El contenido viene troceado; el JSON puede quedar partido.
        c = conexion(SesionFalsa(contenido=[bloque('{"n":'), bloque(' 3}')]))

        assert c.ejecutar_tool('t', {}) == {'n': 3}

    def test_una_respuesta_que_no_es_JSON_se_devuelve_como_texto(self, conexion):
        c = conexion(SesionFalsa(contenido=[bloque('no soy json')]))

        assert c.ejecutar_tool('t', {}) == {'resultado': 'no soy json'}

    def test_una_respuesta_vacia_no_lanza(self, conexion):
        assert conexion(SesionFalsa(contenido=[])).ejecutar_tool('t', {}) == {'resultado': ''}


class TestContratoDeErrores:
    """La regla que hace que el agente sobreviva a una herramienta rota."""

    def test_un_fallo_del_servidor_vuelve_como_dict_no_como_excepcion(self, conexion):
        # Si esto lanzara, un fallo de UNA herramienta tumbaría el bucle entero
        # en vez de darle al modelo la ocasión de rectificar.
        c = conexion(SesionFalsa(revienta=True))

        r = c.ejecutar_tool('rota', {})

        assert 'error' in r and 'rota' in r['error']

    def test_usar_la_conexion_sin_abrir_lo_dice_claro(self):
        with pytest.raises(McpError, match='no está abierta'):
            ConexionMCP()._esperar(None)


class TestCicloDeVidaDelHilo:
    """La parte más delicada del módulo: la sesión vive en un hilo con su propio
    bucle de eventos. Un fallo aquí no da error — deja el proceso colgado.

    Se sustituyen `_abrir`/`_cerrar` para no lanzar el servidor real (arrancarlo
    levanta Django entero), pero el hilo y el bucle son los de verdad.
    """

    @pytest.fixture
    def conexion_viva(self, monkeypatch):
        import apps.samples.mcp_conexion as mod

        abiertas, cerradas = [], []

        async def abrir(self):
            abiertas.append(True)
            self._sesion = SesionFalsa([ToolMCP('t', 'T.', ESQUEMA)])

        async def cerrar(self):
            cerradas.append(True)

        monkeypatch.setattr(mod.ConexionMCP, '_abrir', abrir)
        monkeypatch.setattr(mod.ConexionMCP, '_cerrar', cerrar)
        return abiertas, cerradas

    def test_abre_el_hilo_al_entrar_y_lo_para_al_salir(self, conexion_viva):
        abiertas, cerradas = conexion_viva

        with ConexionMCP() as c:
            assert c._hilo.is_alive()
            hilo = c._hilo

        assert abiertas and cerradas
        hilo.join(timeout=5)
        assert not hilo.is_alive(), 'el hilo quedó vivo: fuga de recursos'

    def test_una_excepcion_dentro_del_with_no_deja_el_hilo_colgado(self, conexion_viva):
        # Si el agente revienta a mitad, el subproceso tiene que cerrarse igual.
        with pytest.raises(ValueError):
            with ConexionMCP() as c:
                hilo = c._hilo
                raise ValueError('algo falló en el bucle del agente')

        hilo.join(timeout=5)
        assert not hilo.is_alive()

    def test_un_fallo_al_cerrar_no_enmascara_el_error_original(self, monkeypatch):
        import apps.samples.mcp_conexion as mod

        async def abrir(self):
            self._sesion = SesionFalsa()

        async def cerrar(self):
            raise RuntimeError('el subproceso ya no estaba')

        monkeypatch.setattr(mod.ConexionMCP, '_abrir', abrir)
        monkeypatch.setattr(mod.ConexionMCP, '_cerrar', cerrar)

        with ConexionMCP():                 # no debe propagar el fallo de cierre
            pass

    def test_el_esperar_REAL_despacha_al_bucle_del_hilo(self, conexion_viva):
        # Este es el camino de produccion: una corrutina enviada desde el hilo
        # sincrono al bucle del hilo de eventos.
        async def suma():
            return 40 + 2

        with ConexionMCP() as c:
            assert c._esperar(suma()) == 42

    def test_un_fallo_dentro_de_la_corrutina_sale_como_McpError(self, conexion_viva):
        async def revienta():
            raise RuntimeError('timeout del servidor')

        with ConexionMCP() as c:
            with pytest.raises(McpError, match='timeout del servidor'):
                c._esperar(revienta())
