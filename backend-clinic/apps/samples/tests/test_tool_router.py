"""Tests del enrutador de herramientas — tool calling (Módulo 6, semana 3).

La propiedad que se protege es una sola: **el modelo elige la herramienta, el
código produce la respuesta**. De ahí sale el test más importante de este
archivo — el escenario 1 y el 2 deben devolver EXACTAMENTE los mismos datos,
aunque uno resuelva sin modelo y el otro pasando por él.

El LLM se sustituye por dobles: los cuatro escenarios se verifican sin Ollama.
"""
from decimal import Decimal

import pytest

from apps.samples import tool_router
from apps.samples.models import Chromosome, Karyotype, Sample, SampleStatus
from apps.samples.tool_router import responder
from apps.samples.tools import CATALOGO, LIMITE_FILAS, buscar_por_palabra_clave

pytestmark = pytest.mark.django_db

# Las tres preguntas de la consigna: la misma de fondo en 1/2/4, otra en el 3.
CONTROLADA = '¿Qué cromosomas están naranjas?'
SINONIMO = '¿Cuáles necesitan que el analista los mire de nuevo?'
FUERA_DE_ALCANCE = '¿Cuál es el presupuesto del laboratorio para 2027?'


@pytest.fixture(autouse=True)
def _ia_encendida(settings):
    settings.CLINIC_LLM_ENABLED = True


@pytest.fixture
def caso_con_naranjas(analyst_user):
    """Un caso con 3 cromosomas bajo el umbral, sin resolver (RN-02)."""
    sample = Sample.objects.create(
        chn_code='CHN-TOOLS-0001', analyst=analyst_user,
        status=SampleStatus.READY, sample_type='sangre',
    )
    karyotype = Karyotype.objects.create(sample=sample)
    for orden, (clase, conf) in enumerate([('9', '0.612'), ('13', '0.704'), ('21', '0.783')]):
        Chromosome.objects.create(
            karyotype=karyotype, predicted_class=clase, position_index=0,
            confidence_score=Decimal(conf), resolution_status='PENDING', order=orden,
        )
    return sample


def _mock_seleccion(monkeypatch, herramienta: str, motivo: str = 'elegida por significado'):
    monkeypatch.setattr(tool_router, '_elegir_con_modelo', lambda p: (herramienta, motivo))


def _explota_si_llaman(monkeypatch):
    """Falla el test si el código llega al modelo cuando no debería."""
    def explota(_pregunta):
        raise AssertionError('no debió llamarse al modelo')
    monkeypatch.setattr(tool_router, '_elegir_con_modelo', explota)


class TestEscenario1Controlado:
    """La pregunta usa el vocabulario del catálogo: se resuelve sin modelo."""

    def test_resuelve_por_palabra_clave(self, monkeypatch, caso_con_naranjas):
        _explota_si_llaman(monkeypatch)
        r = responder(CONTROLADA)

        assert r.camino == 'KEYWORD'
        assert r.tool == 'CROMOSOMAS_PARA_REVISION'
        assert len(r.filas) == 3

    def test_declara_de_qué_tabla_salió_el_dato(self, monkeypatch, caso_con_naranjas):
        """Sin procedencia, un usuario no distingue un dato consultado de uno
        inventado."""
        _explota_si_llaman(monkeypatch)
        assert responder(CONTROLADA).source == 'clinic_chromosomes'

    def test_no_llama_al_modelo(self, monkeypatch, caso_con_naranjas):
        llamadas = []
        monkeypatch.setattr(tool_router, '_elegir_con_modelo',
                            lambda p: llamadas.append(p) or ('NINGUNA', ''))
        responder(CONTROLADA)
        assert llamadas == []

    def test_devuelve_los_datos_reales_de_la_base(self, monkeypatch, caso_con_naranjas):
        _explota_si_llaman(monkeypatch)
        clases = {f['clase'] for f in responder(CONTROLADA).filas}
        assert clases == {'9', '13', '21'}


