"""Qué metafase es la del cariotipo y cómo se entrega (DD-KARYO-006).

## Una sola elección de la metafase (D4)

`metafase_segmentada()` es la imagen con la que se calcularon las cajas del
cariotipo. Antes esa elección estaba escrita tres veces en `services.py`
(reprocesar, explicación XAI y recorte); si una cambiaba y otra no, el visor
mostraría una imagen y las cajas apuntarían a otra.

## Una imagen se reconoce por su contenido, no por su firma (D2, D5)

Las metafases se guardan con extensión `.img`, así que el tipo sale de los
bytes. Pero mirar solo la firma no basta. Medido el 13/10 sobre `media/`:
de 1.312 ficheros, solo 40 son imágenes; el resto son marcadores que dejan
tests y seeds, y **350 de ellos empiezan con una firma válida**:

    148  b'BM' + ceros                         BMP sin dimensiones
     24  b'BM6' ...  (54 bytes)                cabecera BMP sin píxeles
    178  b'\\xff\\xd8\\xff\\xe0' + b'00000000'     JPEG sin fin de imagen

Con una comprobación de firma, el navegador recibiría esos bytes como imagen y
pintaría una imagen rota en lugar de caer a los rectángulos de siempre. Por
eso cada formato exige algo que un marcador no tiene: el BMP, dimensiones y
datos de píxeles; el JPEG, su marca de fin; el PNG, su bloque `IHDR`.

## La ruta no sale de MEDIA_ROOT (D6)

`image_path` viene de la base de datos; se resuelve y se comprueba que queda
dentro de `MEDIA_ROOT` antes de abrir nada. La ruta nunca se devuelve al cliente.
"""
from __future__ import annotations

import struct
from pathlib import Path

from django.conf import settings

_CABECERA = 64


def metafase_segmentada(sample):
    """La imagen de la muestra sobre la que se segmentó el cariotipo."""
    return sample.images.order_by('order', 'captured_at').first()


def ruta_segura(image_path: str) -> Path | None:
    """Ruta absoluta del fichero si existe y está dentro de MEDIA_ROOT."""
    if not image_path:
        return None
    raiz = Path(settings.MEDIA_ROOT).resolve()
    ruta = (raiz / image_path).resolve()
    if ruta != raiz and raiz not in ruta.parents:
        return None
    return ruta if ruta.is_file() else None


def _es_bmp(cabeza: bytes, tamano: int) -> bool:
    """Un BMP con dimensiones y TODOS los bytes de píxeles que declaran.

    No basta con «hay algún píxel»: un fichero truncado también lo cumple, y el
    navegador lo pintaría a medias. Cada fila ocupa un múltiplo de 4 bytes.
    """
    if len(cabeza) < 30 or not cabeza.startswith(b'BM'):
        return False
    inicio_pixeles = struct.unpack('<I', cabeza[10:14])[0]
    ancho, alto = struct.unpack('<ii', cabeza[18:26])
    bits = struct.unpack('<H', cabeza[28:30])[0]
    if ancho <= 0 or alto == 0 or bits == 0 or inicio_pixeles < 26:
        return False
    fila = ((ancho * bits + 31) // 32) * 4
    return tamano - inicio_pixeles >= fila * abs(alto)


def _es_png(cabeza: bytes) -> bool:
    return cabeza.startswith(b'\x89PNG\r\n\x1a\n') and cabeza[12:16] == b'IHDR'


def _es_jpeg(cabeza: bytes, cola: bytes) -> bool:
    return cabeza.startswith(b'\xff\xd8\xff') and cola == b'\xff\xd9'


def tipo_de_imagen(ruta: Path) -> str | None:
    """`image/bmp`, `image/png`, `image/jpeg`, o None si no es una imagen."""
    tamano = ruta.stat().st_size
    with open(ruta, 'rb') as f:
        cabeza = f.read(_CABECERA)
        f.seek(max(tamano - 2, 0))
        cola = f.read(2)
    if _es_bmp(cabeza, tamano):
        return 'image/bmp'
    if _es_png(cabeza):
        return 'image/png'
    if _es_jpeg(cabeza, cola):
        return 'image/jpeg'
    return None
