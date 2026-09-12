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

    # Ejemplos REALES del estándar ISCN 2024, con su sección. No inventados:
    # la versión previa de estos tests usaba formas simplificadas («del(5p)»
    # en vez de «del(5)(q13)») y por eso no detectó que el validador rechazaba
    # el 44% de la nomenclatura legítima.
    @pytest.mark.parametrize('iscn', [
        '46,XX',                          # §5.2 i    femenino normal
        '46,XY',                          # §5.2 ii   masculino normal
        '46,U',                           # §5.2 iii  sexo no revelado
        '45,X',                           # §5.3.1.1  Turner
        '48,XXXY',                        # §5.3.1.1  cuatro sexuales
        '47,XX,+21',                      # §5.3.2 i  Down
        '46,XX,+8,-21',                   # §5.3.2 iv ganancia y pérdida
        '46,XX,del(5)(q13)',              # §5.5.2 i  deleción terminal
        '46,XX,del(5)(q13q33)',           # §5.5.2 iii deleción intersticial
        '46,XY,t(9;22)(q34;q11.2)',       # §5.5.18   Filadelfia
        '46,XX,inv(2)(p23p13)',           # §5.5.10 i inversión paracéntrica
        '46,XX,i(17)(q10)',               # §5.5.11 i isocromosoma
        '46,XX,r(7)(p15q31)',             # §5.5.16.1 anillo
        '46,XX,add(19)(p13.3)',           # §5.5.1 i  material desconocido
        '45,XX,dic(13;15)(q22;q24)',      # §5.5.4 ii dicéntrico
        '46,XY,der(1)t(1;3)(p22;q13.1)',  # §5.5.3 d  derivado encadenado
        '47,XX,+mar',                     # §5.5.12 i marcador
        '47,XX,+der(5)t(2;5)(q21;q31)',   # tabla 5   derivado supernumerario
        '45,XY,psu dic(15;13)(q12;q12)',  # §5.5.4 h  espacio significativo
        '46,X,fra(X)(q27.3)',             # §5.5.7 i  sitio frágil
        '46,XX,del(6)(q13q23)x2',         # §5.6 i    copias múltiples
    ])
    def test_acepta_nomenclatura_del_estandar(self, iscn):
        assert validate_iscn(iscn)

    @pytest.mark.parametrize('iscn', [
        '45,X[13]/46,XY[17]',             # §5.3.1.1 v  mosaico
        'mos 47,XXY[10]/46,XY[20]',       # §5.3.1.1 vi prefijo mos
        '46,XX[5]//46,XY[25]',            # §4.5.3 iii  quimera post-trasplante
        '45~48,XX,+8[cp10]',              # §4.2.1 j    cariotipo compuesto
        '47,XY,+mar dn[14]/46,XY[16]',    # §4.4.1 b    dos abreviaturas
    ])
    def test_acepta_mosaicismo_y_recuentos(self, iscn):
        """El Supervisor necesita reportar mosaicismo; rechazarlo le bloquea
        trabajo legítimo."""
        assert validate_iscn(iscn)

    @pytest.mark.parametrize('iscn', [
        '47,XX,+21c',                     # §4.2.1 e  constitucional
        '46,XX,t(5;6)(q34;q23)mat',       # §4.2.1 g  origen materno
        '46,XY,?del(1)(p36.1)',           # §4.2.1 k  identificación dudosa
        '47,XX,+?8',                      # §4.2.1 k  cromosoma dudoso
    ])
    def test_acepta_sufijos_y_dudas(self, iscn):
        assert validate_iscn(iscn)

    def test_preserva_el_espacio_significativo(self):
        """§4.4.1: el espacio SÍ es significativo entre dos abreviaturas.
        Borrarlo convertiría «psu dic» en «psudic» y corrompería el dato."""
        assert validate_iscn('45,XY, psu dic(15;13)(q12;q12)') ==             '45,XY,psu dic(15;13)(q12;q12)'

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


