"""Reintentos explícitos y límite de concurrencia del LLM (DD-AUD-001 F2, issue #3).

Hallazgo CON-04 de la auditoría de M8: el SDK de OpenAI reintentaba 2 veces por
defecto también tras un timeout de 240 s (~12 min por petición), y no había
límite de llamadas simultáneas a un modelo que tarda 30–120 s por respuesta.
"""
from __future__ import annotations

import re
import sys
import threading
import time
import types
from pathlib import Path

import pytest

from apps.samples import llm_conexion
from apps.samples.llm_conexion import LimiteLlm, LlmOcupado

APPS = Path(__file__).resolve().parents[2]       # backend-clinic/apps


def _sdk_falso(monkeypatch, llamadas: list, inits: list):
    """Módulo `openai` falso: cuenta las llamadas a `create` y los kwargs del cliente."""
    class Completions:
        def create(self, **kwargs):
            llamadas.append(kwargs)
            msg = types.SimpleNamespace(content='{}', tool_calls=None)
            return types.SimpleNamespace(choices=[types.SimpleNamespace(message=msg)],
                                         usage=None)

    class OpenAI:
        def __init__(self, **kwargs):
            inits.append(kwargs)
            self.chat = types.SimpleNamespace(completions=Completions())

    mod = types.ModuleType('openai')
    mod.OpenAI = OpenAI
    monkeypatch.setitem(sys.modules, 'openai', mod)


@pytest.fixture
def limite_lleno(monkeypatch):
    """Un límite de una plaza, ya ocupada, con espera mínima."""
    limite = LimiteLlm(maximo=1, espera_s=0.05)
    monkeypatch.setattr(llm_conexion, 'limite_llm', limite)
    with limite.turno():
        yield limite


# ---------------------------------------------------------------- reintentos

class TestReintentosExplicitos:
    @pytest.mark.parametrize('reintentos', [0, 1])
    def test_el_cliente_del_sdk_lleva_max_retries_de_settings(self, monkeypatch, settings, reintentos):
        settings.CLINIC_LLM_MAX_RETRIES = reintentos
        inits = []
        _sdk_falso(monkeypatch, [], inits)
        llm_conexion.crear_cliente_llm()
        assert inits[0]['max_retries'] == reintentos

    def test_por_defecto_no_se_reintenta(self, settings):
        # El valor de producción: un reintento tras 240 s solo duplica la espera.
        assert settings.CLINIC_LLM_MAX_RETRIES == 0

    def test_el_modelo_de_langchain_lleva_el_mismo_max_retries(self, monkeypatch, settings):
        settings.CLINIC_LLM_MAX_RETRIES = 0
        visto = {}

        class ChatOpenAI:
            def __init__(self, **kwargs):
                visto.update(kwargs)

        mod = types.ModuleType('langchain_openai')
        mod.ChatOpenAI = ChatOpenAI
        monkeypatch.setitem(sys.modules, 'langchain_openai', mod)
        llm_conexion.crear_modelo_chat(temperature=0)
        assert visto['max_retries'] == 0
        assert visto['temperature'] == 0

    def test_ningun_modulo_construye_su_propio_cliente(self):
        # Si alguien vuelve a escribir `OpenAI(` o `ChatOpenAI(` fuera de
        # llm_conexion, se salta max_retries sin que nada lo avise.
        patron = re.compile(r'\b(?:Chat)?OpenAI\(')
        culpables = [
            str(p.relative_to(APPS))
            for p in APPS.rglob('*.py')
            if 'tests' not in p.parts and p.name != 'llm_conexion.py'
            and patron.search(p.read_text(encoding='utf-8'))
        ]
        assert culpables == []


# ---------------------------------------------------------------- límite

