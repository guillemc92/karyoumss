"""Embeddings, indice y recuperacion: las piezas, una a una.

`test_integracion_rag_flujo.py` prueba el camino entero con el disco de verdad.
Aqui se prueban las decisiones sueltas que ese camino no llega a ejercitar,
casi todas relacionadas con **lo que pasa cuando algo falta**:

    embeber        que lotea, que normaliza y que un fallo de Ollama se llama
                   RagError y dice con que modelo fue
    Indice         que un descuadre vectores/fragmentos se detecta al construir,
                   no al buscar
    buscar         que una consulta vacia o un indice vacio devuelven [] sin
                   tocar la red
    cargar         que la ausencia de indice explica COMO construirlo
    indice()       que se carga una sola vez por proceso
    construir      que embebe el fragmento CON su contexto, no el texto pelado

Doble unicamente en la frontera: `httpx` (Ollama) y el disco (`tmp_path`).
La aritmetica de vectores es la real de numpy.
"""
import json

import numpy as np
import pytest

from apps.samples import rag_index
from apps.samples.rag_corpus import Fragmento
from apps.samples.rag_index import (
    LOTE,
    TIMEOUT_S,
    Indice,
    RagError,
    Resultado,
    construir,
    embeber,
)


def frag(texto='texto', fuente='DOC.md', seccion='Seccion', orden=1):
    return Fragmento(texto=texto, fuente=fuente, seccion=seccion, orden=orden)


class Ollama:
    """Doble de `httpx.Client`: devuelve vectores y registra cada lote pedido."""

    def __init__(self, dims=4, lanza=None):
        self.dims = dims
        self.lanza = lanza
        self.lotes = []
        self.timeout = None

    def montar(self, monkeypatch):
        # `embeber` importa httpx dentro de la funcion: se sustituye en el
        # modulo httpx, que es donde lo va a buscar.
        import httpx
        monkeypatch.setattr(httpx, 'Client', self._abrir)
        return self

    def _abrir(self, **kw):
        self.timeout = kw.get('timeout')
        return self

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def post(self, url, json=None):
        if self.lanza is not None:
            raise self.lanza
        entradas = json['input']
        self.lotes.append({'url': url, 'modelo': json['model'], 'n': len(entradas),
                           'textos': list(entradas)})
        # Vectores sin normalizar a proposito: normalizar es trabajo de embeber.
        return _Respuesta({'embeddings': [[float(i + 1)] * self.dims
                                          for i in range(len(entradas))]})


class _Respuesta:
    def __init__(self, cuerpo):
        self.cuerpo = cuerpo

    def raise_for_status(self):
        return None

    def json(self):
        return self.cuerpo


# --- embeber ----------------------------------------------------------------

def test_embeber_devuelve_vectores_normalizados(monkeypatch):
    """El coseno se reduce a producto escalar solo si la norma es 1.

    Si embeber dejara pasar vectores sin normalizar, `buscar` seguiria
    ordenando —el fallo no se veria— pero las similitudes reportadas dejarian
    de estar en [0, 1] y el umbral de 0.55 no significaria nada.
    """
    Ollama().montar(monkeypatch)
    m = embeber(['uno', 'dos', 'tres'])
    assert m.shape == (3, 4)
    assert np.allclose(np.linalg.norm(m, axis=1), 1.0)


def test_embeber_va_por_lotes_y_avisa_del_avance(monkeypatch):
    """Una peticion por fragmento multiplicaria por mil la latencia."""
    ollama = Ollama().montar(monkeypatch)
    textos = ['t%d' % i for i in range(LOTE * 2 + 1)]
    avances = []

    embeber(textos, progreso=lambda hechos, total: avances.append((hechos, total)))

    assert [l['n'] for l in ollama.lotes] == [LOTE, LOTE, 1]
    # El progreso es acumulado, no por lote: construir el indice tarda minutos y
    # sin senal no se distingue de un cuelgue.
    assert avances == [(LOTE, len(textos)), (LOTE * 2, len(textos)),
                       (len(textos), len(textos))]


