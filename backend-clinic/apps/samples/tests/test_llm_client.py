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


NORMAL = (
    'El análisis citogenético muestra un complemento cromosómico femenino normal, '
    'sin alteraciones numéricas ni estructurales detectables al nivel de resolución '
    'empleado. Se recomienda correlación clínica.'
)
TRISOMIA = (
    'El estudio revela la presencia de un cromosoma 21 adicional, compatible con '
    'trisomía 21 (+21) en todas las metafases analizadas. El hallazgo requiere '
    'correlación clínica y asesoramiento genético.'
)


class TestGeneracionNarrativa:
    def test_camino_feliz_devuelve_texto_y_metricas(self, monkeypatch):
        _fake_sdk(monkeypatch, text=NORMAL)
        out = _client().generate_narrative('46,XX', 'sangre', 'CHN-001', {'X': 2})
        assert 'normal' in out['text'].lower()
        assert out['model'] == 'llama3.2:3b'
        assert out['tokens'] == 120
        assert out['latency_ms'] >= 0

    def test_acepta_anomalia_que_si_esta_en_el_iscn(self, monkeypatch):
        _fake_sdk(monkeypatch, text=TRISOMIA)
        out = _client().generate_narrative('47,XY,+21', 'sangre', 'CHN-002', {'21': 3})
        assert '+21' in out['text']

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
        texto = (
            'Se observa una deleción del brazo corto, del(5p), en el material '
            'analizado, hallazgo que requiere correlación clínica posterior.'
        )
        _fake_sdk(monkeypatch, text=texto)
        with pytest.raises(LlmServiceError, match='alucinación'):
            _client().generate_narrative('46,XX', 'sangre', 'CHN-005', {})

    def test_rechaza_anomalia_de_otro_cromosoma(self, monkeypatch):
        """Confundir +18 con +21 cambia el diagnóstico: Edwards vs Down."""
        texto = (
            'El estudio muestra un cromosoma adicional, +18, compatible con '
            'trisomía 18 en las metafases analizadas. Requiere correlación clínica.'
        )
        _fake_sdk(monkeypatch, text=texto)
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

    @pytest.mark.parametrize('texto', ['', 'Normal.', 'x' * 3000])
    def test_rechaza_longitud_fuera_de_rango(self, monkeypatch, texto):
        _fake_sdk(monkeypatch, text=texto)
        with pytest.raises(LlmServiceError, match='longitud'):
            _client().generate_narrative('46,XX', 'sangre', 'CHN-008', {})

    def test_none_del_modelo_no_revienta(self, monkeypatch):
        _fake_sdk(monkeypatch, text=None)
        with pytest.raises(LlmServiceError, match='longitud'):
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
