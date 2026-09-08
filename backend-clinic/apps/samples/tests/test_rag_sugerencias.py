"""Tests del paso 6: sugerencias por comparación de similitud.

Lo que se fija aquí es lo que hace que la sugerencia sea **honesta** y no un
adorno: que no repita lo que ya se citó, que no invente pertinencia donde la
medición dice que no la hay, y sobre todo que **exista cuando el corpus NO
responde** — que es el caso en el que le sirve al usuario.

Módulo puro: no toca el índice, ni el modelo, ni la base. Los `Resultado` se
construyen a mano porque lo que se prueba es la comparación, no la
recuperación.
"""
import pytest

from apps.samples.rag_corpus import Fragmento
from apps.samples.rag_index import Resultado
from apps.samples.rag_sugerencias import (
    MAX_SUGERENCIAS,
    Sugerencia,
    seccion_legible,
    sugerir,
    texto,
)


def res(fuente, seccion, similitud):
    return Resultado(Fragmento(texto='...', fuente=fuente, seccion=seccion, orden=0),
                     similitud)


@pytest.fixture
def candidatos():
    """Cinco candidatos casi empatados, como los que se midieron de verdad."""
    return [
        res('ADR-0022.md', '§3 Cadena de hash', 0.681),
        res('AGENTS.md', '§9 Pipeline de IA', 0.679),
        res('ADR-0022.md', '§5 Eventos', 0.672),
        res('FSD_vFinal.md', 'UC-007', 0.668),
        res('ISCN 2024.md', 'Cap. 4', 0.663),
    ]


class TestCuandoElCorpusNoResponde:
    """El caso que justifica todo el paso 6."""

    def test_un_no_se_deja_de_ser_un_callejon_sin_salida(self, candidatos):
        s = sugerir(candidatos, citas=[], respondio=False)

        assert s, 'sin sugerencias, el usuario no sabe si reformular o rendirse'
        assert all(x.tipo == 'explorar' for x in s)

    def test_el_texto_NO_promete_que_eso_responda(self, candidatos):
        # El puntaje no predice pertinencia (medido tres veces): una sugerencia
        # solo puede decir «es lo más parecido», nunca «esto responde».
        salida = texto(sugerir(candidatos, respondio=False))

        assert 'más parecido' in salida
        assert 'no cubre' in salida


class TestCuandoElCorpusSiResponde:
    def test_no_repite_lo_que_ya_se_cito(self, candidatos):
        citas = [candidatos[0]]

        s = sugerir(candidatos, citas=citas, respondio=True)

        assert ('ADR-0022.md', '§3 Cadena de hash') not in [(x.fuente, x.seccion) for x in s]

    def test_otra_seccion_del_MISMO_documento_si_se_sugiere(self, candidatos):
        # Citar ADR-0022 §3 no agota el ADR-0022: §5 sigue siendo ampliación.
        s = sugerir(candidatos, citas=[candidatos[0]], respondio=True)

        assert ('ADR-0022.md', '§5 Eventos') in [(x.fuente, x.seccion) for x in s]

    def test_son_de_tipo_ampliar(self, candidatos):
        s = sugerir(candidatos, citas=[candidatos[0]], respondio=True)

        assert all(x.tipo == 'ampliar' for x in s)


class TestQueSeAgrupaEnCadaCaso:
    """Diferencia que salió al ejecutarlo contra el índice real."""

    def test_explorando_NO_se_repite_documento(self, candidatos):
        # Preguntando por el teléfono de una persona salían tres secciones del
        # mismo ADR-0011: tres formas de decir lo mismo, ocupando el sitio de
        # otros documentos que sí podrían orientar.
        s = sugerir(candidatos, respondio=False)

        assert len(s) == len({x.fuente for x in s})

    def test_ampliando_SI_puede_repetirse_documento(self, candidatos):
        # Aquí ya se sabe qué documento responde: lo útil es la otra sección.
        s = sugerir(candidatos, citas=[candidatos[0]], respondio=True)

        assert 'ADR-0022.md' in [x.fuente for x in s]


