pytestmark = pytest.mark.agente

def test_cariotipo_femenino_normal():
    counts = _normal('XX')
    assert generate_iscn(counts) == '46,XX'

def test_cariotipo_masculino_normal():
    counts = _normal('XY')
    assert generate_iscn(counts) == '46,XY'

def test_trisomia_21():
    counts = {'21': 3}
    assert generate_iscn(counts) == '47,XX,+21'

def test_monosomia_X():
    counts = {'X': 1}
    assert generate_iscn(counts) == '45,XX,-X'

def test_klinefelter():
    counts = {'21': 1}
    assert generate_iscn(counts) == '47,XX,+21'

def test_conteo_vacio():
    counts = {}
    assert generate_iscn(counts) == ''

def test_cariotipo_femenino_trisomia_13():
    counts = {'13': 3}
    assert generate_iscn(counts) == '48,XX,+13'

def test_cariotipo_masculino_trisomia_8():
    counts = {'8': 3}
    assert generate_iscn(counts) == '47,XY,+8'
