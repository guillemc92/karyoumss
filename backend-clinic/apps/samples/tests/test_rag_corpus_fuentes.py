"""`cargar_fuentes`: que documentos entran al corpus y cuales se ignoran.

Es la primera pieza del RAG y la unica que toca el sistema de ficheros. Aqui no
se dobla nada: se escriben ficheros de verdad en `tmp_path` y se leen de verdad.
Doblar el disco para probar la funcion cuyo trabajo ES leer del disco no probaria
nada.

## Lo que hay que asegurar

El contrato de la funcion es raro a proposito: **ignora en silencio** lo que no
puede leer. Eso normalmente seria un olor, y aqui es la decision correcta —el
corpus documental de un proyecto cambia, y que falte un ADR no debe impedir
construir el indice—. Pero al ser silenciosa, una regresion tampoco haria ruido:
el indice saldria mas pobre y nadie se enteraria hasta que el RAG contestara «no
lo sé» a algo que si estaba documentado.

Por eso se afirma exactamente QUE se ignora y QUE no.
"""
import pytest

from apps.samples.rag_corpus import FUENTES, MIN_CHARS, cargar_fuentes

# Las secciones pasan de MIN_CHARS (120) a proposito: por debajo de eso el
# troceador las descarta, porque un fragmento suelto de dos lineas no lleva
# contexto suficiente para que el embedding signifique algo. Un corpus de prueba
# con secciones cortas devuelve cero fragmentos y parece que la carga falla.
DOC = """# Titulo

## Seccion primera

Un cromosoma naranja es el que tiene una confianza por debajo de 0.85, el umbral
que fija RN-02. Mientras quede uno sin resolver, el caso no puede emitir informe:
el analista tiene que revisarlo con el mapa de calor delante y decidir.

## Seccion segunda

El supervisor firma el informe con doble factor de autenticacion, y no puede ser
la misma persona que lo valido como analista. Esa separacion es RN-06, y es lo
que convierte la firma en un acto de cumplimiento y no en un tramite.
"""


@pytest.fixture
def raiz(tmp_path):
    (tmp_path / 'docs').mkdir()
    (tmp_path / 'docs' / 'ADR-0022.md').write_text(DOC, encoding='utf-8')
    (tmp_path / 'docs' / 'ADR-0023.md').write_text(DOC, encoding='utf-8')
    (tmp_path / 'suelto.md').write_text(DOC, encoding='utf-8')
    return tmp_path


def fuentes_de(fragmentos):
    return sorted({f.fuente for f in fragmentos})


# --- lo que entra -----------------------------------------------------------

def test_carga_y_trocea_los_documentos_que_encuentra(raiz):
    fragmentos = cargar_fuentes(raiz, [('docs/*.md', 'ADR')])

    assert fuentes_de(fragmentos) == ['ADR: ADR-0022.md', 'ADR: ADR-0023.md']
    # Trocea: un documento con dos secciones no entra como un bloque unico.
    assert len(fragmentos) > 2
    assert any('naranja' in f.texto for f in fragmentos)


def test_la_etiqueta_va_delante_del_nombre(raiz):
    """La cita que ve el usuario sale de aqui. «ADR: ADR-0022.md» dice de que
    clase de documento viene; el nombre a secas, no."""
    (fragmento, *_) = cargar_fuentes(raiz, [('suelto.md', 'Manual')])
    assert fragmento.fuente == 'Manual: suelto.md'


def test_sin_etiqueta_queda_el_nombre_del_fichero(raiz):
    """La etiqueta es opcional: un documento que se explica solo no necesita
    prefijo, y anadir «: » delante quedaria feo en la cita."""
    (fragmento, *_) = cargar_fuentes(raiz, [('suelto.md', '')])
    assert fragmento.fuente == 'suelto.md'


def test_varios_patrones_se_acumulan_en_orden(raiz):
    fragmentos = cargar_fuentes(raiz, [('suelto.md', 'Manual'), ('docs/*.md', 'ADR')])
    fuentes = [f.fuente for f in fragmentos]
    # El orden de la lista manda: primero el manual, despues los ADR.
    assert fuentes[0].startswith('Manual:')
    assert fuentes[-1].startswith('ADR:')


