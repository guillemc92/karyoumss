"""Lectura de dimensiones de imagen sin dependencias externas.

backend-clinic no tiene Pillow instalado y no merece la pena añadirlo solo para
leer dos enteros de una cabecera. Estas funciones leen el ancho y el alto
directamente del formato, sin decodificar los píxeles.

## Por qué existe esto

Un recorte de un cromosoma suelto (60x119 px) se aceptaba como si fuera una
metafase: el pipeline lo segmentaba, encontraba un objeto y producía un
cariotipo de un cromosoma. Basura entra, cariotipo sale, y sin una sola
advertencia. En un sistema clínico eso no puede pasar en silencio.

## De dónde sale el umbral

Medido sobre las 460 metafases del archivo del laboratorio
(`datasets/metaclass/metafases/`): la más pequeña es 1024x768 y la mayor
1280x1290. Los recortes que provocaron el fallo iban de 60x119 a 405x305.

640x480 deja un margen amplio por ambos lados: ninguna metafase real se acerca
por abajo, ningún recorte se acerca por arriba.
"""
import struct

#: Dimensiones mínimas para aceptar una imagen como metafase (ver docstring).
ANCHO_MINIMO = 640
ALTO_MINIMO = 480

_PNG_FIRMA = b'\x89PNG\r\n\x1a\n'


def dimensiones(raw: bytes) -> tuple[int, int] | None:
    """Ancho y alto en píxeles, o None si el formato no se reconoce.

    Devolver None no es un error: significa «no lo sé». Quien llama decide, y
    aquí se decide dejar pasar lo desconocido en vez de bloquear un formato
    legítimo que no contemplamos.
    """
    for lector in (_bmp, _png, _jpeg):
        try:
            medida = lector(raw)
        except (struct.error, IndexError, ValueError):
            continue
        if medida:
            return medida
    return None


def es_metafase_plausible(raw: bytes) -> bool:
    """False solo si se pudo medir la imagen Y es demasiado pequeña."""
    medida = dimensiones(raw)
    if medida is None:
        return True
    ancho, alto = medida
    return ancho >= ANCHO_MINIMO and alto >= ALTO_MINIMO


def _bmp(raw: bytes) -> tuple[int, int] | None:
    if not raw.startswith(b'BM') or len(raw) < 26:
        return None
    ancho, alto = struct.unpack('<ii', raw[18:26])
    # El alto es negativo cuando el mapa de bits se guarda de arriba abajo.
    return abs(ancho), abs(alto)


def _png(raw: bytes) -> tuple[int, int] | None:
    if not raw.startswith(_PNG_FIRMA) or len(raw) < 24:
        return None
    ancho, alto = struct.unpack('>II', raw[16:24])
    return ancho, alto


def _jpeg(raw: bytes) -> tuple[int, int] | None:
    if not raw.startswith(b'\xff\xd8'):
        return None
    i = 2
    fin = len(raw)
    while i + 9 < fin:
        if raw[i] != 0xFF:
            i += 1
            continue
        marcador = raw[i + 1]
        # SOF0..SOF15, saltando los que no describen el marco (DHT, JPG, DAC).
        if 0xC0 <= marcador <= 0xCF and marcador not in (0xC4, 0xC8, 0xCC):
            alto, ancho = struct.unpack('>HH', raw[i + 5:i + 9])
            return ancho, alto
        longitud = struct.unpack('>H', raw[i + 2:i + 4])[0]
        if longitud < 2:
            return None
        i += 2 + longitud
    return None