def test_embeber_habla_con_ollama_local_y_con_holgura(monkeypatch):
    """RN-03: el corpus clinico no sale de la maquina para volverse numeros."""
    ollama = Ollama().montar(monkeypatch)
    embeber(['uno'], modelo='nomic-embed-text')

    assert ollama.lotes[0]['url'] == 'http://localhost:11434/api/embed'
    assert ollama.lotes[0]['modelo'] == 'nomic-embed-text'
    # En CPU, 32 fragmentos largos pasaron de dos minutos: el timeout se midio.
    assert ollama.timeout == TIMEOUT_S >= 600.0


def test_un_vector_nulo_no_rompe_la_division(monkeypatch):
    """Norma 0 -> se sustituye por 1. Es division por cero, no un caso raro."""
    class Nulo(Ollama):
        def post(self, url, json=None):
            return _Respuesta({'embeddings': [[0.0] * self.dims]})

    Nulo().montar(monkeypatch)
    m = embeber(['vacio'])
    assert np.all(m == 0.0) and not np.isnan(m).any()


def test_si_ollama_no_responde_se_dice_con_que_modelo_fue(monkeypatch):
    """El error mas frecuente en la practica es tener Ollama sin ese modelo
    descargado. Si la excepcion no lo nombra, el diagnostico cuesta media hora.
    """
    import httpx
    Ollama(lanza=httpx.ConnectError('conexion rechazada')).montar(monkeypatch)
    with pytest.raises(RagError) as exc:
        embeber(['uno'], modelo='nomic-embed-text')
    assert 'nomic-embed-text' in str(exc.value)
    assert 'conexion rechazada' in str(exc.value)


# --- Resultado --------------------------------------------------------------

def test_la_cita_lleva_documento_seccion_y_porcentaje():
    r = Resultado(frag(fuente='ADR-0022.md', seccion='Decision > D1'), 0.8123)
    assert r.como_cita() == 'ADR-0022.md — Decision > D1 (81.2%)'


def test_sin_seccion_la_cita_es_solo_el_documento():
    """No todos los documentos tienen encabezados; la cita sigue siendo valida."""
    r = Resultado(frag(fuente='ISCN 2024.md', seccion=''), 0.5)
    assert r.como_cita() == 'ISCN 2024.md (50.0%)'


# --- Indice -----------------------------------------------------------------

def test_un_descuadre_se_detecta_al_construir_no_al_buscar():
    """Con un vector de mas, `buscar` devolveria el fragmento equivocado en
    silencio. Fallar aqui convierte una respuesta falsa en un error visible."""
    with pytest.raises(RagError, match='descuadrados'):
        Indice(np.zeros((3, 4), dtype=np.float32), [frag(), frag()], 'm')


def test_una_consulta_vacia_no_llega_a_la_red(monkeypatch):
    llamadas = []
    monkeypatch.setattr(rag_index, 'embeber',
                        lambda *a, **kw: llamadas.append(a) or np.zeros((1, 4)))
    indice = Indice(np.zeros((1, 4), dtype=np.float32), [frag()], 'm')

    assert indice.buscar('   ') == []
    assert llamadas == []


def test_un_indice_vacio_devuelve_lista_vacia(monkeypatch):
    monkeypatch.setattr(rag_index, 'embeber',
                        lambda *a, **kw: pytest.fail('no deberia embeber'))
    assert Indice(np.zeros((0, 4), dtype=np.float32), [], 'm').buscar('algo') == []
    assert len(Indice(np.zeros((0, 4), dtype=np.float32), [], 'm')) == 0


def test_buscar_ordena_por_similitud_y_corta_por_umbral(monkeypatch):
    """Devolver [] cuando nada supera el umbral es una respuesta legitima: el
    corpus no cubre la pregunta. No es un fallo que haya que enmascarar."""
    vectores = np.array([[1.0, 0.0], [0.6, 0.8], [0.0, 1.0]], dtype=np.float32)
    fragmentos = [frag(fuente='A.md'), frag(fuente='B.md'), frag(fuente='C.md')]
    indice = Indice(vectores, fragmentos, 'm')
    monkeypatch.setattr(rag_index, 'embeber',
                        lambda *a, **kw: np.array([[1.0, 0.0]], dtype=np.float32))

    assert [r.fragmento.fuente for r in indice.buscar('q', k=3, umbral=0.0)] == [
        'A.md', 'B.md', 'C.md']
    assert [r.fragmento.fuente for r in indice.buscar('q', k=3, umbral=0.5)] == [
        'A.md', 'B.md']
    assert indice.buscar('q', k=3, umbral=0.99) != []      # A.md da exactamente 1.0
    assert indice.buscar('q', k=3, umbral=1.01) == []


