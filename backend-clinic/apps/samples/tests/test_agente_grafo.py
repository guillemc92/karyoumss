"""Tests del agente como grafo con memoria persistente (nivel 5).

Lo que se fija aquí es lo que rompería sin avisar: que la traza del nivel 5
tenga **la misma forma** que la del nivel 4 —si no, la evidencia deja de ser
comparable entre niveles y el endpoint cambia de contrato en silencio—, que el
tope de pasos se traduzca bien al `recursion_limit` del grafo, y que sin modelo
degrade en vez de reventar (RN-07).

No se llama al modelo: `llama3.2:3b` tarda ~100 s por paso y eso no cabe en una
suite. La cadena completa se mide aparte, con `manage.py eval_memoria`.
"""
import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from apps.samples.agente import MAX_PASOS, AgenteError
from apps.samples.agente_grafo import (
    LIMITE_RECURSION,
    RUTA_MEMORIA,
    _traza_desde,
    conversar,
)


def ia_msg(contenido='', tool_calls=None, tokens=(0, 0)):
    m = AIMessage(content=contenido, tool_calls=tool_calls or [])
    if any(tokens):
        m.usage_metadata = {'input_tokens': tokens[0], 'output_tokens': tokens[1],
                            'total_tokens': sum(tokens)}
    return m


def llamada(nombre, args=None, id_='c1'):
    return {'name': nombre, 'args': args or {}, 'id': id_, 'type': 'tool_call'}


class TestTrazaCompatibleConNivel4:
    """La traza es la evidencia que pide la consigna: no puede cambiar de forma."""

    def test_registra_pregunta_accion_observacion_y_respuesta(self):
        mensajes = [
            HumanMessage(content='que cromosomas hay pendientes?'),
            ia_msg(tool_calls=[llamada('CROMOSOMAS_PARA_REVISION')]),
            ToolMessage(content="{'n': 3}", tool_call_id='c1',
                        name='CROMOSOMAS_PARA_REVISION'),
            ia_msg('Hay 3 pendientes.'),
        ]

        traza = _traza_desde(mensajes, 0, 0.0)

        assert [p['tipo'] for p in traza.pasos] == [
            'pregunta', 'accion', 'observacion', 'respuesta']

    def test_suma_los_tokens_de_todas_las_llamadas(self):
        # Sin esto no se puede enseñar el coste, que es lo que el docente pide
        # ver en la traza.
        mensajes = [ia_msg('a', tokens=(100, 10)), ia_msg('b', tokens=(250, 20))]

        traza = _traza_desde(mensajes, 0, 0.0)

        assert (traza.tokens_entrada, traza.tokens_salida) == (350, 30)

    def test_una_llamada_sin_uso_declarado_no_rompe_el_conteo(self):
        traza = _traza_desde([ia_msg('sin metadatos')], 0, 0.0)

        assert traza.tokens_entrada == 0

    def test_la_accion_lleva_el_nombre_y_los_argumentos(self):
        mensajes = [ia_msg(tool_calls=[llamada('buscar_documentacion',
                                               {'pregunta': 'que es naranja'})])]

        traza = _traza_desde(mensajes, 0, 0.0)

        assert 'buscar_documentacion' in traza.pasos[0]['detalle']
        assert 'que es naranja' in traza.pasos[0]['detalle']

    def test_varias_herramientas_en_un_paso_dan_varias_acciones(self):
        mensajes = [ia_msg(tool_calls=[llamada('A', id_='1'), llamada('B', id_='2')])]

        traza = _traza_desde(mensajes, 0, 0.0)

        assert len(traza.pasos) == 2


