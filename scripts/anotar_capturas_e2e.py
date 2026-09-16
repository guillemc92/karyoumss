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
        # captura de cmd 1016x583: comando en y~55, los 7 ok en 119..215, resumen en 247.
        ('recuadro', (8, 45, 712, 66)),
        ('nota', ((720, 46), 'comando, desde frontend-clinic/')),
        ('recuadro', (8, 108, 1008, 226)),
        ('nota', ((420, 236), 'los 7 tests auditados, por nombre (tests/auditado/)')),
        ('recuadro', (8, 237, 165, 260)),
        ('flecha', ((300, 330), (170, 250))),
        ('nota', ((300, 322), '7 passed: cantidad y tiempo total, sin recortar el resumen')),
    ],
    'captura2.png': [
        # reporte HTML 1150x900: contadores arriba a la derecha, fecha/hora en y~70.
        ('recuadro', (562, 16, 1064, 48)),
        ('nota', ((120, 30), 'reporte HTML: 7 passed, 0 failed')),
        ('recuadro', (795, 60, 1062, 82)),
        ('flecha', ((700, 100), (795, 72))),
        ('nota', ((440, 92), 'MISMA corrida que la terminal: 16/9 1:24, 3.0m')),
        ('recuadro', (86, 92, 1064, 866)),
        ('nota', ((120, 875), 'los 7 tests con tick verde y su duración')),
    ],
    'captura3.png': [
        # reporte HTML del rojo controlado 1150x780 (16/09): 6 modulos ausentes + 1 SyntaxError.
        ('recuadro', (585, 16, 1064, 48)),
        ('nota', ((120, 30), 'Rojo controlado: los 11 generados por el agente, sin tocar')),
        ('flecha', ((400, 120), (118, 168))),
        ('nota', ((400, 108), '6 de 11 importan fixtures/credenciales, que no existe')),
        ('recuadro', (104, 578, 1048, 770)),
        ('nota', ((400, 560), 'SUP-05: error de sintaxis, la API test(...)({...}) no existe')),
        ('nota', ((120, 745), '7 de 11 no llegan a ejecutarse; se conservan como evidencia de la auditoria (§3)')),
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