class TestLimiteLlm:
    def test_rechaza_cuando_no_hay_plaza(self, limite_lleno):
        t0 = time.perf_counter()
        with pytest.raises(LlmOcupado):
            with limite_lleno.turno():
                pass
        assert time.perf_counter() - t0 < 1.0     # rechazo rápido, no cola invisible

    def test_deja_pasar_hasta_el_maximo_a_la_vez(self):
        limite = LimiteLlm(maximo=2, espera_s=0.05)
        dentro, salir = threading.Barrier(3), threading.Event()

        def ocupar():
            with limite.turno():
                dentro.wait()
                salir.wait()

        hilos = [threading.Thread(target=ocupar) for _ in range(2)]
        for h in hilos:
            h.start()
        dentro.wait()                            # las dos plazas están ocupadas
        try:
            with pytest.raises(LlmOcupado):
                with limite.turno():
                    pass
        finally:
            salir.set()
            for h in hilos:
                h.join()
        with limite.turno():                     # liberadas: vuelve a haber hueco
            pass

    def test_libera_la_plaza_aunque_falle_la_llamada(self):
        limite = LimiteLlm(maximo=1, espera_s=0.05)
        with pytest.raises(RuntimeError):
            with limite.turno():
                raise RuntimeError('timeout del modelo')
        with limite.turno():
            pass

    @pytest.mark.parametrize('maximo, espera', [(0, 5), (-1, 5), (1, -0.1)])
    def test_rechaza_configuraciones_invalidas(self, maximo, espera):
        with pytest.raises(ValueError):
            LimiteLlm(maximo, espera)


# ---------------------------------------------------- los cinco llamadores

class TestLosLlamadoresRespetanElLimite:
    """Con las plazas llenas, ningún llamador llega a tocar el modelo."""

    def test_narrativa_degrada_sin_abrir_el_circuito(self, monkeypatch, settings, limite_lleno):
        from apps.samples.llm_client import LlmClient, LlmServiceError
        settings.CLINIC_LLM_ENABLED = True
        llamadas = []
        _sdk_falso(monkeypatch, llamadas, [])
        cliente = LlmClient(base_url='http://llm', model='m', timeout=1, threshold=1, cooldown=60)

        with pytest.raises(LlmServiceError, match='ocupado'):
            cliente.generate_narrative('46,XY', 'sangre', 'CHN-1', {})

        assert llamadas == []
        # Estar ocupado no es un fallo del servicio: con threshold=1 un solo
        # fallo lo abriría.
        assert not cliente._circuit_open()

    def test_enrutador(self, monkeypatch, limite_lleno):
        from apps.samples import tool_router
        llamadas = []
        _sdk_falso(monkeypatch, llamadas, [])
        with pytest.raises(LlmOcupado):
            tool_router._elegir_con_modelo('¿cuántos casos hay?')
        assert llamadas == []

    def test_rag(self, monkeypatch, settings, limite_lleno):
        from apps.samples import rag_qa
        settings.CLINIC_LLM_ENABLED = True
        llamadas = []
        _sdk_falso(monkeypatch, llamadas, [])
        # Un fragmento recuperado y aprobado: el flujo llega hasta el juez.
        fragmento = types.SimpleNamespace(similitud=0.9, fragmento=types.SimpleNamespace(fuente='x'))
        monkeypatch.setattr(rag_qa, 'indice', lambda: types.SimpleNamespace(
            buscar=lambda *a, **kw: [fragmento]))
        monkeypatch.setattr(rag_qa, 'filtrar_fuentes', lambda r: (r, []))

        respuesta = rag_qa.responder_documental('¿qué es un cariotipo?')

        assert llamadas == []
        assert respuesta.responde is False
        assert 'ocupado' in respuesta.motivo

    def test_agente(self, monkeypatch, limite_lleno):
        from apps.samples import agente
        llamadas = []
        _sdk_falso(monkeypatch, llamadas, [])
        with pytest.raises(agente.AgenteError, match='ocupado'):
            agente.ejecutar_agente('hola', schemas=[], ejecutar=lambda n, a: {},
                                   instrucciones='x')
        assert llamadas == []

    def test_agente_con_memoria(self, monkeypatch, settings, tmp_path, limite_lleno):
        from apps.samples import agente, agente_grafo
        settings.CLINIC_LLM_ENABLED = True
        monkeypatch.setattr(agente_grafo, 'RUTA_MEMORIA', tmp_path / 'memoria.sqlite3')
        invocado = []

        class Modelo:
            def invoke(self, mensajes):
                invocado.append(mensajes)

        monkeypatch.setattr(agente_grafo, '_modelo', lambda: Modelo())
        monkeypatch.setattr(agente_grafo, '_grafo', None)
        monkeypatch.setattr(agente_grafo, '_conexion', None)

        with pytest.raises(agente.AgenteError, match='ocupado'):
            agente_grafo.conversar('hola', thread_id='t-ocupado')
        assert invocado == []
