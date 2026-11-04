"""DD-OPS-001 D3: la variable gana, después el archivo de BIOMED_SECRETS_DIR, después el defecto."""
import pytest

from admin_backend.entorno import env


@pytest.fixture
def carpeta(tmp_path, monkeypatch):
    monkeypatch.setenv('BIOMED_SECRETS_DIR', str(tmp_path))
    monkeypatch.delenv('BIOMED_PRUEBA', raising=False)
    return tmp_path


def test_la_variable_gana_al_archivo(carpeta, monkeypatch):
    (carpeta / 'BIOMED_PRUEBA').write_text('del-archivo', encoding='utf-8')
    monkeypatch.setenv('BIOMED_PRUEBA', 'de-la-variable')
    assert env('BIOMED_PRUEBA', required=True) == 'de-la-variable'


def test_sin_variable_se_lee_el_archivo_sin_el_salto_de_linea(carpeta):
    (carpeta / 'BIOMED_PRUEBA').write_text('del-archivo\n', encoding='utf-8')
    assert env('BIOMED_PRUEBA', 'defecto') == 'del-archivo'


def test_sin_variable_ni_archivo_vale_el_defecto(carpeta):
    assert env('BIOMED_PRUEBA', 'defecto') == 'defecto'


def test_sin_carpeta_no_se_busca_archivo(monkeypatch):
    monkeypatch.delenv('BIOMED_SECRETS_DIR', raising=False)
    monkeypatch.delenv('BIOMED_PRUEBA', raising=False)
    assert env('BIOMED_PRUEBA') is None


def test_un_secreto_obligatorio_sin_fuentes_sigue_fallando(carpeta):
    with pytest.raises(RuntimeError, match='BIOMED_PRUEBA'):
        env('BIOMED_PRUEBA', required=True)


def test_una_carpeta_en_el_nombre_no_cuenta_como_archivo(carpeta):
    (carpeta / 'BIOMED_PRUEBA').mkdir()
    assert env('BIOMED_PRUEBA', 'defecto') == 'defecto'
