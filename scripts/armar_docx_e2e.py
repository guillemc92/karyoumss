"""Cierra el ENTREGABLE_E2E_MEJORADO.docx del autor con las capturas anotadas.

    backend-clinic/.venv/Scripts/python scripts/armar_docx_e2e.py ENTRADA.docx SALIDA.docx [commit]

No regenera el documento: edita el que escribió el autor a mano. Hace cuatro
cosas, y solo esas:

1. Quita del final el bloque suelto (comando huérfano, tres imágenes sin pie,
   «Fin del entregable», «se adjuntan por separado»).
2. Pone en la §2 la corrida CAPTURADA: tiempos por test y total, leídos de
   `docs/M8_E2E/capturas/corrida.txt` (la salida `list` de esa misma corrida).
   La consigna corrige sobre la captura; el texto tiene que decir lo mismo.
3. Añade al inventario (§1) la columna «qué debe ver al final», que es como
   el docente define un flujo en la consigna del 11/09.
4. Añade una «9 · Capturas» con las tres imágenes anotadas y su pie.
"""
import copy
import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

RAIZ = Path(__file__).resolve().parents[1]
CAPTURAS = RAIZ / 'docs' / 'M8_E2E' / 'capturas'

# Flujo -> qué debe ver la persona al final. Mismo orden que la tabla del §1.
QUE_VE = {
    '1': 'la tabla de sus muestras con CHN, estado y fecha',
    '2': 'la muestra creada con sus metafases y el estado inicial',
    '3': 'CHN, estado, metafases y el acceso al visor',
    '4': 'el cariograma con los pares ordenados',
    '5': 'cada cromosoma verde, naranja o rojo según su confianza',
    '6': 'el mapa de calor y el cromosoma reclasificado',
    '7': '«Validar» bloqueado y el motivo: quedan naranjas',
    '8': '«No es dueño de esta muestra…», no un error genérico',
    '9': 'los casos por validar y los sorteados al 5 %',
    '10': 'el banner de modo manual y la muestra registrada sin cariotipo',
    '11': 'la respuesta y de qué camino y tabla salió',
    '12': 'ningún dato de paciente (ningún CHN)',
    '13': 'la muestra con los cambios guardados',
    '14': 'el aviso de que el pipeline no está disponible',
}

PIES = [
    ('captura1_anotada.png',
     'Captura 1 — Terminal: `npx playwright test` desde frontend-clinic/. Los 5 tests auditados, '
     '5 passed y el tiempo total, sin recortar el resumen.'),
    ('captura2_anotada.png',
     'Captura 2 — Reporte HTML de Playwright de esa misma corrida (`npx playwright show-report`): '
     'los 5 tests con su tick y su duración.'),
    ('captura3_anotada.png',
     'Captura 3 — Rojo controlado: `npx playwright test --config playwright.agente.config.ts`. '
     'Los 9 generados por el agente, sin tocar; 5 de 9 no cargan porque importan un módulo que no existe.'),
]


def texto(p):
    return ''.join(t.text or '' for t in p.iter(qn('w:t')))


def leer_corrida():
    """Tiempos por test y total desde la salida `list` de la corrida capturada."""
    s = (CAPTURAS / 'corrida.txt').read_text(encoding='utf-8')
    tiempos = {}
    for m in re.finditer(r'ok \d+ .*?auditado[\\/](\S+?)\.spec\.ts.*?\((\d+\.\d)s\)', s):
        tiempos[m.group(1)] = m.group(2).replace('.', ',')
    total = re.search(r'(\d+) passed \(([\d.]+)(s|m)\)', s)
    return tiempos, total.group(2).replace('.', ','), total.group(3)


def quitar_bloque_final(doc):
    body = doc.element.body
    hijos = list(body.iterchildren())
    # Desde el último Título1 («8 · Qué queda...») hacia abajo, todo lo que sea
    # imagen, el comando suelto o los dos cierres.
    borrar = []
    for el in reversed(hijos):
        tag = el.tag.split('}')[1]
        if tag == 'sectPr':
            continue
        if tag == 'tbl':
            break
        t = texto(el).strip()
        if el.iter(qn('w:drawing')) and list(el.iter(qn('w:drawing'))):
            borrar.append(el)
        elif t in ('npx playwright test --reporter=list', '— Fin del entregable —') \
                or t.startswith('Capturas de terminal y reporte HTML'):
            borrar.append(el)
        elif not t:
            borrar.append(el)
        else:
            break
    for el in borrar:
        body.remove(el)
    return len(borrar)