# --- persistencia -----------------------------------------------------------

def test_guardar_reduce_a_float16_y_cargar_lo_devuelve_utilizable(tmp_path):
    """El indice entra al repositorio: float16 parte por dos lo que se versiona."""
    vectores = np.array([[0.6, 0.8], [0.8, 0.6]], dtype=np.float32)
    Indice(vectores, [frag(fuente='A.md'), frag(fuente='B.md')], 'm').guardar(tmp_path)

    assert np.load(tmp_path / 'vectores.npy').dtype == np.float16
    meta = json.loads((tmp_path / 'fragmentos.json').read_text(encoding='utf-8'))
    assert meta['modelo'] == 'm'
    assert [f['fuente'] for f in meta['fragmentos']] == ['A.md', 'B.md']

    recargado = Indice.cargar(tmp_path)
    assert recargado.vectores.dtype == np.float32      # vuelve a float32 en memoria
    assert len(recargado) == 2


def test_sin_indice_el_error_dice_como_construirlo(tmp_path):
    """Un «fichero no encontrado» pelado deja al que despliega sin saber que hacer."""
    with pytest.raises(RagError) as exc:
        Indice.cargar(tmp_path / 'no_existe')
    assert 'build_rag_index' in str(exc.value)


def test_falta_uno_de_los_dos_ficheros_y_tambien_falla(tmp_path):
    """Medio indice es peor que ninguno: cargaria vectores sin sus metadatos."""
    np.save(tmp_path / 'vectores.npy', np.zeros((1, 2), dtype=np.float16))
    with pytest.raises(RagError):
        Indice.cargar(tmp_path)


def test_el_indice_se_carga_una_sola_vez_por_proceso(monkeypatch):
    """Son ~2 MB: recargarlo en cada pregunta se nota en la latencia."""
    cargas = []

    def cargar_falso(ruta=None):
        cargas.append(ruta)
        return Indice(np.zeros((1, 2), dtype=np.float32), [frag()], 'm')

    monkeypatch.setattr(rag_index, '_indice', None)
    monkeypatch.setattr(Indice, 'cargar', staticmethod(cargar_falso))

    primero, segundo = rag_index.indice(), rag_index.indice()
    assert primero is segundo
    assert len(cargas) == 1


# --- construir --------------------------------------------------------------

def test_construir_embebe_el_fragmento_con_su_seccion_delante(monkeypatch):
    """Sin la cabecera, «se escribe primero el sexo» no se parece a «¿como se
    calcula el ISCN?». Con ella, si. Es la diferencia entre recuperar y no."""
    ollama = Ollama().montar(monkeypatch)
    fragmentos = [frag(texto='Se escribe primero el sexo.', fuente='ISCN 2024.md',
                       seccion='5 Nomenclatura > 5.2 Sexo')]

    indice = construir(fragmentos, modelo='nomic-embed-text')

    (enviado,) = ollama.lotes[0]['textos']
    assert enviado.startswith('ISCN 2024.md — 5 Nomenclatura > 5.2 Sexo')
    assert 'Se escribe primero el sexo.' in enviado
    assert len(indice) == 1 and indice.modelo == 'nomic-embed-text'


def test_construir_sin_fragmentos_falla_antes_de_llamar_a_ollama(monkeypatch):
    """Un indice vacio se guardaria sin protestar y solo se notaria en produccion,
    cuando el RAG contestara «no lo sé» a todo."""
    ollama = Ollama().montar(monkeypatch)
    with pytest.raises(RagError, match='no hay fragmentos'):
        construir([])
    assert ollama.lotes == []
