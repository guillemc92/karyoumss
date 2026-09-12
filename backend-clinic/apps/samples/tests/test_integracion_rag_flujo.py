"""Integracion: entrada del usuario -> recuperacion -> respuesta.

## Que es REAL aqui y que no

Real, sobre un espacio temporal (`tmp_path`):

    la base vectorial      numpy de verdad, con producto coseno de verdad
    los ficheros           `vectores.npy` + `fragmentos.json` escritos y
                           releidos del disco, con su ida y vuelta a float16
    la busqueda            orden por similitud, corte por `k` y por umbral
    el reparto             candidatos que van al juez / vecinos que no
    la resolucion de citas del numero que devuelve el juez al fichero real

Doblado, y solo esto — son las dos unicas salidas del proceso:

    `embeber`   la red hacia Ollama para vectorizar
    `OpenAI`    la red hacia el juez

## Se afirma el CAMINO, no solo el resultado

La consigna pide asegurar el recorrido. Cada prueba deja constancia de por
donde paso: que el indice se escribio a disco y se releyo, QUE fragmentos se
recuperaron y en que orden, cuales llegaron al juez y cuales se quedaron fuera,
y que la cita final apunta a un documento que estaba en el disco temporal.

Un test que solo mirase `responde is True` pasaria aunque la recuperacion
devolviera el fragmento equivocado.
"""
import json

import numpy as np
import pytest

from apps.samples import rag_index, rag_qa
from apps.samples.rag_corpus import Fragmento
from apps.samples.rag_index import Indice

MODELO = 'nomic-embed-text'

# Corpus minimo pero con la FORMA del real: cinco documentos del mismo dominio.
CORPUS = [
    Fragmento(texto='Un cromosoma naranja tiene confianza por debajo de 0.85 '
                    'y bloquea la emision del informe.',
              fuente='FSD_vFinal.md', seccion='5 Reglas de negocio > RN-02', orden=1),
    Fragmento(texto='El supervisor firma el informe con doble factor y no '
                    'puede ser el mismo analista que lo valido.',
              fuente='ADR-0023.md', seccion='Decision > D2', orden=2),
    Fragmento(texto='La nomenclatura ISCN la calcula una funcion determinista, '
                    'nunca el modelo de lenguaje.',
              fuente='ADR-0024.md', seccion='Decision > D1', orden=3),
    Fragmento(texto='La auditoria del 5% selecciona cromosomas verdes al azar '
                    'para que el supervisor los revise.',
              fuente='ADR-0023.md', seccion='Decision > D4', orden=4),
    Fragmento(texto='El audit trail es append-only y encadena cada evento con '
                    'SHA-256.',
              fuente='ADR-0022.md', seccion='Decision > D1', orden=5),
]

# Los vectores comparten una componente grande (eje 0) y se diferencian en un
# eje propio mas pequeno. NO es un detalle de laboratorio: reproduce lo que se
# midio en produccion — todo el corpus habla del mismo dominio, asi que todos
# los fragmentos se parecen entre si y ningun umbral los separa. Con vectores
# ortogonales solo uno superaria el umbral y el reparto candidatos/vecinos no
# se podria probar.
DIMS = 6
PESO_COMPARTIDO = 1.0
PESO_PROPIO = 0.6


def _vector_doc(i):
    v = np.zeros(DIMS, dtype=np.float32)
    v[0] = PESO_COMPARTIDO
    v[i + 1] = PESO_PROPIO
    return v / np.linalg.norm(v)


CONSULTAS = {
    # Cercana a todos (dominio comun) pero mas al documento 1.
    '¿que significa que un cromosoma este naranja?': [1.0, 0.5, 0.4, 0.3, 0.2, 0.05],
    '¿quien firma el informe?':                      [1.0, 0.2, 0.5, 0.3, 0.4, 0.05],
    '¿cual es el presupuesto del laboratorio?':       [1.0, 0.3, 0.3, 0.3, 0.3, 0.30],
}


def _normalizar(v):
    v = np.asarray(v, dtype=np.float32)
    return v / (np.linalg.norm(v) or 1.0)


@pytest.fixture
def indice_en_disco(tmp_path, monkeypatch):
    """Construye un indice REAL, lo guarda en tmp_path y lo vuelve a cargar.

    Devuelve (indice_recargado, ruta) para poder afirmar que los ficheros
    existen de verdad.
    """
    def embeber_falso(textos, modelo=MODELO):
        # Unica frontera doblada en la construccion: la red hacia Ollama.
        salida = []
        for t in textos:
            if t in CONSULTAS:
                salida.append(_normalizar(CONSULTAS[t]))
            else:
                idx = next((i for i, f in enumerate(CORPUS) if f.texto == t), 0)
                salida.append(_vector_doc(idx))
        return np.vstack(salida)

    monkeypatch.setattr(rag_index, 'embeber', embeber_falso)

    ruta = tmp_path / 'indice'
    original = Indice(np.vstack([_vector_doc(i) for i in range(len(CORPUS))]),
                      list(CORPUS), MODELO)
    original.guardar(ruta)
    return Indice.cargar(ruta), ruta


def montar_juez(monkeypatch, contenido):
    """Doble del juez que ademas GUARDA lo que se le mando, para inspeccionarlo."""
    registro = {}

    class Juez:
        def __init__(self):
            self.chat = self
            self.completions = self

        def create(self, **kw):
            registro.update(kw)
            m = type('M', (), {'content': contenido})()
            return type('R', (), {'choices': [type('C', (), {'message': m})()]})()

    import openai
    monkeypatch.setattr(openai, 'OpenAI', lambda **kw: Juez())
    return registro


