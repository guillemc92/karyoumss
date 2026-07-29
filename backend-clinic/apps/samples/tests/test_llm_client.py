"""Tests del cliente LLM local (ADR-0024).

El foco está en la defensa que hace segura la integración: **el LLM no puede
introducir una anomalía que el ISCN determinístico no contiene**. Un texto que
afirme una trisomía inexistente es un diagnóstico falso; por eso la validación se
prueba con más detalle que el camino feliz.

No requieren Ollama corriendo: el SDK se sustituye por dobles.
"""
import sys
import types

import pytest

from apps.samples.llm_client import LlmClient, LlmServiceError


@pytest.fixture(autouse=True)
def _llm_encendido(settings):
    """El LLM está apagado por defecto (RN-07); estos tests lo encienden."""
    settings.CLINIC_LLM_ENABLED = True


def _client(**overrides):
    defaults = dict(
        base_url='http://localhost:11434/v1',
        model='llama3.2:3b',
        timeout=1.0,
        threshold=3,
        cooldown=60,
    )
    defaults.update(overrides)
    return LlmClient(**defaults)


def _fake_sdk(monkeypatch, *, text=None, raises=None, tokens=120, capture=None):
    """Instala un módulo `openai` falso que devuelve `text` o lanza `raises`."""
    class FakeCompletions:
        def create(self, **kwargs):
            if capture is not None:
                capture.update(kwargs)
            if raises is not None:
                raise raises
            msg = types.SimpleNamespace(content=text)
            return types.SimpleNamespace(
                choices=[types.SimpleNamespace(message=msg)],
                usage=types.SimpleNamespace(total_tokens=tokens),
            )

    class FakeOpenAI:
        def __init__(self, **kwargs):
            if capture is not None:
                capture['_init'] = kwargs
            self.chat = types.SimpleNamespace(completions=FakeCompletions())

    mod = types.ModuleType('openai')
    mod.OpenAI = FakeOpenAI
    monkeypatch.setitem(sys.modules, 'openai', mod)


# El cliente ahora pide un OBJETO tipado, no prosa: los dobles devuelven JSON.
NORMAL = (
    '{"hallazgo": "No se observan alteraciones numericas ni estructurales.",'
    ' "interpretacion": "El complemento cromosomico es normal. El resultado '
    'requiere correlacion clinica.",'
    ' "es_normal": true, "anomalias_citadas": [], "nivel_confianza": "alta"}'
)
TRISOMIA = (
    '{"hallazgo": "Se observa un cromosoma 21 adicional en las metafases.",'
    ' "interpretacion": "El hallazgo es compatible con trisomia 21. Requiere '
    'correlacion clinica y asesoramiento genetico.",'
    ' "es_normal": false, "anomalias_citadas": ["+21"], "nivel_confianza": "alta"}'
)
ESTRUCTURAL = (
    '{"hallazgo": "Se observa una delecion en el brazo corto del cromosoma 5.",'
    ' "interpretacion": "El hallazgo sugiere del(5p). Requiere correlacion clinica.",'
    ' "es_normal": false, "anomalias_citadas": ["del(5p)"], "nivel_confianza": "media"}'
)
TRISOMIA_18 = TRISOMIA.replace('"+21"', '"+18"').replace('21 adicional', '18 adicional')


class TestGeneracionNarrativa:
    def test_camino_feliz_devuelve_texto_y_metricas(self, monkeypatch):
        _fake_sdk(monkeypatch, text=NORMAL)
        out = _client().generate_narrative('46,XX', 'sangre', 'CHN-001', {'X': 2})
        assert 'normal' in out['text'].lower()
        assert out['structured']['es_normal'] is True
        assert out['model'] == 'llama3.2:3b'
        assert out['tokens'] == 120
        assert out['latency_ms'] >= 0

    def test_acepta_anomalia_que_si_esta_en_el_iscn(self, monkeypatch):
        _fake_sdk(monkeypatch, text=TRISOMIA)
        out = _client().generate_narrative('47,XY,+21', 'sangre', 'CHN-002', {'21': 3})
        assert out['structured']['anomalias_citadas'] == ['+21']

    def test_apagado_por_settings_no_llama_al_modelo(self, monkeypatch, settings):
        _fake_sdk(monkeypatch, text=NORMAL)
        settings.CLINIC_LLM_ENABLED = False
        with pytest.raises(LlmServiceError, match='llm_disabled'):
            _client().generate_narrative('46,XX', 'sangre', 'CHN-003', {})


