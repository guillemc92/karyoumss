"""Tests del motor ISCN (ADR-0023 D4, ADR-0025).

El motor produce un **diagnóstico**: `47,XY,+21` es síndrome de Down. Por eso se
prueba contra síndromes reales y no solo contra casos sintéticos — un error acá
no es un test rojo, es un informe clínico equivocado.

Función pura: no necesitan base de datos ni Django.
"""
import pytest

from apps.samples.iscn import IscnError, generate_iscn, validate_iscn


def _normal(sexo: str) -> dict:
    """Cariotipo normal: 2 copias de cada autosoma + los sexuales."""
    counts = {str(n): 2 for n in range(1, 23)}
    counts.update({'X': 2} if sexo == 'XX' else {'X': 1, 'Y': 1})
    return counts


class TestCariotiposNormales:
    def test_femenino(self):
        assert generate_iscn(_normal('XX')) == '46,XX'

    def test_masculino(self):
        assert generate_iscn(_normal('XY')) == '46,XY'


class TestSindromesReales:
    """Casos clínicos con nomenclatura conocida y publicada."""

    def test_down_trisomia_21(self):
        counts = _normal('XY')
        counts['21'] = 3
        assert generate_iscn(counts) == '47,XY,+21'

    def test_edwards_trisomia_18(self):
        counts = _normal('XX')
        counts['18'] = 3
        assert generate_iscn(counts) == '47,XX,+18'

    def test_patau_trisomia_13(self):
        counts = _normal('XY')
        counts['13'] = 3
        assert generate_iscn(counts) == '47,XY,+13'

    def test_turner_monosomia_x(self):
        """45,X — una sola X, sin Y. El sexo se escribe tal cual, no como -X."""
        counts = {str(n): 2 for n in range(1, 23)}
        counts['X'] = 1
        assert generate_iscn(counts) == '45,X'

    def test_klinefelter_xxy(self):
        """47,XXY — la copia extra de X va en el componente sexual, NO como '+X'."""
        counts = {str(n): 2 for n in range(1, 23)}
        counts.update({'X': 2, 'Y': 1})
        assert generate_iscn(counts) == '47,XXY'

    def test_klinefelter_con_trisomia_21(self):
        counts = {str(n): 2 for n in range(1, 23)}
        counts.update({'X': 2, 'Y': 1, '21': 3})
        assert generate_iscn(counts) == '48,XXY,+21'

    def test_monosomia_autosomica(self):
        counts = _normal('XX')
        counts['21'] = 1
        assert generate_iscn(counts) == '45,XX,-21'


class TestOrdenDeAnomalias:
    """ISCN exige orden numérico ascendente (ADR-0023 D4). Ordenar por string
    daría '+21' antes de '+8' — inválido."""

    def test_18_antes_que_21(self):
        counts = _normal('XY')
        counts['18'] = 3
        counts['21'] = 3
        assert generate_iscn(counts) == '48,XY,+18,+21'

    def test_un_digito_antes_que_dos_digitos(self):
        counts = _normal('XX')
        counts['8'] = 3
        counts['21'] = 3
        assert generate_iscn(counts) == '48,XX,+8,+21'

    def test_ganancia_doble_se_repite(self):
        """Tetrasomía: 4 copias = dos ganancias sobre las 2 normales."""
        counts = _normal('XX')
        counts['21'] = 4
        assert generate_iscn(counts) == '48,XX,+21,+21'


class TestEntradasInvalidas:
    def test_conteo_vacio_no_inventa_un_cariotipo(self):
        """Devolver '46,XX' por defecto sería inventar un diagnóstico."""
        with pytest.raises(IscnError, match='sin cromosomas'):
            generate_iscn({})

    def test_none_no_revienta(self):
        with pytest.raises(IscnError):
            generate_iscn(None)

    def test_sin_sexuales_es_incompleto(self):
        with pytest.raises(IscnError, match='sexuales'):
            generate_iscn({str(n): 2 for n in range(1, 23)})

    def test_ignora_ceros(self):
        counts = _normal('XX')
        counts['Y'] = 0
        assert generate_iscn(counts) == '46,XX'


class TestDeterminismo:
    """Lo que hace auditable el dato clínico (ADR-0025 D4)."""

    def test_mismo_input_mismo_output(self):
        counts = _normal('XY')
        counts['21'] = 3
        assert len({generate_iscn(counts) for _ in range(20)}) == 1

    def test_el_orden_de_las_claves_no_importa(self):
        counts = _normal('XY')
        counts['21'] = 3
        invertido = dict(reversed(list(counts.items())))
        assert generate_iscn(counts) == generate_iscn(invertido)

    def test_no_muta_la_entrada(self):
        counts = _normal('XX')
        copia = dict(counts)
        generate_iscn(counts)
        assert counts == copia


class TestValidacionDeOverride:
    """El Supervisor es la autoridad médica: se valida la GRAMÁTICA, no la
    plausibilidad clínica (puede reportar hallazgos que el motor no deriva)."""

    @pytest.mark.parametrize('iscn', [
        '46,XX', '46,XY', '47,XY,+21', '45,X', '47,XXY', '48,XXY,+21',
        '46,XX,del(5p)', '46,XY,t(9;22)', '47,XX,+21,+18', '46,XY,inv(9)',
    ])
    def test_acepta_nomenclatura_valida(self, iscn):
        assert validate_iscn(iscn) == iscn

    def test_normaliza_espacios(self):
        assert validate_iscn('  47, XY, +21  ') == '47,XY,+21'

    @pytest.mark.parametrize('iscn', [
        '', '   ', 'cuarenta y seis', '46', 'XX', '46-XX',
        '46,ZZ', '46,XX,', 'DROP TABLE samples',
    ])
    def test_rechaza_basura(self, iscn):
        with pytest.raises(IscnError):
            validate_iscn(iscn)

    def test_rechaza_recuento_fuera_de_rango(self):
        with pytest.raises(IscnError, match='rango biológico'):
            validate_iscn('999,XX')

    def test_none_no_revienta(self):
        with pytest.raises(IscnError):
            validate_iscn(None)


class TestRoundTrip:
    """Lo que genera el motor debe pasar su propia validación."""

    @pytest.mark.parametrize('mods', [
        {}, {'21': 3}, {'18': 3}, {'13': 3}, {'21': 1}, {'8': 3, '21': 3},
    ])
    def test_generado_es_valido(self, mods):
        counts = _normal('XY')
        counts.update(mods)
        assert validate_iscn(generate_iscn(counts))