class TestEscenario2Sinonimo:
    """El dato existe pero la palabra no está en el catálogo: escala al modelo."""

    def test_ninguna_palabra_clave_coincide(self):
        # Si esto falla, el escenario 2 dejaría de probar lo que dice probar.
        assert buscar_por_palabra_clave(SINONIMO) is None

    def test_el_modelo_elige_la_herramienta(self, monkeypatch, caso_con_naranjas):
        _mock_seleccion(monkeypatch, 'CROMOSOMAS_PARA_REVISION')
        r = responder(SINONIMO)

        assert r.camino == 'LLM'
        assert r.tool == 'CROMOSOMAS_PARA_REVISION'

    def test_devuelve_EXACTAMENTE_lo_mismo_que_el_escenario_1(self, monkeypatch, caso_con_naranjas):
        """El test central del módulo: el camino cambia, los datos no.

        Si difirieran, significaría que el modelo influyó en la respuesta — que
        es justo lo que esta arquitectura prohíbe.
        """
        _explota_si_llaman(monkeypatch)
        por_palabra = responder(CONTROLADA)

        _mock_seleccion(monkeypatch, 'CROMOSOMAS_PARA_REVISION')
        por_modelo = responder(SINONIMO)

        assert por_palabra.filas == por_modelo.filas
        assert por_palabra.tool == por_modelo.tool
        assert por_palabra.source == por_modelo.source
        assert por_palabra.camino != por_modelo.camino     # el camino sí difiere

    def test_expone_por_qué_el_modelo_eligió_esa(self, monkeypatch, caso_con_naranjas):
        _mock_seleccion(monkeypatch, 'CROMOSOMAS_PARA_REVISION', 'requiere revisión manual')
        assert responder(SINONIMO).motivo == 'requiere revisión manual'


class TestEscenario3FueraDeAlcance:
    """Ninguna herramienta responde eso. No es un error."""

    def test_dice_que_no_sabe(self, monkeypatch):
        _mock_seleccion(monkeypatch, 'NINGUNA')
        r = responder(FUERA_DE_ALCANCE)

        assert r.camino == 'SIN_MATCH'
        assert r.tool is None
        assert r.filas == []

    def test_publica_lo_que_sí_puede_responder(self, monkeypatch):
        """Decir 'no sé' sin decir qué sí se sabe deja al usuario sin salida."""
        _mock_seleccion(monkeypatch, 'NINGUNA')
        catalogo = responder(FUERA_DE_ALCANCE).catalogo

        assert catalogo is not None
        assert len(catalogo) == len(CATALOGO)
        assert all('fuente' in c for c in catalogo)

    def test_no_inventa_datos(self, monkeypatch):
        _mock_seleccion(monkeypatch, 'NINGUNA')
        assert responder(FUERA_DE_ALCANCE).filas == []

    def test_un_nombre_inexistente_se_trata_como_NINGUNA(self, monkeypatch):
        """El modelo puede ignorar el enum pese a `strict`: no se confía en él."""
        _mock_seleccion(monkeypatch, 'HERRAMIENTA_QUE_NO_EXISTE')
        assert responder(FUERA_DE_ALCANCE).camino == 'SIN_MATCH'


class TestEscenario4ModeloApagado:
    """El feature flag apagado: la respuesta la sigue produciendo el código."""

    def test_los_datos_salen_igual(self, monkeypatch, settings, caso_con_naranjas):
        settings.CLINIC_LLM_ENABLED = False
        _explota_si_llaman(monkeypatch)
        r = responder(CONTROLADA)

        assert r.camino == 'KEYWORD'
        assert len(r.filas) == 3

    def test_respuesta_idéntica_a_la_del_escenario_1(self, monkeypatch, settings, caso_con_naranjas):
        _explota_si_llaman(monkeypatch)
        con_ia = responder(CONTROLADA)

        settings.CLINIC_LLM_ENABLED = False
        sin_ia = responder(CONTROLADA)

        assert con_ia.filas == sin_ia.filas
        assert con_ia.tool == sin_ia.tool
        assert con_ia.source == sin_ia.source

    def test_el_sinónimo_deja_de_funcionar(self, monkeypatch, settings, caso_con_naranjas):
        """La medición que pide la consigna: esto es lo que aporta la IA.

        Con el flag apagado la pregunta del escenario 2 cae en 'no sé' — y eso
        está bien, es la diferencia medida entre tener modelo y no tenerlo.
        """
        settings.CLINIC_LLM_ENABLED = False
        _explota_si_llaman(monkeypatch)
        r = responder(SINONIMO)

        assert r.camino == 'SIN_MATCH'
        assert 'desactivada' in r.mensaje