class TestDefensaContraAlucinacion:
    """ADR-0024 D4.1 — el núcleo de seguridad de esta integración."""

    def test_rechaza_trisomia_inventada(self, monkeypatch):
        """Un cariotipo normal narrado como trisomía 21 es un diagnóstico falso."""
        _fake_sdk(monkeypatch, text=TRISOMIA)
        with pytest.raises(LlmServiceError, match='alucinación'):
            _client().generate_narrative('46,XX', 'sangre', 'CHN-004', {})

    def test_rechaza_anomalia_estructural_inventada(self, monkeypatch):
        _fake_sdk(monkeypatch, text=ESTRUCTURAL)
        with pytest.raises(LlmServiceError, match='alucinación'):
            _client().generate_narrative('46,XX', 'sangre', 'CHN-005', {})

    def test_rechaza_anomalia_de_otro_cromosoma(self, monkeypatch):
        """Confundir +18 con +21 cambia el diagnóstico: Edwards vs Down."""
        _fake_sdk(monkeypatch, text=TRISOMIA_18)
        with pytest.raises(LlmServiceError, match='alucinación'):
            _client().generate_narrative('47,XY,+21', 'sangre', 'CHN-006', {})

    def test_una_alucinacion_no_abre_el_circuito(self, monkeypatch):
        """El modelo respondió: el servicio está sano. Abrir el circuito aquí
        dejaría fuera de servicio al LLM por un error de contenido."""
        _fake_sdk(monkeypatch, text=TRISOMIA)
        client = _client(threshold=1)
        with pytest.raises(LlmServiceError):
            client.generate_narrative('46,XX', 'sangre', 'CHN-007', {})
        assert not client._circuit_open()

    @pytest.mark.parametrize('crudo', [
        '',
        'El cariotipo es normal.',                       # prosa, no objeto
        '{"hallazgo": "corto", "interpretacion": "x", "es_normal": true}',  # muy corto
        '{"hallazgo": "' + 'x' * 400 + '"}',             # desbordado + incompleto
    ])
    def test_rechaza_lo_que_no_cumple_el_esquema(self, monkeypatch, crudo):
        _fake_sdk(monkeypatch, text=crudo)
        with pytest.raises(LlmServiceError, match='esquema'):
            _client().generate_narrative('46,XX', 'sangre', 'CHN-008', {})

    def test_none_del_modelo_no_revienta(self, monkeypatch):
        _fake_sdk(monkeypatch, text=None)
        with pytest.raises(LlmServiceError, match='esquema'):
            _client().generate_narrative('46,XX', 'sangre', 'CHN-009', {})


class TestSinPiiEnElPrompt:
    """ADR-0024 D6 — el prompt no puede llevar datos identificables."""

    def test_el_prompt_solo_lleva_chn_iscn_tipo_y_conteo(self, monkeypatch):
        capture = {}
        _fake_sdk(monkeypatch, text=NORMAL, capture=capture)
        _client().generate_narrative('46,XX', 'sangre', 'CHN-010', {'X': 2})

        enviado = ' '.join(m['content'] for m in capture['messages'])
        assert 'CHN-010' in enviado and '46,XX' in enviado
        # PII que vive cifrada en PatientVault (ADR-0016 D2): nunca en el prompt.
        for pii in ['Guillermo', 'Mamani', '12345678', '1990-05-12']:
            assert pii not in enviado

    def test_temperatura_baja_para_registro_clinico(self, monkeypatch):
        capture = {}
        _fake_sdk(monkeypatch, text=NORMAL, capture=capture)
        _client().generate_narrative('46,XX', 'sangre', 'CHN-011', {})
        assert capture['temperature'] <= 0.3


