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
    '15': '«Esta bandeja es exclusiva del Supervisor» y ningún caso',
    '16': '«Fuera de alcance» y ninguna fila de datos',
}

PIES = [
    ('captura1_anotada.png',
     'Captura 1 — Terminal: `npx playwright test` desde frontend-clinic/. Los 7 tests auditados, '
     '7 passed y el tiempo total, sin recortar el resumen.'),
    ('captura2_anotada.png',
     'Captura 2 — Reporte HTML de Playwright de esa misma corrida (`npx playwright show-report`): '
     'los 7 tests con su tick y su duración.'),
    ('captura3_anotada.png',
     'Captura 3 — Rojo controlado: `npx playwright test --config playwright.agente.config.ts`. '
     'Los 11 generados por el agente, sin tocar; 7 de 11 no llegan a ejecutarse (6 importan un módulo que no existe, 1 tiene un error de sintaxis).'),
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
            if '29,6 s' in r.text or '33,3 s' in r.text:
                r.text = r.text.replace('29,6 s', '%s s' % total).replace('33,3 s', '%s s' % total); cambios += 1
        if texto(p._p).strip() == 'npx playwright test --reporter=list':
            for r in p.runs[1:]:
                r._r.getparent().remove(r._r)
            p.runs[0].text = 'cd frontend-clinic && npx playwright test'
            cambios += 1
        elif texto(p._p).startswith('Tiempo total:'):
            for r in p.runs[1:]:
                r._r.getparent().remove(r._r)
            p.runs[0].text = (
                'Tiempo total: %s %s (corrida capturada, 16/09). La corrida se hizo con la CPU de la máquina al 100 %% '
                'por otro programa; en una máquina libre la misma suite tarda ~1 min (33 s los 5 primeros el 14/09). '
                'Todos corren contra el stack real, no contra un mock: modo-degradado registra por API y abre dos '
                'pantallas; consulta-fuera-de-alcance pasa por el modelo local; listado y segregación piden un JWT '
                'real a backend-admin.'
                % (total, 'min' if unidad == 'm' else 's'))
            cambios += 1
    for t in doc.tables:
        cab = [texto(c._tc).strip() for c in t.rows[0].cells]
        if cab[0] == 'Equipo':
            for fila in t.rows:
                if texto(fila.cells[0]._tc).strip() == 'Fecha':
                    poner_texto(fila.cells[1], '16 de septiembre de 2026 (código: 11/09 y 16/09)'); cambios += 1
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


def poner_texto(celda_o_parrafo, valor):
    """Deja UN run con el texto, conservando el formato del primero."""
    p = celda_o_parrafo.paragraphs[0] if hasattr(celda_o_parrafo, 'paragraphs') else celda_o_parrafo
    if not p.runs:
        p.add_run(valor)
        return
    for r in p.runs[1:]:
        r._r.getparent().remove(r._r)
    p.runs[0].text = valor


def anadir_fila(tabla, valores):
    """Copia la ultima fila (formato incluido) y la rellena."""
    ultima = tabla.rows[-1]._tr
    nueva = copy.deepcopy(ultima)
    ultima.addnext(nueva)
    fila = tabla.rows[-1]
    for celda, valor in zip(fila.cells, valores):
        poner_texto(celda, valor)
    return fila


def tabla_con_cabecera(doc, *inicio):
    for t in doc.tables:
        cab = [texto(c._tc).strip() for c in t.rows[0].cells]
        if tuple(cab[:len(inicio)]) == inicio:
            return t
    return None


def sustituir_parrafo(doc, empieza_por, nuevo):
    for p in doc.paragraphs:
        if texto(p._p).strip().startswith(empieza_por):
            poner_texto(p, nuevo)
            return True
    return False


def insertar_tabla_despues(doc, parrafo, cabecera, filas):
    """Tabla nueva justo despues de `parrafo`, con el estilo de la primera tabla del doc."""
    t = doc.add_table(rows=1, cols=len(cabecera))
    t.style = doc.tables[0].style
    for c, v in zip(t.rows[0].cells, cabecera):
        poner_texto(c, v)
        c.paragraphs[0].runs[0].bold = True
    for fila in filas:
        celdas = t.add_row().cells
        for c, v in zip(celdas, fila):
            poner_texto(c, v)
    parrafo._p.addnext(t._tbl)
    return t


def actualizar_por_seccion(doc, tiempos, total_txt):
    """Todo lo que cambia porque el Planner se corrio por seccion (16/09)."""
    n = 0
    OK = '✅'
    # Resumen ejecutivo
    t = tabla_con_cabecera(doc, '5 tests auditados')
    if t is not None:
        poner_texto(t.rows[0].cells[0], '7 tests auditados'); poner_texto(t.rows[0].cells[2], '11 generados')
        poner_texto(t.rows[1].cells[0], '10 / 16 flujos'); n += 1
    n += sustituir_parrafo(doc, 'Resultado clave:',
        'Resultado clave: 7 tests pasan contra el stack real (backend-admin + backend-clinic + Vite) en %s. '
        'El Planner se corrió por sección (4 secciones, 15 casos) como pide la consigna; ningún caso salió '
        'aceptable sin tocar. Los 11 tests generados por el agente se conservan intactos como evidencia de la '
        'auditoría: 0 aceptados sin corrección.' % total_txt)
    # §1 inventario: dos flujos mas
    t = tabla_con_cabecera(doc, '#', 'Flujo')
    anadir_fila(t, ['15', 'Segregación: analista en la bandeja del supervisor', '/clinic/supervisor',
                    'UC-005 / RN-06', 'bandeja-supervisor-analista', OK])
    anadir_fila(t, ['16', 'Consulta fuera de alcance', '/clinic/consultas',
                    'tool calling (M6)', 'consulta-fuera-de-alcance', OK])
    n += sustituir_parrafo(doc, '8 de 14 flujos en verde',
        '10 de 16 flujos en verde. Los 6 restantes van a evals (motivo en §7).')
    # §2 tabla de la suite: 7 filas
    for p in doc.paragraphs:
        if texto(p._p).strip() == 'Suite auditada — 5 passed':
            poner_texto(p, 'Suite auditada — 7 passed')
    t = tabla_con_cabecera(doc, '#', 'Test')
    anadir_fila(t, ['6', 'bandeja-supervisor-analista.spec.ts — analista en la bandeja del supervisor ve el aviso',
                    tiempos.get('bandeja-supervisor-analista', '?') + ' s', OK + ' ok'])
    anadir_fila(t, ['7', 'consulta-fuera-de-alcance.spec.ts — consulta ajena al dominio se declara fuera de alcance',
                    tiempos.get('consulta-fuera-de-alcance', '?') + ' s', OK + ' ok'])
    n += sustituir_parrafo(doc, '5 de 9 generados ni cargan',
        '7 de 11 generados ni cargan: 6 importan fixtures/credenciales (módulo inexistente) y SUP-05 tiene un '
        'error de sintaxis (usa una API test(...)({...}) que no existe). Playwright los rechaza antes de ejecutar. '
        'Se corren aparte para no abortar la suite verde. Se conservan intactos como evidencia de la auditoría.')
    # §3 tabla de auditoria: dos filas mas, y balance
    t = tabla_con_cabecera(doc, 'Caso del plan')
    anadir_fila(t, ['SUP-05 Analista en la bandeja (plan por sección)', 'agente/SUP-05 → auditado/bandeja-supervisor-…',
                    'reescrito', '1, 3, 4',
                    'API inventada (no carga); locator sin corchetes; afirma el texto de mi plan, no el de la UI; exige a la vez un error de carga'])
    anadir_fila(t, ['CON-04 Fuera de alcance (plan por sección)', 'agente/CON-04 → auditado/consulta-fuera-de-…',
                    'reescrito', '1, 2, 3, 4',
                    'import inexistente; input[name=query] no existe; 4 waitForSelector; anclas de otras 3 pantallas; medido 9/9 SIN_MATCH antes de aceptar'])
    n += sustituir_parrafo(doc, 'Balance:',
        'Balance: Planner por sección (16/09, la corrida que vale) → 15 propuestos · 0 aceptados sin tocar · 9 corregidos · '
        '6 descartados · 4 añadidos por auditoría.  Corrida única del 11/09 (sustituida) → 8 · 1 · 6 · 1 · +3.  '
        'Generator → 11 generados · 0 aceptados · 1 corregido · 10 descartados (3 de ellos reescritos).')
    for p in doc.paragraphs:
        if texto(p._p).startswith('Balance:'):
            insertar_tabla_despues(doc, p,
                ['Sección', 'Propuestos', 'Aceptados', 'Corregidos', 'Descartados', 'Añadidos', 'Tokens in/out', 'Motivo dominante'],
                [['muestras', '4', '0', '3', '1', '2', '705 / 333', 'los 4 en /register; RN-07 ignorada; 2 criterios afirman la violación'],
                 ['visor', '4', '0', '3', '1', '0', '755 / 472', 'cremallera de nuevo: RN-01, 02, 04, 06 en orden de lista'],
                 ['supervisor', '4', '0', '1', '3', '1', '676 / 456', '3 criterios circulares; oráculos cruzados; inventa un error de BD'],
                 ['consultas', '3', '0', '2', '1', '1', '635 / 251', 'lo que no está en el FSD lo rellena con RN-03'],
                 ['Total', '15', '0', '9', '6', '4', '2 771 / 1 512', 'detalle en specs/PLANNER_POR_SECCION.md']])
            break
    n += sustituir_parrafo(doc, 'Hallazgo previo a generar:',
        'Hallazgo previo a generar: en la corrida única del 11/09, 5 de 8 casos emparejaban UC-N con RN-0N por posición '
        '(cremallera). Al repetirlo por sección el 16/09 la cremallera VOLVIÓ en la sección visor (RN-01, 02, 04, 06 en el '
        'orden exacto de la lista): acotar el contexto no la quita, la quita la auditoría. Por eso el Generator lee los '
        'planes auditados y no los crudos.')
    # §4 tokens
    t = tabla_con_cabecera(doc, '', 'Entrada (tokens)')
    if t is not None:
        poner_texto(t.rows[1].cells[0], 'Planner, corrida única 11/09 (8 casos)')
        poner_texto(t.rows[2].cells[0], 'Generator, promedio/test (11)')
        poner_texto(t.rows[2].cells[1], '699'); poner_texto(t.rows[2].cells[2], '365'); poner_texto(t.rows[2].cells[3], '399 s')
        poner_texto(t.rows[3].cells[1], '7 691'); poner_texto(t.rows[3].cells[2], '4 023'); poner_texto(t.rows[3].cells[3], '73 min')
        anadir_fila(t, ['Planner por sección 16/09 (4 secciones, 15 casos)', '2 771', '1 512', '22 min'])
        anadir_fila(t, ['Planner por sección, promedio por sección', '693', '378', '330 s'])
        n += 1
    # §8 repositorio
    t = tabla_con_cabecera(doc, 'Ruta')
    if t is not None:
        poner_texto(t.rows[1].cells[1], 'Los 7 tests aceptados, con las cinco preguntas resueltas por diseño en cada cabecera')
        poner_texto(t.rows[2].cells[1], 'Los 11 generados, intactos: la evidencia de la auditoría')
        anadir_fila(t, ['specs/PLANNER_POR_SECCION.md', 'El Planner por sección: 4 planes auditados con totales y motivo'])
        anadir_fila(t, ['docs/M8_E2E/secciones/', 'plan_<sección>.json (crudo) y plan_<sección>_auditado.json'])
        n += 1
    return n


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
        'Las capturas 1 y 2 son de la misma corrida, la del 16/09; la fecha y hora del reporte lo muestran. '
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
    total_txt = '%s %s' % (total, 'min' if unidad == 'm' else 's')
    print('cambios por seccion:', actualizar_por_seccion(doc, tiempos, total_txt))
    print('filas con columna nueva en §1:', anadir_columna_que_ve(doc))
    anadir_capturas(doc)
    doc.save(str(salida))
    print('escrito', salida)


if __name__ == '__main__':
    main()
