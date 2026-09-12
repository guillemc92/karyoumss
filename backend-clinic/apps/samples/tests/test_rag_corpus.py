"""Tests del troceado del corpus documental (RAG, pasos 1 y 2).

Lógica pura: no necesitan Ollama, ni base de datos, ni el índice construido.
Lo que se fija aquí son las propiedades de las que depende la calidad de la
recuperación — si el troceado es malo, ningún modelo de embeddings lo arregla.
"""
from apps.samples.rag_corpus import (
    MIN_CHARS,
    Fragmento,
    trocear_markdown,
)


class TestJerarquiaDeSecciones:
    """Cada fragmento debe saber de qué sección salió: es lo que permite
    citar la procedencia («ISCN 2024 — 5.2 Sexo») en vez de soltar un texto
    huérfano. En clínica, una afirmación sin fuente no sirve."""

    MD = """# Capitulo 1

Texto introductorio del capitulo uno que necesita ser suficientemente largo
para superar el minimo de caracteres exigido y generar un fragmento propio.

## Seccion 1.1

Contenido de la seccion uno punto uno, tambien con longitud bastante para
que el troceador lo considere un fragmento con valor y no lo descarte.

## Seccion 1.2

Contenido de la seccion uno punto dos, igualmente largo para superar el
umbral minimo que descarta los fragmentos sin contexto aprovechable.
"""

    def test_cada_fragmento_conoce_su_seccion(self):
        frs = trocear_markdown(self.MD, 'doc.md')

        secciones = {f.seccion for f in frs}
        assert 'Capitulo 1' in secciones
        assert 'Capitulo 1 > Seccion 1.1' in secciones
        assert 'Capitulo 1 > Seccion 1.2' in secciones

    def test_la_subseccion_no_arrastra_a_su_hermana(self):
        """1.2 debe colgar de «Capitulo 1», no de «Capitulo 1 > Seccion 1.1»."""
        frs = trocear_markdown(self.MD, 'doc.md')

        s12 = next(f for f in frs if 'Seccion 1.2' in f.seccion)
        assert s12.seccion == 'Capitulo 1 > Seccion 1.2'

    def test_el_texto_embebido_lleva_fuente_y_seccion(self):
        """Sin esa cabecera, un fragmento que dice «se escribe primero el
        sexo» no se parece a «¿cómo se calcula el ISCN?»."""
        fr = Fragmento(texto='se escribe primero el sexo', fuente='ISCN 2024',
                       seccion='5 Nomenclatura > 5.2 Sexo', orden=0)

        contexto = fr.con_contexto()

        assert 'ISCN 2024' in contexto
        assert '5.2 Sexo' in contexto
        assert 'se escribe primero el sexo' in contexto


class TestSolape:
    """La consigna exige troceado CON SOLAPE. Sin él, una definición que cae
    justo en la frontera queda partida y es irrecuperable desde ambos lados."""

    def test_los_trozos_de_una_seccion_larga_comparten_texto(self):
        parrafo = ('Definicion importante que no debe perderse por el corte. ' * 120)
        frs = trocear_markdown(f'# Titulo\n\n{parrafo}', 'largo.md',
                               maximo=600, solape=150)

        assert len(frs) > 1, 'una seccion muy larga debe subdividirse'
        # Al menos un par consecutivo comparte contenido.
        solapan = any(
            any(frs[i].texto[-60:][j:] and frs[i].texto[-60:][j:] in frs[i + 1].texto
                for j in range(40))
            for i in range(len(frs) - 1)
        )
        assert solapan, 'los trozos consecutivos no comparten nada'

    def test_sin_solape_los_trozos_siguen_cubriendo_el_texto(self):
        """Aunque el solape sea cero, no se puede perder contenido."""
        parrafo = 'Frase con contenido suficiente. ' * 100
        frs = trocear_markdown(f'# T\n\n{parrafo}', 'x.md', maximo=500, solape=0)

        recompuesto = ''.join(f.texto for f in frs)
        assert len(recompuesto) >= len(parrafo.strip()) * 0.9


class TestDescartes:
    def test_las_secciones_vacias_no_generan_fragmento(self):
        frs = trocear_markdown('# Solo titulo\n\n## Otro titulo\n', 'v.md')

        assert frs == []

    def test_los_fragmentos_demasiado_cortos_se_descartan(self):
        """Un fragmento de dos palabras contamina el índice: casa con
        cualquier cosa y no aporta contexto."""
        frs = trocear_markdown('# T\n\nCorto.\n', 'c.md')

        assert frs == []

    def test_ningun_fragmento_baja_del_minimo(self):
        texto = 'Contenido con suficiente longitud para ser indexable. ' * 40
        frs = trocear_markdown(f'# T\n\n{texto}', 'd.md', maximo=400, solape=80)

        assert all(len(f.texto) >= MIN_CHARS for f in frs)


class TestOrdenYClave:
    def test_el_orden_es_correlativo_dentro_del_documento(self):
        texto = 'Parrafo con longitud suficiente para generar fragmento. ' * 30
        frs = trocear_markdown(f'# A\n\n{texto}\n\n# B\n\n{texto}', 'o.md',
                               maximo=500, solape=100)

        assert [f.orden for f in frs] == list(range(len(frs)))

    def test_la_clave_identifica_al_fragmento(self):
        texto = 'Contenido largo y suficiente para pasar el filtro minimo. ' * 30
        frs = trocear_markdown(f'# A\n\n{texto}', 'k.md', maximo=500, solape=100)

        assert len({f.clave for f in frs}) == len(frs), 'claves duplicadas'
