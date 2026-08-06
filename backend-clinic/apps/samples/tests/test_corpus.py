"""Tests del corpus clínico que fundamenta la narrativa (ADR-0028).

La propiedad central es la de D1: la búsqueda es **determinística por clave**,
no vectorial. De ahí salen las dos garantías que se prueban acá — precisión
exacta y trazabilidad de qué entrada fundamentó cada informe.

Función pura sobre datos declarativos: no necesitan base, Django ni Ollama.
"""
import pytest

from apps.samples.corpus import (
    CORPUS,
    buscar_contexto,
    formatear_para_prompt,
    resumen_auditoria,
)


class TestBusquedaPorClave:
    """ADR-0028 D1 — coincidencia exacta, no similitud."""

    @pytest.mark.parametrize('iscn, claves', [
        ('47,XY,+21',      ['XY', '+21']),      # Down
        ('47,XX,+18',      ['XX', '+18']),      # Edwards
        ('47,XY,+13',      ['XY', '+13']),      # Patau
        ('45,X',           ['X']),              # Turner
        ('47,XXY',         ['XXY']),            # Klinefelter
        ('48,XX,+13,+21',  ['XX', '+13', '+21']),
        ('45,XX,-22',      ['XX', '-22']),
        ('46,XX',          ['XX']),
    ])
    def test_recupera_lo_que_corresponde(self, iscn, claves):
        assert [e.clave for e in buscar_contexto(iscn)] == claves

    def test_el_sexo_va_primero(self):
        """Mismo orden que ISCN §4.3 usa para escribir: sexuales antes que
        autosómicas. Un orden distinto le daría al modelo un contexto cuya
        secuencia no se corresponde con el ISCN que está leyendo."""
        assert buscar_contexto('48,XX,+13,+21')[0].clave == 'XX'

    def test_una_anomalia_repetida_no_duplica_el_contexto(self):
        """Tetrasomía («+21,+21») aporta la misma explicación una sola vez."""
        assert [e.clave for e in buscar_contexto('48,XX,+21,+21')] == ['XX', '+21']

    def test_solo_mira_la_primera_linea_del_mosaico(self):
        """Las líneas de un mosaico describen poblaciones distintas; fundir sus
        anomalías daría un contexto que no corresponde a ninguna."""
        assert [e.clave for e in buscar_contexto('mos 47,XXY[10]/46,XY[20]')] == ['XXY']


class TestCoberturaParcial:
    """ADR-0028 D3 — el corpus no es exhaustivo y no debe pretenderlo."""

    def test_una_anomalia_sin_entrada_no_rompe_la_busqueda(self):
        """Se recupera lo que sí se conoce y se ignora el resto: bloquear la
        narrativa por un vacío documental convertiría falta de documentación en
        fallo clínico, y RN-07 lo prohíbe."""
        encontradas = buscar_contexto('46,XY,inv(9)(p12q13)')
        assert [e.clave for e in encontradas] == ['XY']

    @pytest.mark.parametrize('iscn', ['', '   ', 'basura', None])
    def test_un_iscn_irreconocible_devuelve_vacio_sin_lanzar(self, iscn):
        assert buscar_contexto(iscn) == []


class TestEstadoDeRevision:
    """ADR-0028 D2 — el estado de revisión no es decorativo."""

    def test_las_entradas_semilla_estan_sin_revisar(self):
        """Las redactó un asistente de IA, no un clínico. Marcarlas como
        revisadas sería exactamente el fallo que este módulo combate: dar
        apariencia de autoridad verificada a algo que nadie validó."""
        assert all(not e.revisada for e in CORPUS.values())

    def test_la_auditoria_cuenta_lo_que_no_esta_firmado(self):
        """Es el dato que permite rehacer los informes afectados si una entrada
        resulta incorrecta."""
        resumen = resumen_auditoria(buscar_contexto('47,XY,+21'))
        assert resumen['corpus_entradas'] == ['XY', '+21']
        assert resumen['corpus_sin_revisar'] == 2

    def test_la_auditoria_de_un_caso_sin_corpus_es_cero(self):
        assert resumen_auditoria([]) == {'corpus_entradas': [], 'corpus_sin_revisar': 0}


class TestProcedencia:
    """Sin fuente, una entrada es indistinguible de una alucinación escrita a
    mano — que es justo lo que este corpus existe para evitar."""

    def test_toda_entrada_cita_su_fuente(self):
        assert all(e.fuente for e in CORPUS.values())

    def test_toda_entrada_tiene_nombre_y_descripcion(self):
        assert all(e.nombre and e.descripcion for e in CORPUS.values())

    def test_la_clave_coincide_con_su_indice(self):
        assert all(clave == e.clave for clave, e in CORPUS.items())


class TestFormatoParaPrompt:
    def test_se_rotula_como_referencia_no_como_texto_a_copiar(self):
        """ADR-0028 D3: el modelo redacta SOBRE el material, no lo devuelve."""
        texto = formatear_para_prompt(buscar_contexto('47,XY,+21'))
        assert 'no lo copies' in texto.lower()

    def test_incluye_la_descripcion_de_lo_recuperado(self):
        texto = formatear_para_prompt(buscar_contexto('47,XY,+21'))
        assert 'Trisomía 21' in texto and 'cromosoma 21' in texto

    def test_sin_entradas_no_ensucia_el_prompt(self):
        assert formatear_para_prompt([]) == ''


class TestCorpusEnElPrompt:
    """El cableado: lo recuperado tiene que llegar al modelo."""

    def _prompt(self, iscn):
        from apps.samples.llm_client import llm_client
        return llm_client._build_prompt(iscn, 'sangre', 'CHN-T', {})

    def test_la_referencia_llega_al_prompt(self):
        assert 'Trisomía 21' in self._prompt('47,XY,+21')

    def test_el_iscn_sigue_presente(self):
        """El corpus complementa el dato clínico, no lo reemplaza (D3)."""
        assert '47,XY,+21' in self._prompt('47,XY,+21')

    def test_sin_corpus_el_prompt_sigue_siendo_valido(self):
        prompt = self._prompt('basura')
        assert 'REFERENCIA' not in prompt
        assert 'Redacta el párrafo interpretativo' in prompt

    def test_el_prompt_no_lleva_pii(self):
        """ADR-0024 D6 sigue vigente: el corpus no abre una vía para filtrar
        datos de paciente."""
        prompt = self._prompt('47,XY,+21')
        assert 'CHN-T' in prompt          # el seudónimo sí
        for pii in ('nombre', 'documento', 'nacimiento', 'teléfono'):
            assert pii not in prompt.lower()
