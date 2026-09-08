"""Regenera README.md leyendo el frontmatter de cada ADR.

    python docs/adr/generar_indice.py           # reescribe el indice
    python docs/adr/generar_indice.py --check    # solo avisa, no escribe (para CI)

## Por que generado y no a mano

Un indice manual se desincroniza igual que se desincronizaron los estados: el
21/08/2026 habia dos ADRs marcadas `proposed` que llevaban meses en produccion.
Escribir "acuerdate de actualizar la tabla" no funciono; leer el frontmatter si.

`--check` devuelve codigo 1 si el indice esta desactualizado o si alguna ADR
tiene el frontmatter mal, para poder colgarlo de un hook o de CI.
"""
import argparse
import io
import os
import re
import sys
from pathlib import Path

ADR_DIR = Path(__file__).resolve().parent
INDICE = ADR_DIR / 'README.md'
MARCA_INICIO = '<!-- INDICE:INICIO -->'
MARCA_FIN = '<!-- INDICE:FIN -->'

ESTADOS = {
    'accepted': 'Aceptada',
    'proposed': 'Propuesta',
    'rejected': 'Rechazada',
    'superseded': 'Reemplazada',
    'deprecated': 'Derogada',
}


def leer(ruta: Path) -> dict:
    txt = io.open(ruta, encoding='utf-8', errors='replace').read()
    m = re.match(r'^---\n(.*?)\n---', txt, re.S)
    fm = m.group(1) if m else ''

    def campo(nombre, defecto=''):
        mm = re.search(r'^%s:\s*(.+)$' % nombre, fm, re.M)
        return mm.group(1).strip().strip('"').strip("'") if mm else defecto

    titulo = campo('title')
    if not titulo:
        h = re.search(r'^#\s+(.+)$', txt, re.M)
        titulo = re.sub(r'^ADR[- ]?\d+:\s*', '', h.group(1).strip()) if h else ''

    return {
        'archivo': ruta.name,
        'num': ruta.name[:4],
        'titulo': titulo,
        'estado': campo('status'),
        'fecha': campo('date'),
        'tiene_frontmatter': bool(m),
    }


def problemas(adrs: list) -> list:
    avisos = []
    for a in adrs:
        if not a['tiene_frontmatter']:
            avisos.append('%s: sin frontmatter YAML' % a['archivo'])
            continue
        if not a['estado']:
            avisos.append('%s: sin campo `status`' % a['archivo'])
        elif a['estado'] not in ESTADOS:
            avisos.append('%s: estado desconocido "%s"' % (a['archivo'], a['estado']))
        if not a['titulo']:
            avisos.append('%s: sin titulo' % a['archivo'])
        if not a['fecha']:
            avisos.append('%s: sin fecha' % a['archivo'])
    return avisos


def tabla(adrs: list) -> str:
    lineas = ['| ADR | Título | Estado | Fecha |', '|-----|--------|--------|-------|']
    for a in adrs:
        estado = ESTADOS.get(a['estado'], a['estado'] or '—')
        if a['estado'] == 'proposed':
            estado = '**%s**' % estado          # resalta lo que sigue sin cerrar
        lineas.append('| [%s](%s) | %s | %s | %s |'
                      % (a['num'], a['archivo'], a['titulo'] or '—', estado, a['fecha'] or '—'))
    return '\n'.join(lineas)


def resumen(adrs: list) -> str:
    from collections import Counter
    c = Counter(a['estado'] for a in adrs)
    partes = ['%d %s' % (n, ESTADOS.get(e, e or 'sin estado').lower())
              for e, n in sorted(c.items(), key=lambda x: -x[1])]
    return '**%d ADRs**: %s.' % (len(adrs), ', '.join(partes))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true',
                    help='no escribe; devuelve 1 si el indice esta desactualizado')
    opts = ap.parse_args()

    adrs = [leer(p) for p in sorted(ADR_DIR.glob('[0-9][0-9][0-9][0-9]-*.md'))]
    if not adrs:
        print('no se encontro ninguna ADR', file=sys.stderr)
        return 1

    avisos = problemas(adrs)
    bloque = '%s\n\n%s\n\n%s\n\n%s' % (MARCA_INICIO, resumen(adrs), tabla(adrs), MARCA_FIN)

    if not INDICE.exists():
        print('falta %s: creala con las marcas %s / %s' % (INDICE.name, MARCA_INICIO, MARCA_FIN),
              file=sys.stderr)
        return 1

    actual = io.open(INDICE, encoding='utf-8').read()
    nuevo = re.sub(re.escape(MARCA_INICIO) + '.*?' + re.escape(MARCA_FIN),
                   bloque.replace('\\', '\\\\'), actual, flags=re.S)

    desactualizado = nuevo != actual
    for a in avisos:
        print('AVISO: %s' % a)

    if opts.check:
        if desactualizado:
            print('El indice esta DESACTUALIZADO. Corre: python docs/adr/generar_indice.py')
        return 1 if (desactualizado or avisos) else 0

    if desactualizado:
        io.open(INDICE, 'w', encoding='utf-8', newline='\n').write(nuevo)
        print('indice actualizado: %d ADRs' % len(adrs))
    else:
        print('indice ya estaba al dia: %d ADRs' % len(adrs))
    return 1 if avisos else 0


if __name__ == '__main__':
    raise SystemExit(main())
