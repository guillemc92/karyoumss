"""Convierte los Markdown de entrega a .docx.

    ../backend-clinic/.venv/Scripts/python md_a_word.py ENTREGA_TOOL_CALLING.md

Cubre lo que usan los documentos de entrega: encabezados, párrafos, negrita e
`inline code`, tablas, bloques de código y citas. No pretende ser un conversor
general — pretende que el documento se regenere solo cuando cambie la fuente,
en vez de mantenerse a mano en dos formatos.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor

CODIGO_FONDO = RGBColor(0x1F, 0x2A, 0x37)
NEGRITA_O_CODE = re.compile(r'(\*\*[^*]+\*\*|`[^`]+`)')


def _texto_con_formato(parrafo, texto: str) -> None:
    """Escribe `texto` aplicando **negrita** e `inline code`."""
    for trozo in NEGRITA_O_CODE.split(texto):
        if not trozo:
            continue
        if trozo.startswith('**') and trozo.endswith('**'):
            parrafo.add_run(trozo[2:-2]).bold = True
        elif trozo.startswith('`') and trozo.endswith('`'):
            run = parrafo.add_run(trozo[1:-1])
            run.font.name = 'Consolas'
            run.font.size = Pt(9.5)
        else:
            parrafo.add_run(trozo)


def _tabla(doc: Document, filas: list[str]) -> None:
    celdas = [[c.strip() for c in f.strip().strip('|').split('|')] for f in filas]
    cabecera, cuerpo = celdas[0], celdas[2:]      # celdas[1] es el separador ---
    tabla = doc.add_table(rows=1, cols=len(cabecera))
    tabla.style = 'Light Grid Accent 1'
    for i, titulo in enumerate(cabecera):
        celda = tabla.rows[0].cells[i]
        celda.text = ''
        _texto_con_formato(celda.paragraphs[0], titulo)
        for run in celda.paragraphs[0].runs:
            run.bold = True
    for fila in cuerpo:
        nuevas = tabla.add_row().cells
        for i, valor in enumerate(fila[:len(cabecera)]):
            nuevas[i].text = ''
            _texto_con_formato(nuevas[i].paragraphs[0], valor)


def _bloque_codigo(doc: Document, lineas: list[str]) -> None:
    parrafo = doc.add_paragraph()
    parrafo.paragraph_format.left_indent = Pt(14)
    parrafo.paragraph_format.space_after = Pt(10)
    run = parrafo.add_run('\n'.join(lineas))
    run.font.name = 'Consolas'
    run.font.size = Pt(8.5)
    run.font.color.rgb = CODIGO_FONDO


def convertir(origen: Path, destino: Path) -> None:
    doc = Document()
    doc.styles['Normal'].font.name = 'Calibri'
    doc.styles['Normal'].font.size = Pt(10.5)

    lineas = origen.read_text(encoding='utf-8').splitlines()
    i = 0
    while i < len(lineas):
        linea = lineas[i]

        if linea.startswith('```'):                       # bloque de código
            cierre = i + 1
            while cierre < len(lineas) and not lineas[cierre].startswith('```'):
                cierre += 1
            _bloque_codigo(doc, lineas[i + 1:cierre])
            i = cierre + 1
            continue

        if linea.startswith('|'):                          # tabla
            fin = i
            while fin < len(lineas) and lineas[fin].startswith('|'):
                fin += 1
            _tabla(doc, lineas[i:fin])
            doc.add_paragraph()
            i = fin
            continue

        if linea.startswith('#'):                          # encabezado
            nivel = len(linea) - len(linea.lstrip('#'))
            doc.add_heading(linea.lstrip('# ').strip(), level=min(nivel, 4))
        elif linea.strip() == '---':
            doc.add_paragraph()
        elif linea.startswith('> '):                       # cita
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Pt(18)
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            _texto_con_formato(p, linea[2:])
            for run in p.runs:
                run.italic = True
        elif linea.startswith(('- ', '* ')):               # viñeta
            _texto_con_formato(doc.add_paragraph(style='List Bullet'), linea[2:])
        elif re.match(r'^\d+\. ', linea):                  # numerada
            _texto_con_formato(doc.add_paragraph(style='List Number'),
                               re.sub(r'^\d+\. ', '', linea))
        elif linea.strip():
            _texto_con_formato(doc.add_paragraph(), linea)

        i += 1

    doc.save(destino)
    print(f'  {destino.name}  <-  {origen.name}')


if __name__ == '__main__':
    base = Path(__file__).parent
    fuentes = sys.argv[1:] or ['ENTREGA_TOOL_CALLING.md',
                               'ENTREGA_TOOL_CALLING_UNA_PAGINA.md']
    print('Generando Word:')
    for nombre in fuentes:
        origen = base / nombre
        convertir(origen, origen.with_suffix('.docx'))