class TestSoloElTurnoActual:
    """El hilo acumula; la traza que se devuelve es de ESTE turno."""

    def test_los_mensajes_previos_no_entran_en_la_traza(self):
        # Si entraran, cada turno repetiría toda la conversación anterior y la
        # traza dejaría de decir qué hizo el agente ahora.
        previos = [HumanMessage(content='turno viejo'), ia_msg('respuesta vieja')]
        nuevos = [HumanMessage(content='turno nuevo'), ia_msg('respuesta nueva')]

        traza = _traza_desde(previos + nuevos, len(previos), 0.0)

        assert len(traza.pasos) == 2
        assert 'nuevo' in traza.pasos[0]['detalle']

    def test_un_hilo_vacio_da_una_traza_vacia(self):
        assert _traza_desde([], 0, 0.0).pasos == []


class TestFrenoYDegradacion:
    def test_el_limite_del_grafo_conserva_el_presupuesto_del_nivel_4(self):
        # Un ciclo del grafo son DOS pasos (pensar + actuar): sin duplicar, el
        # nivel 5 cortaría a la mitad de llamadas que el nivel 4.
        assert LIMITE_RECURSION == 2 * MAX_PASOS + 1

    def test_sin_IA_no_revienta_lanza_AgenteError(self, settings):
        settings.CLINIC_LLM_ENABLED = False

        with pytest.raises(AgenteError):
            conversar('lo que sea', 'hilo-x')


class TestSeparacionDeLaBaseClinica:
    def test_la_memoria_NO_vive_en_la_base_clinica(self):
        """Duplicar el estado clínico en un checkpointer crearía una segunda
        fuente de verdad para un proceso auditado (ADR-0031)."""
        assert RUTA_MEMORIA.name == 'agente_memoria.sqlite3'
        assert 'clinic_demo' not in str(RUTA_MEMORIA)


class ModeloFalso:
    """Devuelve respuestas preparadas. El grafo no distingue: solo pide `invoke`.

    Permite probar el CABLEADO del grafo —pensar -> actuar -> pensar— y la
    persistencia del checkpoint sin depender de un modelo que tarda 100 s por
    paso.
    """

    def __init__(self, guion):
        self.guion = list(guion)
        self.vistas = []            # lo que el grafo le fue pasando

    def invoke(self, mensajes):
        self.vistas.append(list(mensajes))
        return self.guion.pop(0) if self.guion else ia_msg('sin guion')


@pytest.fixture
def grafo_falso(monkeypatch, tmp_path, settings):
    """Grafo real, modelo falso y memoria en un fichero desechable."""
    from apps.samples import agente_grafo as mod

    settings.CLINIC_LLM_ENABLED = True
    monkeypatch.setattr(mod, 'RUTA_MEMORIA', tmp_path / 'memoria.sqlite3')

    def montar(guion):
        mod._grafo = None                       # el grafo se cachea por proceso
        mod._conexion = None
        modelo = ModeloFalso(guion)
        monkeypatch.setattr(mod, '_modelo', lambda: modelo)
        return modelo

    yield montar
    mod._grafo = None
    mod._conexion = None


class TestElGrafoEncadena:
    def test_pide_herramienta_la_ejecuta_y_vuelve_a_pensar(self, grafo_falso, monkeypatch):
        from apps.samples import agente_grafo as mod

        ejecutadas = []
        monkeypatch.setattr(mod, 'ejecutar',
                            lambda n, a: ejecutadas.append(n) or {'n': 3})
        grafo_falso([ia_msg(tool_calls=[llamada('CROMOSOMAS_PARA_REVISION')]),
                     ia_msg('Hay 3 pendientes.')])

        r = mod.conversar('que hay pendiente?', 'hilo-1')

        assert ejecutadas == ['CROMOSOMAS_PARA_REVISION']
        assert r.respuesta == 'Hay 3 pendientes.'
        assert r.completado is True

    def test_sin_herramientas_responde_y_corta(self, grafo_falso, monkeypatch):
        from apps.samples import agente_grafo as mod

        monkeypatch.setattr(mod, 'ejecutar', lambda n, a: pytest.fail('no debia ejecutar'))
        grafo_falso([ia_msg('respuesta directa')])

        assert mod.conversar('hola', 'hilo-2').respuesta == 'respuesta directa'

    def test_un_error_de_la_herramienta_llega_como_observacion(self, grafo_falso, monkeypatch):
        """`ejecutar` nunca lanza: el modelo tiene que poder rectificar."""
        from apps.samples import agente_grafo as mod

        monkeypatch.setattr(mod, 'ejecutar', lambda n, a: {'error': 'no existe'})
        grafo_falso([ia_msg(tool_calls=[llamada('INVENTADA')]), ia_msg('perdon')])

        r = mod.conversar('x', 'hilo-3')

        assert any('no existe' in p['detalle'] for p in r.traza.pasos)