class TestDegradaciónYBordes:
    def test_el_modelo_caído_no_rompe_la_consulta(self, monkeypatch, caso_con_naranjas):
        """RN-07: si el LLM no responde, el sistema sigue usable."""
        def cae(_p):
            raise ConnectionError('ollama caído')
        monkeypatch.setattr(tool_router, '_elegir_con_modelo', cae)

        r = responder(SINONIMO)
        assert r.camino == 'SIN_MATCH'
        assert r.catalogo is not None

    def test_el_modelo_caído_no_afecta_al_camino_por_palabra_clave(self, monkeypatch, caso_con_naranjas):
        def cae(_p):
            raise ConnectionError('ollama caído')
        monkeypatch.setattr(tool_router, '_elegir_con_modelo', cae)

        assert responder(CONTROLADA).camino == 'KEYWORD'

    @pytest.mark.parametrize('pregunta', ['', '   ', None])
    def test_consulta_vacía(self, pregunta):
        assert responder(pregunta).camino == 'SIN_MATCH'

    def test_sin_resultados_no_es_lo_mismo_que_sin_herramienta(self, monkeypatch):
        """Base vacía: la herramienta corrió y no encontró nada. Distinto de
        'no sé qué herramienta usar'."""
        _explota_si_llaman(monkeypatch)
        r = responder(CONTROLADA)

        assert r.camino == 'KEYWORD'
        assert r.tool == 'CROMOSOMAS_PARA_REVISION'
        assert r.filas == []
        assert r.catalogo is None

    def test_gana_la_palabra_clave_más_específica(self):
        tool = buscar_por_palabra_clave('quiero ver los casos pendiente de firma de hoy')
        assert tool is not None and tool.name == 'CASOS_PENDIENTES_FIRMA'


class TestCatálogo:
    def test_toda_herramienta_declara_su_tabla(self):
        assert all(t.source for t in CATALOGO)

    def test_los_nombres_son_únicos(self):
        nombres = [t.name for t in CATALOGO]
        assert len(nombres) == len(set(nombres))

    def test_ninguna_palabra_clave_está_repetida_entre_herramientas(self):
        """Una palabra en dos herramientas haría el enrutado ambiguo."""
        vistas: dict[str, str] = {}
        for tool in CATALOGO:
            for kw in tool.keywords:
                assert kw not in vistas, f'"{kw}" está en {vistas.get(kw)} y {tool.name}'
                vistas[kw] = tool.name

    def test_toda_herramienta_es_ejecutable(self):
        for tool in CATALOGO:
            assert isinstance(tool.run(), list)


class TestEndpoint:
    """POST /api/clinic/tools/query/ - la consigna pide el tool calling detras
    de un interruptor, expuesto en el sistema, no solo en un comando."""

    URL = '/api/clinic/tools/query/'

    def test_responde_con_la_procedencia_del_dato(self, monkeypatch, analyst_client, caso_con_naranjas):
        _explota_si_llaman(monkeypatch)
        r = analyst_client.post(self.URL, {'pregunta': CONTROLADA}, format='json')

        assert r.status_code == 200
        assert r.data['camino'] == 'KEYWORD'
        assert r.data['tool'] == 'CROMOSOMAS_PARA_REVISION'
        assert r.data['source'] == 'clinic_chromosomes'
        assert len(r.data['filas']) == 3

    def test_fuera_de_alcance_es_200_no_error(self, monkeypatch, analyst_client):
        """Preguntar algo que el sistema no sabe no es culpa del cliente."""
        _mock_seleccion(monkeypatch, 'NINGUNA')
        r = analyst_client.post(self.URL, {'pregunta': FUERA_DE_ALCANCE}, format='json')

        assert r.status_code == 200
        assert r.data['camino'] == 'SIN_MATCH'
        assert r.data['catalogo']

    def test_con_la_ia_apagada_sigue_respondiendo(self, monkeypatch, settings, analyst_client, caso_con_naranjas):
        settings.CLINIC_LLM_ENABLED = False
        _explota_si_llaman(monkeypatch)
        r = analyst_client.post(self.URL, {'pregunta': CONTROLADA}, format='json')

        assert r.status_code == 200
        assert len(r.data['filas']) == 3

    def test_get_publica_el_catalogo(self, analyst_client):
        r = analyst_client.get(self.URL)

        assert r.status_code == 200
        assert len(r.data['herramientas']) == len(CATALOGO)

    def test_anonimo_rechazado(self):
        from rest_framework.test import APIClient
        r = APIClient().post(self.URL, {'pregunta': CONTROLADA}, format='json')
        assert r.status_code in (401, 403)


class TestTruncado:
    """Una lista truncada que se presenta como completa esconde trabajo.

    Las consultas cortan en LIMITE_FILAS. Si la respuesta dice «50 resultado(s)»
    y hay 100 cromosomas naranjas, el analista cree haber visto toda su cola de
    revisión cuando le falta la mitad. Se encontró con datos reales: 100
    naranjas en la base, 50 en la respuesta, sin ninguna advertencia.
    """

    def test_por_debajo_del_tope_no_advierte(self):
        assert tool_router._mensaje_resultados([{}] * 7) == '7 resultado(s).'

    def test_en_el_tope_advierte_que_puede_haber_mas(self):
        mensaje = tool_router._mensaje_resultados([{}] * LIMITE_FILAS)

        assert 'puede haber más' in mensaje
        assert str(LIMITE_FILAS) in mensaje

    def test_sin_filas_no_habla_de_truncado(self):
        assert 'puede haber más' not in tool_router._mensaje_resultados([])
