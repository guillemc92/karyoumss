"""Unit tests de `responder_documental` — el paso de generacion del RAG.

## Por que este fichero existe

`rag_qa.py` estaba al **0 % de cobertura**: 62 sentencias sin una sola prueba,
y es el modulo que decide si el sistema responde una pregunta clinica o dice que
no sabe. Se detecto midiendo la cobertura en la Actividad 2 del Modulo 7.

## Los dobles estan en la FRONTERA, no dentro

Se sustituyen las dos unicas cosas que salen del proceso:

    indice()   -> disco  (el indice vectorial, 1.144 fragmentos)
    OpenAI     -> red    (el juez, Ollama en local)

Todo lo demas corre de verdad. Asi estas pruebas son deterministas y no gastan
tokens ni necesitan Ollama levantado — se pueden ejecutar en un pipeline.

## Lo que se afirma

Sobre todo, los caminos de DEGRADACION (RN-07): sin indice, sin modelo, con el
modelo caido o con el modelo devolviendo basura, el sistema **no revienta y no
inventa** — dice que no puede responder y explica por que.
"""
import pytest

from apps.samples import rag_qa
from apps.samples.rag_corpus import Fragmento
from apps.samples.rag_index import RagError, Resultado


def resultado(n: int, similitud: float = 0.7) -> Resultado:
    return Resultado(
        fragmento=Fragmento(texto='texto del fragmento %d' % n,
                            fuente='DOC_%d.md' % n,
                            seccion='seccion %d' % n,
                            orden=n),
        similitud=similitud,
    )


class IndiceFalso:
    """Doble del indice: no toca disco ni calcula embeddings."""

    def __init__(self, devuelve=None, lanza=None):
        self._devuelve = devuelve or []
        self._lanza = lanza
        self.llamadas = []

    def buscar(self, consulta, k=None, umbral=None):
        self.llamadas.append({'consulta': consulta, 'k': k, 'umbral': umbral})
        if self._lanza:
            raise self._lanza
        return list(self._devuelve)


class ModeloFalso:
    """Doble del cliente OpenAI: devuelve el JSON que se le diga, o revienta."""

    def __init__(self, contenido=None, lanza=None):
        self._contenido = contenido
        self._lanza = lanza
        self.peticiones = []
        self.chat = self                       # cliente.chat.completions.create
        self.completions = self

    def create(self, **kwargs):
        self.peticiones.append(kwargs)
        if self._lanza:
            raise self._lanza
        mensaje = type('M', (), {'content': self._contenido})()
        return type('R', (), {'choices': [type('C', (), {'message': mensaje})()]})()


@pytest.fixture
def con_ia(settings):
    settings.CLINIC_LLM_ENABLED = True
    return settings


def montar(monkeypatch, indice=None, modelo=None):
    """Coloca los dobles en la frontera y devuelve ambos para poder afirmarlos."""
    indice = indice if indice is not None else IndiceFalso()
    monkeypatch.setattr(rag_qa, 'indice', lambda: indice)
    if modelo is not None:
        import openai
        monkeypatch.setattr(openai, 'OpenAI', lambda **kw: modelo)
    return indice, modelo


# --- caminos que NO llegan al modelo ---------------------------------------

@pytest.mark.parametrize('vacia', ['', '   ', None])
def test_pregunta_vacia_no_toca_el_indice(monkeypatch, vacia):
    indice, _ = montar(monkeypatch)
    r = rag_qa.responder_documental(vacia)
    assert r.responde is False
    assert r.motivo == 'consulta vacía'
    assert indice.llamadas == []        # ni se molesta en buscar


def test_indice_no_disponible_degrada_en_vez_de_lanzar(monkeypatch):
    montar(monkeypatch, IndiceFalso(lanza=RagError('no hay índice')))
    r = rag_qa.responder_documental('¿qué es un cromosoma naranja?')
    assert r.responde is False
    assert 'índice no disponible' in r.motivo


def test_sin_fragmentos_sobre_el_umbral_no_responde(monkeypatch):
    montar(monkeypatch, IndiceFalso(devuelve=[]))
    r = rag_qa.responder_documental('¿cuál es el presupuesto de 2027?')
    assert r.responde is False
    assert 'umbral de recuperación' in r.motivo


def test_con_la_ia_apagada_no_hay_juez_y_no_se_responde(monkeypatch, settings):
    settings.CLINIC_LLM_ENABLED = False
    montar(monkeypatch, IndiceFalso(devuelve=[resultado(1)]))
    r = rag_qa.responder_documental('¿quién firma el informe?')
    assert r.responde is False
    assert 'sin juez' in r.motivo
    # Los candidatos SI se conservan: alimentan las sugerencias del paso 6.
    assert len(r.candidatos) == 1


# --- la frontera del modelo -------------------------------------------------

def test_el_indice_se_consulta_con_umbral_bajo_y_mas_vecinos(monkeypatch, con_ia):
    indice, _ = montar(monkeypatch, IndiceFalso(devuelve=[]))
    rag_qa.responder_documental('una pregunta')
    assert indice.llamadas[0]['k'] == rag_qa.VECINOS
    assert indice.llamadas[0]['umbral'] == rag_qa.UMBRAL_RECUPERACION


