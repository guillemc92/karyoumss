"""El contrato OpenAPI de backend-ml (DD-API-001).

- `backend-ml/openapi.json` es exactamente el que exporta el código (drift);
- exportar dos veces da lo mismo;
- las operaciones de edición de la metafase (DD-KARYO-007) están, con sus errores.
"""
import json
from pathlib import Path

import pytest

from app import exportar_openapi
from app.exportar_openapi import POR_DEFECTO, contrato

ARCHIVO = Path(__file__).resolve().parent.parent / 'openapi.json'


def test_el_archivo_del_repositorio_es_el_que_genera_el_codigo():
    assert ARCHIVO == POR_DEFECTO
    assert ARCHIVO.exists(), 'falta backend-ml/openapi.json: python -m app.exportar_openapi'
    assert contrato() == ARCHIVO.read_text(encoding='utf-8'), (
        'openapi.json está desactualizado: python -m app.exportar_openapi')


def test_exportar_dos_veces_da_lo_mismo():
    assert contrato() == contrato()


def test_el_comando_escribe_donde_se_le_pide(tmp_path):
    salida = exportar_openapi.main(['--salida', str(tmp_path / 'x.json')])
    assert json.loads(salida.read_text(encoding='utf-8'))['info']['version'] == '8.2.0'


@pytest.mark.parametrize('ruta, codigos', [
    ('/api/v1/split/', {'200', '400', '422'}),
    ('/api/v1/join/', {'200', '400', '422'}),
    ('/api/v1/contours/', {'200', '400', '422'}),
])
def test_las_operaciones_de_edicion_estan_descritas(ruta, codigos):
    operacion = json.loads(contrato())['paths'][ruta]['post']
    assert set(operacion['responses']) == codigos
    assert operacion['tags'] == ['Edición de la metafase']


def test_separar_devuelve_los_trozos():
    esquemas = json.loads(contrato())['components']['schemas']
    trozo = esquemas['TrozoOut']['properties']
    assert {'contour', 'bbox', 'area'} <= set(trozo)
