"""Cuántos cromosomas de una metafase salen inclinados (DD-KARYO-008 §1.2).

Lee la respuesta de backend-ml `POST /api/v1/segment/` guardada en un JSON y,
para cada silueta (`contour`), calcula el eje mayor con los momentos de área
del polígono. Dice cuántos se apartan más de 10, 20 y 30 grados del eje vertical
u horizontal (los únicos que el cariograma sabe poner de pie hoy) y cuánto más
largo es el cromosoma a lo largo de su eje que el lado largo de su caja.

Antes de medir se prueba a sí mismo con rectángulos girados en los dos sentidos
de recorrido: las siluetas de backend-ml vienen en sentido horario, y sin
corregir el signo del área el ángulo cae en el eje MENOR (fallo real de la
primera medición).

Uso:
    curl -s -F file=@datasets/metaclass/metafases/metafase_1.bmp \
         http://127.0.0.1:8000/api/v1/segment/ > seg.json
    py -3 -I scripts/medir_ejes_cromosomas.py seg.json
"""
import json
import math
import sys


def siluetas(o):
    if isinstance(o, dict):
        if o.get('contour') and o.get('bbox'):
            yield o
        for v in o.values():
            yield from siluetas(v)
    elif isinstance(o, list):
        for v in o:
            yield from siluetas(v)


def eje_mayor(c):
    """(ángulo del eje mayor en radianes respecto a x, cx, cy) o None si no hay área."""
    area = cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(c, c[1:] + c[:1]):
        k = x0 * y1 - x1 * y0
        area += k
        cx += (x0 + x1) * k
        cy += (y0 + y1) * k
    area /= 2
    if abs(area) < 1:
        return None
    cx /= 6 * area
    cy /= 6 * area
    mxx = myy = mxy = 0.0
    for (x0, y0), (x1, y1) in zip(c, c[1:] + c[:1]):
        x0, x1, y0, y1 = x0 - cx, x1 - cx, y0 - cy, y1 - cy
        k = x0 * y1 - x1 * y0
        mxx += (x0 * x0 + x0 * x1 + x1 * x1) * k / 12
        myy += (y0 * y0 + y0 * y1 + y1 * y1) * k / 12
        mxy += (x0 * y1 + 2 * x0 * y0 + 2 * x1 * y1 + x1 * y0) * k / 24
    signo = 1 if area > 0 else -1  # horario: todos los momentos salen negados
    return 0.5 * math.atan2(2 * mxy * signo, (mxx - myy) * signo), cx, cy


def rectangulo(w, h, grados):
    a = math.radians(grados)
    return [(x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a))
            for x, y in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2))]


def autoprueba():
    for giro in (0, 30, 90, -45):
        for sentido in (1, -1):
            r = rectangulo(10, 100, giro)[::sentido]
            obtenido = math.degrees(eje_mayor(r)[0]) % 180
            esperado = (90 + giro) % 180
            if abs(obtenido - esperado) > 1e-6 and abs(abs(obtenido - esperado) - 180) > 1e-6:
                sys.exit(f'autoprueba fallida: giro {giro}, sentido {sentido}: {obtenido:.1f} != {esperado}')


def main(ruta):
    autoprueba()
    datos = json.load(open(ruta, encoding='utf-8'))
    desvios, ganancias = [], []
    for o in siluetas(datos):
        r = eje_mayor(o['contour'])
        if r is None:
            continue
        th, cx, cy = r
        a = math.degrees(th) % 180
        desvios.append(min(abs(a - 90), a, 180 - a))
        ux, uy = math.cos(th), math.sin(th)
        p = [(x - cx) * ux + (y - cy) * uy for x, y in o['contour']]
        ganancias.append((max(p) - min(p)) / max(o['bbox']['w'], o['bbox']['h']))
    n = len(desvios)
    if n == 0:
        sys.exit('No hay siluetas en el archivo.')
    ganancias.sort()
    print(f'siluetas: {n}')
    for t in (10, 20, 30):
        print(f'  a más de {t}° del eje vertical u horizontal: {sum(d > t for d in desvios)}')
    print(f'  largo sobre su eje / lado largo de la caja: mediana {ganancias[n // 2]:.2f}, máximo {ganancias[-1]:.2f}')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