class TestDegradacionYCircuitBreaker:
    """RN-07 — la narrativa nunca puede bloquear la emisión del informe."""

    def test_servicio_caido_lanza_error_manejable(self, monkeypatch):
        _fake_sdk(monkeypatch, raises=ConnectionError('conexión rechazada'))
        with pytest.raises(LlmServiceError):
            _client().generate_narrative('46,XX', 'sangre', 'CHN-012', {})

    def test_el_circuito_abre_tras_el_umbral(self, monkeypatch):
        _fake_sdk(monkeypatch, raises=ConnectionError('caído'))
        client = _client(threshold=2)
        for _ in range(2):
            with pytest.raises(LlmServiceError):
                client.generate_narrative('46,XX', 'sangre', 'CHN-013', {})
        assert client._circuit_open()
        with pytest.raises(LlmServiceError, match='circuit_open'):
            client.generate_narrative('46,XX', 'sangre', 'CHN-013', {})

    def test_el_exito_resetea_los_fallos(self, monkeypatch):
        client = _client(threshold=3)
        _fake_sdk(monkeypatch, raises=ConnectionError('caído'))
        with pytest.raises(LlmServiceError):
            client.generate_narrative('46,XX', 'sangre', 'CHN-014', {})
        assert client._failures == 1
        _fake_sdk(monkeypatch, text=NORMAL)
        client.generate_narrative('46,XX', 'sangre', 'CHN-014', {})
        assert client._failures == 0

    def test_sin_sdk_instalado_degrada(self, monkeypatch):
        monkeypatch.setitem(sys.modules, 'openai', None)
        with pytest.raises(LlmServiceError, match='sdk_no_instalado'):
            _client().generate_narrative('46,XX', 'sangre', 'CHN-015', {})


JSON_OK = (
    '{"hallazgo": "Se observa un cromosoma 21 adicional en las metafases.",'
    ' "interpretacion": "El hallazgo es compatible con trisomia 21. Requiere '
    'correlacion clinica posterior.",'
    ' "es_normal": false, "anomalias_citadas": ["+21"], "nivel_confianza": "alta"}'
)
JSON_NORMAL = (
    '{"hallazgo": "No se observan alteraciones numericas ni estructurales.",'
    ' "interpretacion": "El cariotipo es normal. Requiere correlacion clinica.",'
    ' "es_normal": true, "anomalias_citadas": [], "nivel_confianza": "alta"}'
)


def _fake_sdk_secuencia(monkeypatch, respuestas, capture=None):
    """SDK falso que devuelve una respuesta distinta por intento."""
    estado = {'i': 0}

    class FakeCompletions:
        def create(self, **kwargs):
            if capture is not None:
                capture.setdefault('llamadas', []).append(kwargs)
            i = min(estado['i'], len(respuestas) - 1)
            estado['i'] += 1
            msg = types.SimpleNamespace(content=respuestas[i])
            return types.SimpleNamespace(
                choices=[types.SimpleNamespace(message=msg)],
                usage=types.SimpleNamespace(total_tokens=100),
            )

    class FakeOpenAI:
        def __init__(self, **kwargs):
            self.chat = types.SimpleNamespace(completions=FakeCompletions())

    mod = types.ModuleType('openai')
    mod.OpenAI = FakeOpenAI
    monkeypatch.setitem(sys.modules, 'openai', mod)
    return estado


class TestSalidaEstructurada:
    """ADR-0024 D4 — el LLM devuelve un objeto tipado, no prosa suelta."""

    def test_devuelve_el_objeto_validado(self, monkeypatch):
        _fake_sdk_secuencia(monkeypatch, [JSON_OK])
        out = _client().generate_narrative('47,XY,+21', 'sangre', 'CHN-1', {'21': 3})

        assert out['structured']['es_normal'] is False
        assert out['structured']['anomalias_citadas'] == ['+21']
        assert out['structured']['nivel_confianza'] == 'alta'
        assert out['intentos'] == 1

    def test_el_texto_plano_sale_del_objeto(self):
        """`narrative_draft` sigue siendo texto: el objeto se aplana al persistir."""
        _fake_sdk_secuencia_ = None
        out_text = None
        import json as _json
        from apps.samples.llm_schemas import NarrativaCariotipo
        n = NarrativaCariotipo.model_validate_json(JSON_OK)
        out_text = n.como_texto()
        assert n.hallazgo in out_text and n.interpretacion in out_text

    def test_pide_el_esquema_a_la_api(self, monkeypatch):
        capture = {}
        _fake_sdk_secuencia(monkeypatch, [JSON_OK], capture)
        _client().generate_narrative('47,XY,+21', 'sangre', 'CHN-2', {})

        enviado = capture['llamadas'][0]
        assert enviado['response_format']['type'] == 'json_schema'
        assert enviado['response_format']['json_schema']['strict'] is True