def corregir_seccion2(doc, tiempos, total, unidad, commit):
    cambios = 0
    for p in doc.paragraphs:
        # Resumen ejecutivo: repite el tiempo total.
        for r in p.runs:
            if '29,6 s' in r.text:
                r.text = r.text.replace('29,6 s', '%s s' % total); cambios += 1
        if texto(p._p).strip() == 'npx playwright test --reporter=list':
            for r in p.runs[1:]:
                r._r.getparent().remove(r._r)
            p.runs[0].text = 'cd frontend-clinic && npx playwright test'
            cambios += 1
        elif texto(p._p).startswith('Tiempo total:'):
            for r in p.runs[1:]:
                r._r.getparent().remove(r._r)
            p.runs[0].text = (
                'Tiempo total: %s %s (corrida capturada, 14/09, stack caliente). La primera corrida del día '
                'tarda ~55 s por el arranque de Vite y la carga del modelo en Ollama. Los tests que superan '
                '3 s corren contra el stack real, no contra un mock: modo-degradado registra por API y abre '
                'dos pantallas; listado y segregación piden un JWT real a backend-admin.'
                % (total, 'min' if unidad == 'm' else 's'))
            cambios += 1
    for t in doc.tables:
        cab = [texto(c._tc).strip() for c in t.rows[0].cells]
        if cab[0] == 'Equipo':
            for fila in t.rows:
                if texto(fila.cells[0]._tc).strip() == 'Repositorio':
                    for r in fila.cells[1].paragraphs[0].runs:
                        if '38cb0bf' in r.text:
                            r.text = r.text.replace('38cb0bf', commit); cambios += 1
        if cab[:2] == ['#', 'Test'] and 'Duración' in cab:
            col = cab.index('Duración')
            for fila in t.rows[1:]:
                nombre = texto(fila.cells[1]._tc).split('.spec.ts')[0].strip()
                if nombre in tiempos:
                    c = fila.cells[col]
                    for r in c.paragraphs[0].runs[1:]:
                        r._r.getparent().remove(r._r)
                    c.paragraphs[0].runs[0].text = tiempos[nombre] + ' s'
                    cambios += 1
    return cambios


def anadir_columna_que_ve(doc):
    for t in doc.tables:
        cab = [texto(c._tc).strip() for c in t.rows[0].cells]
        if cab[:3] == ['#', 'Flujo', 'Ruta']:
            break
    else:
        return 0
    # Insertar la columna después de «Flujo» copiando el formato de esa celda.
    for i, fila in enumerate(t.rows):
        origen = fila.cells[1]._tc
        nueva = copy.deepcopy(origen)
        for tt in list(nueva.iter(qn('w:t'))):
            tt.text = ''
        origen.addnext(nueva)
        ts = list(nueva.iter(qn('w:t')))
        valor = 'Qué debe ver al final' if i == 0 else QUE_VE.get(texto(fila.cells[0]._tc).strip(), '')
        if ts:
            ts[0].text = valor
        else:
            p = nueva.find(qn('w:p'))
            r = OxmlElement('w:r'); tt = OxmlElement('w:t'); tt.text = valor
            r.append(tt); p.append(r)
    # Ajustar los anchos de rejilla si existen.
    grid = t._tbl.find(qn('w:tblGrid'))
    if grid is not None:
        cols = grid.findall(qn('w:gridCol'))
        if len(cols) >= 2:
            grid.insert(2, copy.deepcopy(cols[1]))
    return len(t.rows)


def anadir_capturas(doc):
    doc.add_heading('9 · Capturas', level=1)
    intro = doc.add_paragraph(
        'Las tres capturas van anotadas sobre la propia imagen (recuadro, flecha y nota). '
        'Las capturas 1 y 2 son de la misma corrida, la del 14/09; la fecha y hora del reporte lo muestran. '
        'Anotación reproducible con scripts/anotar_capturas_e2e.py.')
    for archivo, pie in PIES:
        ruta = CAPTURAS / archivo
        if not ruta.exists():
            raise SystemExit('falta ' + str(ruta))
        doc.add_picture(str(ruta), width=Cm(16))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        p = doc.add_paragraph()
        partes = re.split(r'(`[^`]+`)', pie)
        for parte in partes:
            if parte.startswith('`'):
                r = p.add_run(parte.strip('`')); r.font.name = 'Consolas'; r.font.size = Pt(9)
            else:
                r = p.add_run(parte); r.font.size = Pt(9.5)
        p.paragraph_format.space_after = Pt(14)


def main():
    entrada, salida = Path(sys.argv[1]), Path(sys.argv[2])
    commit = sys.argv[3] if len(sys.argv) > 3 else '38cb0bf'
    doc = Document(str(entrada))
    tiempos, total, unidad = leer_corrida()
    print('corrida:', tiempos, total, unidad)
    print('quitados del final:', quitar_bloque_final(doc))
    print('cambios en §2/resumen/cabecera:', corregir_seccion2(doc, tiempos, total, unidad, commit))
    print('filas con columna nueva en §1:', anadir_columna_que_ve(doc))
    anadir_capturas(doc)
    doc.save(str(salida))
    print('escrito', salida)


if __name__ == '__main__':
    main()