def test_los_ficheros_de_un_patron_salen_ordenados(raiz):
    """`sorted(glob)`: sin el, el orden lo decidiria el sistema de ficheros y el
    indice cambiaria de una maquina a otra sin que nadie tocara nada."""
    fuentes = [f.fuente for f in cargar_fuentes(raiz, [('docs/*.md', 'ADR')])]
    assert fuentes == sorted(fuentes, key=lambda s: (s, ))


# --- lo que se ignora, y por que ---------------------------------------------

def test_un_patron_que_no_casa_con_nada_no_rompe(raiz):
    """Que falte un documento empobrece el indice; no debe impedir construirlo."""
    assert cargar_fuentes(raiz, [('no_existe/*.md', 'X')]) == []


def test_un_directorio_que_casa_con_el_patron_se_salta(raiz):
    """`docs/*` casa tambien con subdirectorios. Sin el `is_file()`, leerlo
    lanzaria IsADirectoryError y se caeria la construccion entera del indice."""
    (raiz / 'docs' / 'subcarpeta.md').mkdir()

    fragmentos = cargar_fuentes(raiz, [('docs/*.md', 'ADR')])
    assert fuentes_de(fragmentos) == ['ADR: ADR-0022.md', 'ADR: ADR-0023.md']


def test_un_fichero_que_no_es_utf8_se_salta_sin_tumbar_el_resto(raiz):
    """Los documentos reales del laboratorio llegan de Word y de exportaciones
    viejas; alguno vendra en latin-1. Uno ilegible no puede costar el corpus
    entero — pero los demas si tienen que entrar."""
    (raiz / 'docs' / 'viejo.md').write_bytes(b'# T\xedtulo en latin-1\n\ntexto\n')

    fragmentos = cargar_fuentes(raiz, [('docs/*.md', 'ADR')])
    assert fuentes_de(fragmentos) == ['ADR: ADR-0022.md', 'ADR: ADR-0023.md']


def test_un_fichero_vacio_no_aporta_fragmentos(raiz):
    (raiz / 'docs' / 'vacio.md').write_text('', encoding='utf-8')

    fragmentos = cargar_fuentes(raiz, [('docs/*.md', 'ADR')])
    assert 'ADR: vacio.md' not in fuentes_de(fragmentos)


def test_una_seccion_demasiado_corta_no_entra_al_corpus(raiz):
    """MIN_CHARS = 120. Un fragmento de dos lineas no lleva contexto suficiente
    para que su embedding signifique algo: entraria al indice y competiria por
    salir como cita sin poder fundamentar nada.

    Se prueba porque es invisible: el documento se lee bien, no hay error, y
    simplemente no aparece.
    """
    corto = '# Nota\n\n## Apunte\n\nRevisar esto.\n'
    assert len(corto) < MIN_CHARS
    (raiz / 'docs' / 'nota.md').write_text(corto, encoding='utf-8')

    fragmentos = cargar_fuentes(raiz, [('docs/*.md', 'ADR')])
    assert 'ADR: nota.md' not in fuentes_de(fragmentos)
    assert fuentes_de(fragmentos) == ['ADR: ADR-0022.md', 'ADR: ADR-0023.md']


# --- la lista declarada -----------------------------------------------------

def test_las_fuentes_se_declaran_no_se_descubren():
    """Un corpus que crece por accidente es un corpus que nadie reviso.

    Si manana alguien cambiara `FUENTES` por un `glob('**/*.md')`, el RAG
    empezaria a citar borradores y notas sueltas como si fueran normativa.
    """
    assert FUENTES, 'el corpus no puede quedarse sin fuentes declaradas'
    for patron, etiqueta in FUENTES:
        assert isinstance(patron, str) and isinstance(etiqueta, str)
        assert '**' not in patron, 'patron recursivo: el corpus dejaria de ser explicito'
