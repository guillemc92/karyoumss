"""El contrato OpenAPI de backend-clinic (DD-API-001).

Lo que se fija aquí, en local, antes de que llegue al CI:

- el `openapi.json` del repositorio es EXACTAMENTE el que genera el código
  (drift): si alguien cambia una vista o un serializer y no regenera, falla;
- generar dos veces da el mismo contrato (si no, el drift fallaría solo);
- están todos los endpoints de la corrección manual (DD-KARYO-007), con su
  cuerpo de entrada y cada código de error que devuelven de verdad;
- el contrato no contiene datos de pacientes ni secretos (RN-03).
"""
import json
from pathlib import Path

import pytest
from django.core.management import call_command

RAIZ = Path(__file__).resolve().parents[3]
ARCHIVO = RAIZ / 'openapi.json'
P = '/api/clinic/samples/{id}'


def _generar(tmp_path, nombre='contrato.json') -> str:
    destino = tmp_path / nombre
    call_command('spectacular', '--format', 'openapi-json', '--file', str(destino), '--validate')
    return destino.read_text(encoding='utf-8')


@pytest.fixture(scope='module')
def contrato(tmp_path_factory):
    return json.loads(_generar(tmp_path_factory.mktemp('contrato')))


def test_el_archivo_del_repositorio_es_el_que_genera_el_codigo(tmp_path):
    """El mismo chequeo que el drift del CI, para cazarlo antes del PR."""
    assert ARCHIVO.exists(), 'falta backend-clinic/openapi.json: exportarlo con manage.py spectacular'
    assert _generar(tmp_path) == ARCHIVO.read_text(encoding='utf-8'), (
        'openapi.json está desactualizado: python manage.py spectacular --format openapi-json '
        '--file openapi.json --validate')


def test_generar_dos_veces_da_lo_mismo(tmp_path):
    assert _generar(tmp_path, 'a.json') == _generar(tmp_path, 'b.json')


ENDPOINTS = {
    # (ruta, método): códigos que la vista devuelve de verdad
    (f'{P}/karyotype/', 'get'): {'200', '401', '403', '404'},
    (f'{P}/karyotype/metaphase/', 'get'): {'200', '401', '403', '404'},
    (f'{P}/karyotype/contours/', 'post'): {'200', '401', '403', '404', '409', '503'},
    (f'{P}/karyotype/objects/', 'post'): {'201', '400', '401', '403', '404', '409', '503'},
    (f'{P}/karyotype/undo/', 'get'): {'200', '401', '403', '404'},
    (f'{P}/karyotype/undo/', 'post'): {'200', '401', '403', '404', '409'},
    (f'{P}/chromosomes/{{cid}}/reject/', 'post'): {'200', '400', '401', '403', '404', '409'},
    (f'{P}/chromosomes/{{cid}}/split/', 'post'): {'201', '400', '401', '403', '404', '409', '422', '503'},
    (f'{P}/chromosomes/{{cid}}/join/', 'post'): {'200', '400', '401', '403', '404', '409'},
    (f'{P}/chromosomes/{{cid}}/recrop/', 'post'): {'200', '400', '401', '403', '404', '409'},
    (f'{P}/chromosomes/{{cid}}/orient/', 'post'): {'200', '400', '401', '403', '404', '409'},
}


@pytest.mark.parametrize('ruta, metodo', sorted(ENDPOINTS))
def test_los_endpoints_de_la_correccion_manual_estan_descritos(contrato, ruta, metodo):
    operacion = contrato['paths'][ruta][metodo]
    assert set(operacion['responses']) == ENDPOINTS[(ruta, metodo)]
    assert operacion['tags'][0] in {'Cariotipo', 'Corrección manual'}
    assert operacion.get('summary'), 'sin resumen: el contrato no dice qué hace'
    assert {'jwtBackendAdmin': []} in operacion['security']


def _esquema(contrato, ref):
    return contrato['components']['schemas'][ref.rsplit('/', 1)[-1]]


def _cuerpo(contrato, ruta, metodo):
    ref = contrato['paths'][ruta][metodo]['requestBody']['content']['application/json']['schema']['$ref']
    return _esquema(contrato, ref)


def test_separar_exige_la_linea(contrato):
    cuerpo = _cuerpo(contrato, f'{P}/chromosomes/{{cid}}/split/', 'post')
    assert cuerpo['required'] == ['linea']
    assert cuerpo['properties']['linea']['minItems'] == 2


def test_descartar_lista_los_motivos(contrato):
    cuerpo = _cuerpo(contrato, f'{P}/chromosomes/{{cid}}/reject/', 'post')
    motivo = _esquema(contrato, cuerpo['properties']['motivo']['$ref'])
    assert sorted(motivo['enum']) == ['duplicado', 'nucleo', 'otro', 'suciedad']


def test_orientar_solo_admite_0_y_180(contrato):
    cuerpo = _cuerpo(contrato, f'{P}/chromosomes/{{cid}}/orient/', 'post')
    giro = _esquema(contrato, cuerpo['properties']['giro']['$ref'])
    assert giro['enum'] == [0, 180]
    assert set(cuerpo['required']) == {'giro', 'volteo'}


def test_el_cromosoma_publica_su_silueta(contrato):
    """La pieza que el frontend lee para pintar la metafase (DD-KARYO-007 D1).
    Es la que se rompe a propósito en la demo (DD-API-001 D5)."""
    cromosoma = contrato['components']['schemas']['Chromosome']
    assert 'contour' in cromosoma['properties']
    assert 'bbox' in cromosoma['properties']


def test_los_demas_quedan_declarados_como_sin_describir(contrato):
    """La deuda de DD-API-001 D2 se ve en el contrato, no se esconde."""
    sin_describir = [op for p in contrato['paths'].values() for op in p.values()
                     if 'Sin describir' in op.get('tags', [])]
    assert sin_describir, 'si ya no queda ninguno, actualizar DD-API-001 D2'
    for op in sin_describir:
        assert 'DD-API-001' in op['responses']['200']['description']


def test_sin_datos_de_pacientes_ni_secretos():
    texto = ARCHIVO.read_text(encoding='utf-8').lower()
    for prohibido in ('secret_key', 'password":', 'jwt_secret', 'paciente e2e', 'patient_name'):
        assert prohibido not in texto
