"""Tests de la salida estructurada del LLM (ADR-0024 D4).

Dos capas independientes:

1. **Pydantic valida la FORMA** — campos, tipos, longitudes.
2. **`es_coherente_con` valida el CONTENIDO** contra el ISCN determinístico.

La distinción importa: un objeto perfectamente bien formado que afirme una
trisomía inexistente pasa la primera capa. La segunda es la que evita el
diagnóstico falso.

Función pura: no necesitan base de datos, Django ni Ollama.
"""
import pytest
from pydantic import ValidationError

from apps.samples.llm_schemas import (
    NARRATIVA_JSON_SCHEMA,
    NarrativaCariotipo,
    NivelConfianza,
)

HALLAZGO = 'Se observa un cromosoma 21 adicional en todas las metafases analizadas.'
INTERPRETACION = (
    'El hallazgo es compatible con trisomía 21. El resultado requiere '
    'correlación clínica para determinar su significado.'
)


def _narrativa(**over) -> NarrativaCariotipo:
    datos = dict(
        hallazgo=HALLAZGO, interpretacion=INTERPRETACION,
        es_normal=False, anomalias_citadas=['+21'], nivel_confianza='alta',
    )
    datos.update(over)
    return NarrativaCariotipo(**datos)


class TestContratoDeTipos:
    """Capa 1 — la forma."""

    def test_objeto_valido(self):
        n = _narrativa()
        assert n.es_normal is False
        assert n.anomalias_citadas == ['+21']
        assert n.nivel_confianza is NivelConfianza.ALTA

    def test_nivel_confianza_por_defecto(self):
        n = NarrativaCariotipo(
            hallazgo=HALLAZGO, interpretacion=INTERPRETACION, es_normal=True)
        assert n.nivel_confianza is NivelConfianza.MEDIA
        assert n.anomalias_citadas == []

    @pytest.mark.parametrize('campo', ['hallazgo', 'interpretacion', 'es_normal'])
    def test_campos_obligatorios(self, campo):
        datos = dict(hallazgo=HALLAZGO, interpretacion=INTERPRETACION, es_normal=True)
        del datos[campo]
        with pytest.raises(ValidationError):
            NarrativaCariotipo(**datos)

    def test_rechaza_texto_demasiado_corto(self):
        """Un 'Normal.' pasaría desapercibido en prosa; acá no."""
        with pytest.raises(ValidationError):
            _narrativa(hallazgo='corto')

    def test_rechaza_texto_desbordado(self):
        with pytest.raises(ValidationError):
            _narrativa(interpretacion='x' * 900)

    def test_rechaza_nivel_de_confianza_inventado(self):
        with pytest.raises(ValidationError):
            _narrativa(nivel_confianza='altísima')

    def test_rechaza_tipo_incorrecto(self):
        with pytest.raises(ValidationError):
            _narrativa(es_normal='puede ser')

    def test_normaliza_espacios(self):
        n = _narrativa(hallazgo='  Se   observa\n\nun cromosoma 21 adicional.  ')
        assert n.hallazgo == 'Se observa un cromosoma 21 adicional.'

    def test_limpia_las_anomalias(self):
        n = _narrativa(anomalias_citadas=[' +21 ', '', '  ', '+ 18'])
        assert n.anomalias_citadas == ['+21', '+18']

    def test_parsea_desde_json(self):
        crudo = (
            '{"hallazgo": "' + HALLAZGO + '", "interpretacion": "' + INTERPRETACION + '",'
            ' "es_normal": false, "anomalias_citadas": ["+21"], "nivel_confianza": "media"}'
        )
        assert NarrativaCariotipo.model_validate_json(crudo).anomalias_citadas == ['+21']

    def test_prosa_en_vez_de_json_no_valida(self):
        """El fallo típico de un LLM: responder texto donde se pidió un objeto."""
        with pytest.raises(ValidationError):
            NarrativaCariotipo.model_validate_json('El cariotipo es normal.')


class TestCoherenciaConElIscn:
    """Capa 2 — el contenido. Acá se evita el diagnóstico falso."""

    def test_acepta_anomalia_presente_en_el_iscn(self):
        ok, motivo = _narrativa().es_coherente_con('47,XY,+21')
        assert ok and motivo == ''

    def test_bloquea_trisomia_inventada(self):
        """Objeto bien formado, diagnóstico falso: `+21` sobre un `46,XX`."""
        ok, motivo = _narrativa().es_coherente_con('46,XX')
        assert not ok
        assert '+21' in motivo

    def test_bloquea_anomalia_de_otro_cromosoma(self):
        """Confundir +18 con +21 cambia el diagnóstico: Edwards vs Down."""
        ok, _ = _narrativa(anomalias_citadas=['+18']).es_coherente_con('47,XY,+21')
        assert not ok

    def test_bloquea_estructural_inventada(self):
        ok, _ = _narrativa(anomalias_citadas=['del(5p)']).es_coherente_con('46,XX')
        assert not ok

    def test_acepta_estructural_presente(self):
        ok, _ = _narrativa(anomalias_citadas=['del(5p)']).es_coherente_con('46,XX,del(5p)')
        assert ok

    def test_bloquea_normal_declarado_sobre_iscn_con_anomalias(self):
        n = _narrativa(es_normal=True, anomalias_citadas=[])
        ok, motivo = n.es_coherente_con('47,XY,+21')
        assert not ok
        assert 'normal' in motivo

    def test_bloquea_anormal_declarado_sobre_iscn_normal(self):
        n = _narrativa(es_normal=False, anomalias_citadas=[])
        ok, _ = n.es_coherente_con('46,XX')
        assert not ok

    def test_cariotipo_normal_coherente(self):
        n = _narrativa(es_normal=True, anomalias_citadas=[])
        ok, _ = n.es_coherente_con('46,XX')
        assert ok

    def test_ignora_espacios_y_mayusculas(self):
        ok, _ = _narrativa(anomalias_citadas=['+21']).es_coherente_con('47, XY, +21')
        assert ok

    def test_turner_es_normal_estructuralmente(self):
        """45,X no tiene componentes extra: el sexo va en su propio campo."""
        n = _narrativa(es_normal=True, anomalias_citadas=[])
        ok, _ = n.es_coherente_con('45,X')
        assert ok


class TestTextoPlano:
    def test_concatena_hallazgo_e_interpretacion(self):
        texto = _narrativa().como_texto()
        assert texto.startswith(HALLAZGO)
        assert INTERPRETACION in texto


class TestEsquemaJson:
    """Lo que se envía en `response_format` a la API."""

    def test_declara_strict(self):
        assert NARRATIVA_JSON_SCHEMA['type'] == 'json_schema'
        assert NARRATIVA_JSON_SCHEMA['json_schema']['strict'] is True

    def test_no_admite_campos_extra(self):
        assert NARRATIVA_JSON_SCHEMA['json_schema']['schema']['additionalProperties'] is False

    def test_declara_los_campos_requeridos(self):
        req = NARRATIVA_JSON_SCHEMA['json_schema']['schema']['required']
        assert {'hallazgo', 'interpretacion', 'es_normal'} <= set(req)