class TestCicloDeReintento:
    """El LLM es una función no confiable: si no cumple el contrato, se reintenta
    pasándole el error para que se autocorrija."""

    def test_reintenta_cuando_devuelve_prosa(self, monkeypatch):
        """Fallo típico: responde texto donde se pidió un objeto."""
        _fake_sdk_secuencia(monkeypatch, ['El cariotipo es normal.', JSON_OK])
        out = _client().generate_narrative('47,XY,+21', 'sangre', 'CHN-3', {})

        assert out['intentos'] == 2
        assert out['structured']['anomalias_citadas'] == ['+21']

    def test_reintenta_cuando_falta_un_campo(self, monkeypatch):
        incompleto = '{"hallazgo": "Se observa un cromosoma 21 adicional en la muestra."}'
        _fake_sdk_secuencia(monkeypatch, [incompleto, JSON_OK])
        assert _client().generate_narrative('47,XY,+21', 'sangre', 'CHN-4', {})['intentos'] == 2

    def test_reintenta_cuando_alucina(self, monkeypatch):
        """Objeto bien formado pero con una trisomía que el ISCN no tiene."""
        _fake_sdk_secuencia(monkeypatch, [JSON_OK, JSON_NORMAL])
        out = _client().generate_narrative('46,XX', 'sangre', 'CHN-5', {})

        assert out['intentos'] == 2
        assert out['structured']['es_normal'] is True

    def test_le_pasa_el_error_al_modelo(self, monkeypatch):
        """El reintento no repite el prompt: incluye qué falló, para corregirse."""
        capture = {}
        _fake_sdk_secuencia(monkeypatch, ['no es json', JSON_NORMAL], capture)
        _client().generate_narrative('46,XX', 'sangre', 'CHN-6', {})

        segunda = capture['llamadas'][1]['messages']
        assert len(segunda) > 2                       # creció con el intercambio
        ultimo = segunda[-1]['content']
        assert 'rechazada' in ultimo.lower()
        assert '46,XX' in ultimo                      # le recuerda el ISCN válido

    def test_agota_los_intentos_y_falla(self, monkeypatch):
        _fake_sdk_secuencia(monkeypatch, ['basura', 'sigue mal', 'peor'])
        with pytest.raises(LlmServiceError, match='tras 2 intentos'):
            _client().generate_narrative('46,XX', 'sangre', 'CHN-7', {})

    def test_agotar_intentos_no_abre_el_circuito(self, monkeypatch):
        """El modelo respondió: el servicio está sano, el contenido no sirve."""
        _fake_sdk_secuencia(monkeypatch, ['basura'])
        client = _client(threshold=1)
        with pytest.raises(LlmServiceError):
            client.generate_narrative('46,XX', 'sangre', 'CHN-8', {})
        assert not client._circuit_open()

    def test_acumula_los_tokens_de_todos_los_intentos(self, monkeypatch):
        """El costo real es la suma: un reintento no es gratis."""
        _fake_sdk_secuencia(monkeypatch, ['basura', JSON_NORMAL])
        assert _client().generate_narrative('46,XX', 'sangre', 'CHN-9', {})['tokens'] == 200

    def test_max_intentos_configurable(self, monkeypatch):
        estado = _fake_sdk_secuencia(monkeypatch, ['basura'])
        with pytest.raises(LlmServiceError, match='tras 4 intentos'):
            _client().generate_narrative('46,XX', 'sangre', 'CHN-10', {}, max_intentos=4)
        assert estado['i'] == 4
