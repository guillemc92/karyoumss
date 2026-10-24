"""Anota las capturas del entregable M8 sobre la propia imagen.

    py scripts/anotar_capturas_e2e.py

Lee docs/M8_E2E/capturas/captura{1,2,3}.png (las que existan) y escribe
captura{N}_anotada.png al lado, con recuadro, flecha y nota. La consigna exige
la anotacion SOBRE la imagen, no en el texto; este guion la deja reproducible.

Las coordenadas son de las capturas concretas de este entregable (cmd.exe y
el reporte HTML de Playwright a ~1000-1150 px de ancho). Si se retoman con
otro tamano, ajustar las cajas de ANOTACIONES.
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parents[1]
CARPETA = RAIZ / 'docs' / 'M8_E2E' / 'capturas'
ROJO = (214, 39, 39)
BLANCO = (255, 255, 255)


def fuente(tam, negrita=False):
    nombre = 'segoeuib.ttf' if negrita else 'segoeui.ttf'
    try:
        return ImageFont.truetype('C:/Windows/Fonts/' + nombre, tam)
    except OSError:
        return ImageFont.load_default()


def nota(d, xy, texto, ancla='la'):
    """Etiqueta con fondo rojo y texto blanco."""
    f = fuente(15, negrita=True)
    x, y = xy
    caja = d.textbbox((x, y), texto, font=f)
    pad = 6
    d.rectangle((caja[0] - pad, caja[1] - pad, caja[2] + pad, caja[3] + pad), fill=ROJO)
    d.text((x, y), texto, font=f, fill=BLANCO)


def flecha(d, desde, hasta, grosor=3):
    d.line((desde, hasta), fill=ROJO, width=grosor)
    import math
    ang = math.atan2(hasta[1] - desde[1], hasta[0] - desde[0])
    largo = 12
    p1 = (hasta[0] - largo * math.cos(ang - 0.45), hasta[1] - largo * math.sin(ang - 0.45))
    p2 = (hasta[0] - largo * math.cos(ang + 0.45), hasta[1] - largo * math.sin(ang + 0.45))
    d.polygon([hasta, p1, p2], fill=ROJO)


def recuadro(d, caja, grosor=3):
    d.rectangle(caja, outline=ROJO, width=grosor)


# Cada entrada: lista de (tipo, argumentos). Coordenadas en pixeles de la captura.
ANOTACIONES = {
    'captura1.png': [
        # cmd 1016x711: comando y~40, los 12 ok en 112..300, resumen en 327.
        ('recuadro', (8, 30, 700, 51)),
        ('nota', ((708, 31), 'comando, desde frontend-clinic/')),
        ('recuadro', (8, 105, 1008, 308)),
        ('nota', ((320, 318), 'los 12 tests auditados, por nombre (tests/auditado/)')),
        ('recuadro', (8, 317, 172, 341)),
        ('flecha', ((320, 400), (178, 331))),
        ('nota', ((320, 392), '12 passed (5.1m): cantidad y tiempo total, sin recortar')),
    ],
    'captura2.png': [
        ('recuadro', (558, 16, 1064, 48)),
        ('nota', ((120, 30), 'reporte HTML: 12 passed, 0 failed')),
        ('recuadro', (790, 60, 1062, 82)),
        ('flecha', ((700, 100), (790, 72))),
        ('nota', ((405, 92), 'MISMA corrida que la terminal: 24/9 1:10, 5.1m')),
        ('recuadro', (86, 320, 1064, 415)),
        ('nota', ((300, 430), 'el unico lento cruza el modelo local (3.6m); los otros 11 suman <1,5 min')),
        ('recuadro', (86, 92, 1064, 1420)),
        ('nota', ((120, 1355), 'los 12 tests con tick verde y su duracion')),
    ],
    'captura3.png': [
        ('recuadro', (585, 16, 1064, 48)),
        ('nota', ((120, 30), 'Rojo controlado: los 15 generados por el agente, sin tocar')),
        ('flecha', ((400, 120), (118, 168))),
        ('nota', ((400, 108), '9 de 15 no llegan a ejecutarse')),
        ('recuadro', (104, 222, 1048, 580)),
        ('nota', ((330, 205), 'CON-05: error de sintaxis, locator sin corchetes')),
        ('nota', ((120, 795), 'Se conservan intactos como evidencia de la auditoria (§3)')),
    ],
}


def anotar(nombre):
    ruta = CARPETA / nombre
    if not ruta.exists():
        print('  (no existe)', nombre)
        return
    img = Image.open(ruta).convert('RGB')
    d = ImageDraw.Draw(img)
    for tipo, args in ANOTACIONES[nombre]:
        if tipo == 'recuadro':
            recuadro(d, args)
        elif tipo == 'flecha':
            flecha(d, *args)
        elif tipo == 'nota':
            nota(d, args[0], args[1])
    salida = ruta.with_name(ruta.stem + '_anotada.png')
    img.save(salida)
    print('  ok', salida.name, img.size)


if __name__ == '__main__':
    print('anotando en', CARPETA)
    for n in ANOTACIONES:
        anotar(n)