class TestMemoriaPersistente:
    """Es la única razón por la que existe el nivel 5."""

    def test_el_segundo_turno_VE_el_primero(self, grafo_falso, monkeypatch):
        from apps.samples import agente_grafo as mod

        monkeypatch.setattr(mod, 'ejecutar', lambda n, a: {'n': 3})
        modelo = grafo_falso([ia_msg('primera'), ia_msg('segunda')])

        mod.conversar('pregunta uno', 'hilo-memoria')
        mod.conversar('pregunta dos', 'hilo-memoria')

        # Lo que el modelo vio en el 2º turno tiene que incluir el 1º.
        texto = str(modelo.vistas[-1])
        assert 'pregunta uno' in texto and 'primera' in texto

    def test_hilos_distintos_no_se_mezclan(self, grafo_falso, monkeypatch):
        from apps.samples import agente_grafo as mod

        monkeypatch.setattr(mod, 'ejecutar', lambda n, a: {})
        modelo = grafo_falso([ia_msg('a'), ia_msg('b')])

        mod.conversar('secreto del hilo A', 'hilo-A')
        mod.conversar('pregunta en B', 'hilo-B')

        assert 'secreto del hilo A' not in str(modelo.vistas[-1])

    def test_el_system_prompt_se_inyecta_UNA_vez(self, grafo_falso, monkeypatch):
        # Repetirlo cada turno lo duplicaría en el historial y encarecería
        # todas las llamadas siguientes.
        from apps.samples import agente_grafo as mod

        monkeypatch.setattr(mod, 'ejecutar', lambda n, a: {})
        modelo = grafo_falso([ia_msg('a'), ia_msg('b')])

        mod.conversar('uno', 'hilo-sp')
        mod.conversar('dos', 'hilo-sp')

        from langchain_core.messages import SystemMessage
        assert sum(isinstance(m, SystemMessage) for m in modelo.vistas[-1]) == 1

    def test_olvidar_borra_el_hilo(self, grafo_falso, monkeypatch):
        from apps.samples import agente_grafo as mod

        monkeypatch.setattr(mod, 'ejecutar', lambda n, a: {})
        modelo = grafo_falso([ia_msg('a'), ia_msg('b')])

        mod.conversar('algo memorable', 'hilo-borrable')
        mod.olvidar('hilo-borrable')
        mod.conversar('otra cosa', 'hilo-borrable')

        assert 'algo memorable' not in str(modelo.vistas[-1])


class TestElFrenoDeVerdad:
    def test_un_modelo_que_nunca_para_se_corta_y_lo_dice(self, grafo_falso, monkeypatch):
        """Sin tope, un agente confundido es una fuga de dinero."""
        from apps.samples import agente_grafo as mod

        monkeypatch.setattr(mod, 'ejecutar', lambda n, a: {'n': 1})
        # Guion infinito: siempre pide otra herramienta.
        guion = [ia_msg(tool_calls=[llamada('CROMOSOMAS_PARA_REVISION')])
                 for _ in range(50)]
        grafo_falso(guion)

        r = mod.conversar('bucle', 'hilo-tope')

        assert r.completado is False
        assert any(p['tipo'] == 'corte' for p in r.traza.pasos)
