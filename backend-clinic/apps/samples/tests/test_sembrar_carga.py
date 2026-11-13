"""DD-OBS-001 T4 — el seed de la prueba de carga: muestras con una metafase sintética."""
import json
import os
import random
import struct
import zlib
from pathlib import Path

import numpy as np
import pytest
from django.core.management import call_command

from apps.samples.management.commands.sembrar_carga import (
    ALTO, ANCHO, PREFIJO, metafase_sintetica, png_gris,
)
from apps.samples.models import Sample, SampleImage
from apps.samples.pipeline_client import pipeline_client

from .conftest import auth_client

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def media_temporal(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path / 'media')


def sembrar(salida: Path, **opciones) -> list[str]:
    call_command('sembrar_carga', salida=salida, stdout=open(os.devnull, 'w'), **{'muestras': 3, **opciones})
    return json.loads((salida / 'ids.json').read_text(encoding='utf-8'))


def leer_png(datos: bytes) -> np.ndarray:
    """Decodificador mínimo, para comprobar el PNG sin depender de OpenCV."""
    assert datos[:8] == b'\x89PNG\r\n\x1a\n'
    pos, trozos = 8, {}
    while pos < len(datos):
        largo, tipo = struct.unpack('>I4s', datos[pos:pos + 8])
        cuerpo = datos[pos + 8:pos + 8 + largo]
        (crc,) = struct.unpack('>I', datos[pos + 8 + largo:pos + 12 + largo])
        assert crc == zlib.crc32(tipo + cuerpo) & 0xFFFFFFFF
        trozos[tipo] = trozos.get(tipo, b'') + cuerpo
        pos += 12 + largo
    ancho, alto, bits, color = struct.unpack('>IIBB', trozos[b'IHDR'][:10])
    assert (bits, color) == (8, 0)
    filas = np.frombuffer(zlib.decompress(trozos[b'IDAT']), dtype=np.uint8).reshape(alto, ancho + 1)
    assert not filas[:, 0].any()        # filtro 0 en todas las filas
    return filas[:, 1:]


def test_el_png_se_puede_leer_y_devuelve_la_misma_imagen():
    imagen = np.arange(6 * 4, dtype=np.uint8).reshape(4, 6) * 10
    assert (leer_png(png_gris(imagen)) == imagen).all()


def test_la_metafase_sintetica_tiene_46_manchas_oscuras_sobre_blanco():
    imagen = metafase_sintetica(random.Random(1))

    assert imagen.shape == (ALTO, ANCHO)
    oscuro = imagen < 128
    assert 0.01 < oscuro.mean() < 0.10          # hay tinta, pero casi todo es fondo
    assert imagen[0, 0] == 255


def test_la_metafase_sintetica_es_reproducible():
    assert (metafase_sintetica(random.Random(5)) == metafase_sintetica(random.Random(5))).all()
    assert (metafase_sintetica(random.Random(5)) != metafase_sintetica(random.Random(6))).any()


def test_crea_las_muestras_con_su_imagen_guardada(tmp_path, settings):
    ids = sembrar(tmp_path)

    assert len(ids) == 3
    muestras = Sample.objects.filter(chn_code__startswith=PREFIJO)
    assert sorted(str(m.id) for m in muestras) == sorted(ids)
    for muestra in muestras:
        (imagen,) = SampleImage.objects.filter(sample=muestra)
        datos = (Path(settings.MEDIA_ROOT) / imagen.image_path).read_bytes()
        assert leer_png(datos).shape == (ALTO, ANCHO)
        assert muestra.karyotype.chromosomes.count() == 46
        assert muestra.patient_ref.startswith('ANON-CARGA-')


def test_repetirlo_no_duplica_y_devuelve_los_mismos_ids(tmp_path):
    primera = sembrar(tmp_path)
    segunda = sembrar(tmp_path)

    assert primera == segunda
    assert Sample.objects.filter(chn_code__startswith=PREFIJO).count() == 3


def test_pedir_mas_muestras_conserva_las_que_habia(tmp_path):
    tres = sembrar(tmp_path, muestras=3)
    cinco = sembrar(tmp_path, muestras=5)

    assert cinco[:3] == tres and len(cinco) == 5


def test_la_misma_semilla_da_los_mismos_ids_en_una_base_vacia(tmp_path):
    primera = sembrar(tmp_path, semilla=7)
    Sample.objects.filter(chn_code__startswith=PREFIJO).delete()

    assert sembrar(tmp_path, semilla=7) == primera
    Sample.objects.filter(chn_code__startswith=PREFIJO).delete()
    assert sembrar(tmp_path, semilla=8) != primera


def test_la_muestra_sembrada_se_puede_procesar_con_el_token_del_banco(tmp_path, monkeypatch):
    """Lo que hará k6: `POST …/process/` con el usuario del banco. backend-ml se
    sustituye; lo que se comprueba es que llegan los bytes de la metafase."""
    ids = sembrar(tmp_path)
    recibidos = {}

    def segmentar(image_bytes, filename='x'):
        recibidos['imagen'] = image_bytes
        return {'model_version': 'prueba', 'chromosomes': [
            {'order': 0, 'predicted_class': '1', 'confidence_score': 0.9,
             'bbox': {'x': 1, 'y': 1, 'w': 10, 'h': 20}, 'area': 100}]}

    monkeypatch.setattr(pipeline_client, 'segment_image', segmentar)
    analista = Sample.objects.get(id=ids[0]).analyst

    respuesta = auth_client(analista).post(f'/api/clinic/samples/{ids[0]}/process/', {}, format='json')

    assert respuesta.status_code == 200, respuesta.content
    assert respuesta.json()['chromosome_count'] == 1
    assert leer_png(recibidos['imagen']).shape == (ALTO, ANCHO)