# --- el flujo completo ------------------------------------------------------

def test_flujo_completo_deja_rastro_de_todo_el_camino(
        indice_en_disco, monkeypatch, settings):
    """entrada -> recuperacion -> juez -> cita, afirmando cada tramo."""
    indice, ruta = indice_en_disco
    settings.CLINIC_LLM_ENABLED = True

    # TRAMO 1 — el indice existe en el disco temporal, no en memoria.
    assert (ruta / 'vectores.npy').exists()
    assert (ruta / 'fragmentos.json').exists()
    meta = json.loads((ruta / 'fragmentos.json').read_text(encoding='utf-8'))
    assert meta['modelo'] == MODELO
    assert len(meta['fragmentos']) == len(CORPUS)
    assert len(indice) == len(CORPUS)            # y se releyo entero

    monkeypatch.setattr(rag_qa, 'indice', lambda: indice)
    registro = montar_juez(monkeypatch,
                           '{"responde": true, "respuesta": "Confianza bajo 0.85.", '
                           '"fuentes": [1]}')

    pregunta = '¿que significa que un cromosoma este naranja?'
    r = rag_qa.responder_documental(pregunta)

    # TRAMO 2 — la recuperacion trajo el fragmento correcto EN PRIMER LUGAR.
    assert r.candidatos, 'la recuperacion no devolvio nada'
    assert r.candidatos[0].fragmento.fuente == 'FSD_vFinal.md'
    assert r.candidatos[0].similitud > r.candidatos[-1].similitud

    # TRAMO 3 — al juez le llego exactamente ese texto, numerado para citarlo.
    enviado = registro['messages'][1]['content']
    assert '[1] FSD_vFinal.md' in enviado
    assert 'RN-02' in enviado
    assert pregunta in enviado

    # TRAMO 4 — la cita resuelve a un documento que estaba en el disco.
    assert r.responde is True
    assert len(r.citas) == 1
    assert r.citas[0].fragmento.fuente == 'FSD_vFinal.md'
    assert r.citas[0].fragmento.fuente in {f['fuente'] for f in meta['fragmentos']}


def test_una_pregunta_fuera_del_corpus_recorre_el_camino_hasta_el_no(
        indice_en_disco, monkeypatch, settings):
    """El «no sé» tambien es un recorrido completo, y hay que asegurarlo.

    Es el caso que mas importa clinicamente: el sistema recupera, consulta al
    juez, y el juez dice que el corpus no cubre la pregunta. Sin este test, una
    regresion que hiciera responder SIEMPRE pasaria desapercibida.
    """
    indice, _ = indice_en_disco
    settings.CLINIC_LLM_ENABLED = True
    monkeypatch.setattr(rag_qa, 'indice', lambda: indice)
    registro = montar_juez(monkeypatch, '{"responde": false, "respuesta": ""}')

    r = rag_qa.responder_documental('¿cual es el presupuesto del laboratorio?')

    # Recorrio: hubo recuperacion (el umbral es bajo a proposito)...
    assert r.candidatos, 'deberia recuperar algo: el umbral de recuperacion es bajo'
    # ...el juez fue consultado de verdad...
    assert registro['temperature'] == 0.0
    # ...y decidio no responder.
    assert r.responde is False
    assert r.motivo == 'el corpus no cubre la pregunta'
    assert r.texto == ''
    assert r.citas == []
    # Y aun asi el usuario no se queda sin salida: hay sugerencias.
    assert r.as_dict()['sugerencias'] is not None


def test_el_reparto_candidatos_vecinos_sobrevive_al_disco(
        indice_en_disco, monkeypatch, settings):
    """Solo los candidatos van al juez; los vecinos alimentan las sugerencias."""
    indice, _ = indice_en_disco
    settings.CLINIC_LLM_ENABLED = True
    monkeypatch.setattr(rag_qa, 'indice', lambda: indice)
    registro = montar_juez(monkeypatch, '{"responde": false}')

    r = rag_qa.responder_documental('¿quien firma el informe?')

    assert len(r.candidatos) == rag_qa.CANDIDATOS
    # Exigir vecinos NO es decorativo: sin esto el bucle de abajo pasaria en
    # vacio y el test no probaria el reparto, que es lo que dice probar.
    assert r.vecinos, 'sin vecinos el reparto no se esta ejercitando'
    assert len(r.candidatos) + len(r.vecinos) == len(CORPUS)
    assert r.candidatos[0].fragmento.fuente == 'ADR-0023.md'
    # Ningun vecino se colo en el prompt del juez.
    enviado = registro['messages'][1]['content']
    for vecino in r.vecinos:
        assert vecino.fragmento.texto[:40] not in enviado


def test_el_indice_recargado_da_los_mismos_resultados_que_el_original(
        indice_en_disco):
    """La ida y vuelta a disco pasa por float16: hay que comprobar que no rompe.

    `guardar()` reduce a float16 para que el fichero pese la mitad en el
    repositorio. Es una perdida de precision real, y esta prueba fija que no
    altera el ORDEN de recuperacion, que es lo unico que importa.
    """
    recargado, _ = indice_en_disco
    resultados = recargado.buscar('¿que significa que un cromosoma este naranja?',
                                  k=3, umbral=0.0)
    assert [r.fragmento.fuente for r in resultados][:3] == [
        'FSD_vFinal.md', 'ADR-0023.md', 'ADR-0024.md']
    # El orden por similitud se conserva pese al redondeo a float16.
    sims = [r.similitud for r in resultados]
    assert sims == sorted(sims, reverse=True)