class TestSeccionLegible:
    def test_se_queda_con_el_ultimo_tramo_de_la_miga_de_pan(self):
        # El troceador guarda la jerarquía entera para dar contexto al vector;
        # como sugerencia es ilegible.
        larga = '4.2 FSD-UC-002 – Semaforización > 4.3 FSD-UC-003 – XAI > 5. Reglas'

        assert seccion_legible(larga) == '5. Reglas'

    def test_quita_los_escapes_de_markdown(self):
        assert seccion_legible(r'5\. Reglas de negocio') == '5. Reglas de negocio'

    def test_una_seccion_normal_no_se_toca(self):
        assert seccion_legible('§3 Cadena de hash') == '§3 Cadena de hash'

    def test_sin_seccion_devuelve_vacio(self):
        assert seccion_legible('') == ''

    def test_la_sugerencia_muestra_la_seccion_ya_limpia(self):
        s = sugerir([res('FSD.md', 'A > B > 5\\. Reglas', 0.66)], respondio=False)

        assert s[0].seccion == '5. Reglas'


class TestComparacionDeSimilitud:
    def test_van_de_mayor_a_menor_parecido(self, candidatos):
        # Las diferencias son milésimas, pero el orden tiene que ser estable:
        # es el único criterio disponible.
        s = sugerir(candidatos, respondio=False)

        assert [x.similitud for x in s] == sorted((x.similitud for x in s), reverse=True)

    def test_no_repite_la_misma_seccion_dos_veces(self):
        # Dos fragmentos de la misma sección son un solo sitio al que ir.
        repetidos = [res('ADR-0022.md', '§3', 0.68), res('ADR-0022.md', '§3', 0.67)]

        s = sugerir(repetidos, citas=[], respondio=True)

        assert len(s) == 1

    def test_se_corta_en_el_maximo(self):
        muchos = [res(f'DOC-{i}.md', f'§{i}', 0.7 - i / 100) for i in range(10)]

        assert len(sugerir(muchos, respondio=False)) == MAX_SUGERENCIAS

    def test_el_porcentaje_se_muestra_como_lo_pide_la_consigna(self, candidatos):
        s = sugerir(candidatos, respondio=False)

        assert s[0].porcentaje == '68.1%'


class TestBordes:
    def test_sin_candidatos_no_hay_sugerencias(self):
        assert sugerir([], respondio=False) == []

    def test_sin_sugerencias_el_texto_es_vacio(self):
        # Para que nadie imprima un encabezado huérfano.
        assert texto([]) == ''

    def test_si_todo_lo_recuperado_ya_se_cito_no_sobra_nada(self, candidatos):
        s = sugerir(candidatos, citas=candidatos, respondio=True)

        assert s == []

    def test_un_fragmento_sin_seccion_se_muestra_solo_con_el_documento(self):
        s = sugerir([res('AGENTS.md', '', 0.66)], respondio=False)

        assert s[0].donde == 'AGENTS.md'


class TestSerializacion:
    def test_as_dict_lleva_documento_seccion_y_similitud(self, candidatos):
        d = sugerir(candidatos, respondio=False)[0].as_dict()

        assert d == {'tipo': 'explorar', 'documento': 'ADR-0022.md',
                     'seccion': '§3 Cadena de hash', 'similitud': '68.1%'}

    def test_una_seccion_vacia_se_muestra_con_guion(self):
        d = sugerir([res('AGENTS.md', '', 0.66)], respondio=False)[0].as_dict()

        assert d['seccion'] == '—'

    def test_la_sugerencia_es_inmutable(self, candidatos):
        # Viaja dentro de respuestas que se serializan y se auditan: que nadie
        # la retoque por el camino.
        s = sugerir(candidatos, respondio=False)[0]

        with pytest.raises(Exception):
            s.similitud = 0.99  # type: ignore[misc]

    def test_el_tipo_declarado_es_uno_de_los_dos(self, candidatos):
        assert {x.tipo for x in sugerir(candidatos, respondio=False)} <= {'ampliar', 'explorar'}
        assert isinstance(sugerir(candidatos, respondio=False)[0], Sugerencia)