class TestConteosQueProducirianUnIscnFalso:
    """El generador no puede confiar en su entrada.

    El fallo que esto cubre es el peor de todos: no romper nada y emitir un
    diagnóstico verosímil pero falso.
    """

    def test_una_clase_desconocida_no_infla_el_recuento_en_silencio(self):
        """Antes producía `48,XX`: 48 cromosomas y CERO anomalías listadas —
        internamente contradictorio (48 exige dos ganancias) pero con toda la
        apariencia de un cariotipo válido."""
        counts = _normal('XX')
        counts['ZZ'] = 2                      # etiqueta que el sistema no conoce
        with pytest.raises(IscnError, match='no reconocidas'):
            generate_iscn(counts)

    def test_es_alcanzable_desde_el_pipeline(self):
        """`ingest_segmentation` copia `predicted_class` tal como llega de
        backend-ml, y Django no valida `choices` en `save()`. Una etiqueta
        inesperada del modelo llega hasta acá."""
        counts = _normal('XY')
        counts['23'] = 2                      # cromosoma 23 no existe
        with pytest.raises(IscnError, match='no reconocidas'):
            generate_iscn(counts)

    def test_clase_vacia_rechazada(self):
        counts = _normal('XX')
        counts[''] = 3
        with pytest.raises(IscnError, match='no reconocidas'):
            generate_iscn(counts)

    def test_el_mensaje_nombra_la_clase_culpable(self):
        """Sin el nombre, diagnosticar de dónde vino la etiqueta es adivinar."""
        counts = _normal('XX')
        counts['ZZ'] = 1
        with pytest.raises(IscnError, match="'ZZ'"):
            generate_iscn(counts)

    def test_conteo_negativo_rechazado(self):
        """Producía `-21,-21,-21`: perder tres copias de un cromosoma que
        tiene dos."""
        counts = _normal('XX')
        counts['21'] = -1
        with pytest.raises(IscnError, match='negativo'):
            generate_iscn(counts)

    def test_recuento_fuera_de_rango_biologico(self):
        with pytest.raises(IscnError, match='rango biológico'):
            generate_iscn({'X': 2})           # un cariotipo de 2 cromosomas

    def test_el_generador_nunca_produce_algo_que_su_validador_rechace(self):
        """Propiedad de consistencia interna. Antes se rompía: `generate_iscn`
        no comprobaba el rango que `validate_iscn` sí exige."""
        for mods in ({}, {'21': 3}, {'18': 3}, {'21': 1}, {'8': 4}, {'8': 3, '21': 1}):
            for sexo in ('XX', 'XY'):
                counts = _normal(sexo)
                counts.update(mods)
                validate_iscn(generate_iscn(counts))


class TestGeneraNomenclaturaDelEstandar:
    """Salida contrastada contra ejemplos publicados en ISCN 2024."""

    @pytest.mark.parametrize('sexo_counts, esperado, ref', [
        ({'X': 1},               '45,X',      '§5.3.1.1 i   Turner'),
        ({'X': 3},               '47,XXX',    '§5.3.1.1 ii  triple X'),
        ({'X': 1, 'Y': 2},       '47,XYY',    '§5.3.1.1 iii XYY'),
        ({'X': 3, 'Y': 1},       '48,XXXY',   '§5.3.1.1 iv  XXXY'),
        ({'X': 2, 'Y': 1},       '47,XXY',    '§4.2.1 e     Klinefelter'),
    ])
    def test_complemento_sexual(self, sexo_counts, esperado, ref):
        """§5.1 f: los sexuales se escriben tal cual, NUNCA con +/-."""
        counts = {str(n): 2 for n in range(1, 23)}
        counts.update(sexo_counts)
        assert generate_iscn(counts) == esperado

    @pytest.mark.parametrize('mods, esperado, ref', [
        ({'21': 3},           '47,XX,+21',      '§5.3.2 i   Down'),
        ({'13': 3, '21': 3},  '48,XX,+13,+21',  '§5.3.2 ii  doble trisomía'),
        ({'22': 1},           '45,XX,-22',      '§5.3.2 iii monosomía 22'),
        ({'8': 3, '21': 1},   '46,XX,+8,-21',   '§5.3.2 iv  ganancia y pérdida'),
        ({'8': 4},            '48,XX,+8,+8',    'tabla 8 #17 tetrasomía'),
    ])
    def test_anomalias_autosomicas(self, mods, esperado, ref):
        """§4.3: orden cromosómico, ganancias antes que pérdidas."""
        counts = _normal('XX')
        counts.update(mods)
        assert generate_iscn(counts) == esperado