def test_al_juez_solo_van_CANDIDATOS_el_resto_son_vecinos(monkeypatch, con_ia):
    muchos = [resultado(i) for i in range(1, rag_qa.VECINOS + 1)]
    modelo = ModeloFalso(contenido='{"responde": false}')
    montar(monkeypatch, IndiceFalso(devuelve=muchos), modelo)

    r = rag_qa.responder_documental('¿qué significa naranja?')
    assert len(r.candidatos) == rag_qa.CANDIDATOS
    assert len(r.vecinos) == len(muchos) - rag_qa.CANDIDATOS
    # Y el prompt solo menciona los candidatos, no los vecinos.
    enviado = modelo.peticiones[0]['messages'][1]['content']
    assert 'DOC_1.md' in enviado and 'DOC_8.md' not in enviado


def test_el_modelo_caido_degrada_y_conserva_los_candidatos(monkeypatch, con_ia):
    montar(monkeypatch, IndiceFalso(devuelve=[resultado(1)]),
           ModeloFalso(lanza=RuntimeError('connection refused')))
    r = rag_qa.responder_documental('¿quién audita el 5%?')
    assert r.responde is False
    assert 'modelo no disponible' in r.motivo
    assert len(r.candidatos) == 1


def test_json_ilegible_del_modelo_no_revienta(monkeypatch, con_ia):
    montar(monkeypatch, IndiceFalso(devuelve=[resultado(1)]),
           ModeloFalso(contenido='esto no es JSON'))
    r = rag_qa.responder_documental('¿qué es el ISCN?')
    assert r.responde is False
    assert 'modelo no disponible' in r.motivo


def test_el_modelo_puede_declarar_que_el_corpus_no_cubre(monkeypatch, con_ia):
    montar(monkeypatch, IndiceFalso(devuelve=[resultado(1)]),
           ModeloFalso(contenido='{"responde": false, "respuesta": ""}'))
    r = rag_qa.responder_documental('¿cuál es el teléfono del doctor Rojas?')
    assert r.responde is False
    assert r.motivo == 'el corpus no cubre la pregunta'


# --- cuando SI responde -----------------------------------------------------

def test_responde_y_cita_los_fragmentos_que_el_modelo_eligio(monkeypatch, con_ia):
    montar(monkeypatch, IndiceFalso(devuelve=[resultado(1), resultado(2), resultado(3)]),
           ModeloFalso(contenido='{"responde": true, "respuesta": "Naranja es '
                                 'confianza baja.", "fuentes": [1, 3]}'))
    r = rag_qa.responder_documental('¿qué significa naranja?')
    assert r.responde is True
    assert r.texto == 'Naranja es confianza baja.'
    assert [c.fragmento.fuente for c in r.citas] == ['DOC_1.md', 'DOC_3.md']


def test_una_cita_inventada_se_ignora_en_vez_de_fabricar_una_fuente(monkeypatch, con_ia):
    """El guardrail que mas importa de este modulo.

    Si el modelo devuelve un numero de fragmento que no existe, el codigo NO
    debe inventarse una fuente: se descarta esa cita. Un informe clinico que
    cita un documento inexistente es peor que uno que no cita nada.
    """
    montar(monkeypatch, IndiceFalso(devuelve=[resultado(1), resultado(2)]),
           ModeloFalso(contenido='{"responde": true, "respuesta": "Algo.", '
                                 '"fuentes": [1, 99, -3, "dos"]}'))
    r = rag_qa.responder_documental('¿qué significa naranja?')
    assert [c.fragmento.fuente for c in r.citas] == ['DOC_1.md']


def test_sin_fuentes_utiles_cae_al_primer_candidato(monkeypatch, con_ia):
    montar(monkeypatch, IndiceFalso(devuelve=[resultado(1), resultado(2)]),
           ModeloFalso(contenido='{"responde": true, "respuesta": "Algo.", "fuentes": []}'))
    r = rag_qa.responder_documental('¿qué significa naranja?')
    assert len(r.citas) == 1
    assert r.citas[0].fragmento.fuente == 'DOC_1.md'


def test_el_juez_se_llama_con_temperatura_cero(monkeypatch, con_ia):
    modelo = ModeloFalso(contenido='{"responde": false}')
    montar(monkeypatch, IndiceFalso(devuelve=[resultado(1)]), modelo)
    rag_qa.responder_documental('una pregunta')
    assert modelo.peticiones[0]['temperature'] == 0.0
    assert modelo.peticiones[0]['response_format'] is rag_qa.RESPUESTA_SCHEMA


# --- forma de la respuesta --------------------------------------------------

def test_as_dict_expone_la_traza_completa(monkeypatch, con_ia):
    montar(monkeypatch, IndiceFalso(devuelve=[resultado(1), resultado(2)]),
           ModeloFalso(contenido='{"responde": true, "respuesta": "Sí.", "fuentes": [1]}'))
    d = rag_qa.responder_documental('¿qué significa naranja?').as_dict()
    assert set(d) == {'responde', 'texto', 'citas', 'sugerencias',
                      'candidatos_evaluados', 'latency_ms', 'motivo'}
    assert d['citas'][0]['fuente'] == 'DOC_1.md'
    assert d['citas'][0]['similitud'] == '70.0%'
    assert d['candidatos_evaluados'] == 2


def test_el_fragmento_se_trunca_antes_de_ir_al_prompt():
    largo = Resultado(fragmento=Fragmento(texto='x' * 5000, fuente='F.md',
                                          seccion='s', orden=1),
                      similitud=0.7)
    bloque = rag_qa._bloque_fragmentos([largo])
    assert bloque.count('x') == rag_qa.MAX_CHARS_FRAGMENTO


def test_el_bloque_numera_los_fragmentos_para_que_el_modelo_los_cite():
    bloque = rag_qa._bloque_fragmentos([resultado(1), resultado(2)])
    assert '[1] DOC_1.md' in bloque and '[2] DOC_2.md' in bloque
