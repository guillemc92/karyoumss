"""Seed de la prueba de carga con trazas (DD-OBS-001 D6).

    python manage.py sembrar_carga --muestras 20 --salida /k6data

Crea muestras ficticias, cada una con una metafase SINTÉTICA guardada, para que
`POST /samples/{id}/process/` haga el recorrido completo: backend-clinic lee la
imagen, backend-ml la segmenta y la clasifica, y backend-clinic guarda el
cariotipo.

No hay PII (RN-03): ni pacientes ni imágenes reales. La metafase es un dibujo:
46 manchas alargadas sobre fondo blanco.

Se puede repetir: si las muestras ya existen, solo vuelve a escribir `ids.json`.
"""
import json
import random
import struct
import uuid
import zlib
from decimal import Decimal
from pathlib import Path

import numpy as np
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.samples.models import Chromosome, Karyotype, Sample, SampleImage

from .sembrar_bench import CLASES, USUARIO_BENCH

PREFIJO = 'CHN-CARGA-'
ANCHO, ALTO = 1024, 768
CROMOSOMAS = 46
MARGEN = 40          # media ventana: mayor que el semieje más largo (34)


def png_gris(imagen: np.ndarray) -> bytes:
    """Codifica una matriz uint8 de un canal como PNG, solo con la biblioteca
    estándar: la imagen de backend-clinic no lleva OpenCV ni Pillow."""
    alto, ancho = imagen.shape

    def trozo(tipo: bytes, datos: bytes) -> bytes:
        return (struct.pack('>I', len(datos)) + tipo + datos
                + struct.pack('>I', zlib.crc32(tipo + datos) & 0xFFFFFFFF))

    filas = b''.join(b'\x00' + imagen[y].tobytes() for y in range(alto))
    return (b'\x89PNG\r\n\x1a\n'
            + trozo(b'IHDR', struct.pack('>IIBBBBB', ancho, alto, 8, 0, 0, 0, 0))
            + trozo(b'IDAT', zlib.compress(filas, 6))
            + trozo(b'IEND', b''))


def metafase_sintetica(rng: random.Random, cromosomas: int = CROMOSOMAS) -> np.ndarray:
    """Fondo blanco con `cromosomas` elipses oscuras, giradas y sin tocarse."""
    imagen = np.full((ALTO, ANCHO), 255, dtype=np.uint8)
    centros: list[tuple[int, int]] = []
    intentos = 0
    while len(centros) < cromosomas and intentos < 5000:
        intentos += 1
        cx, cy = rng.randint(60, ANCHO - 60), rng.randint(60, ALTO - 60)
        if any(abs(cx - px) < 70 and abs(cy - py) < 70 for px, py in centros):
            continue
        centros.append((cx, cy))
        largo, grueso = rng.randint(18, 34), rng.randint(6, 9)
        angulo = rng.uniform(0, np.pi)
        # La elipse se calcula solo en una ventana alrededor de su centro, no
        # sobre la imagen entera: los centros están a 60 px o más del borde, así que cabe.
        ventana = imagen[cy - MARGEN:cy + MARGEN, cx - MARGEN:cx + MARGEN]
        dy, dx = np.mgrid[-MARGEN:MARGEN, -MARGEN:MARGEN]
        u = dx * np.cos(angulo) + dy * np.sin(angulo)
        v = -dx * np.sin(angulo) + dy * np.cos(angulo)
        ventana[(u / largo) ** 2 + (v / grueso) ** 2 <= 1] = rng.randint(30, 90)
    return imagen


class Command(BaseCommand):
    help = 'Seed sin PII para la prueba de carga con trazas (DD-OBS-001).'

    def add_arguments(self, parser):
        parser.add_argument('--semilla', type=int, default=42)
        parser.add_argument('--muestras', type=int, default=20)
        parser.add_argument('--salida', type=Path, required=True, help='Carpeta donde escribir ids.json')

    def handle(self, *args, semilla, muestras, salida, **opts):
        analista, _ = get_user_model().objects.get_or_create(
            username=USUARIO_BENCH, defaults={'email': USUARIO_BENCH})

        nuevas = 0
        for i in range(muestras):
            chn = f'{PREFIJO}{i:05d}'
            # Un generador por muestra: su id y su imagen no dependen de cuántas
            # muestras había ni de cuántas se piden.
            rng = random.Random(f'{semilla}-{i}')
            if Sample.objects.filter(chn_code=chn).exists():
                continue
            ident = uuid.UUID(int=rng.getrandbits(128), version=4)
            imagen = png_gris(metafase_sintetica(rng))
            sample = Sample.objects.create(id=ident, chn_code=chn, patient_ref=f'ANON-CARGA-{i:05d}',
                                           analyst=analista, status='READY')
            relativa = f'{chn}/metafase.png'
            ruta = Path(settings.MEDIA_ROOT) / relativa
            ruta.parent.mkdir(parents=True, exist_ok=True)
            ruta.write_bytes(imagen)
            SampleImage.objects.create(sample=sample, image_path=relativa, order=0, source='upload')
            karyo = Karyotype.objects.create(sample=sample)
            Chromosome.objects.bulk_create([
                Chromosome(karyotype=karyo, predicted_class=clase, order=n, position_index=n % 2,
                           confidence_score=Decimal(rng.randint(700, 999)) / 1000)
                for n, clase in enumerate(CLASES)
            ])
            nuevas += 1

        ids = [str(i) for i in Sample.objects.filter(chn_code__startswith=PREFIJO)
               .order_by('chn_code').values_list('id', flat=True)]
        salida.mkdir(parents=True, exist_ok=True)
        (salida / 'ids.json').write_text(json.dumps(ids), encoding='utf-8')
        self.stdout.write(f'{nuevas} muestras nuevas, {len(ids)} en total; ids en {salida / "ids.json"}')
