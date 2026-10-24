"""Lleva el entregable M8 del 62,5 % al 81,25 % de flujos cubiertos.

    backend-clinic/.venv/Scripts/python scripts/actualizar_docx_80.py ENTRADA.docx SALIDA.docx [commit]

Parte del documento que el autor entrego el 16/09 y le aplica lo del 23/09.
No regenera nada: edita el suyo, como `armar_docx_e2e.py`.

## Por que hubo una segunda vuelta

La Clase06 —la de esta consigna— fija el umbral con palabras del docente:
«cinco flujos cinco features minimamente deberias tener cinco en tu end» y
«80%... eso es lo minimo recomendable». La entrega iba con 10 de 16 = 62,5 %.

Los tres flujos que faltaban y NO dependen del modelo de IA son registro,
edicion y pagina de modo degradado. Con ellos: 13 de 16 = 81,25 %.

## Que toca

1. Resumen ejecutivo y §1: 13 de 16, y los tres flujos pasan a verde.
2. §2: la tabla de la suite pasa de 7 a 11 filas, con los tiempos capturados.
3. §3: cuatro filas de auditoria mas y los totales del Generator (15 tests).
4. §4: tokens del Generator recalculados sobre 15 tests.
5. §5: las anclas dejan de ser «identificada, no anadida».
6. §7: se quitan los tres flujos ya cubiertos y se deja el motivo de los tres
   que quedan, que son los que dependen del modelo.
7. Seccion nueva: los dos defectos del producto que encontro el E2E.
"""
import copy
import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

RAIZ = Path(__file__).resolve().parents[1]
CAPTURAS = RAIZ / 'docs' / 'M8_E2E' / 'capturas'

#: Flujo -> (test que lo cubre, estado). Solo los que cambian.
AHORA_VERDES = {
    '2': ('registro-por-interfaz + registro-validacion', '✅'),
    '9': ('bandeja-supervisor (el sorteo del 5 % sigue en evals)', '✅'),
    '13': ('edicion-muestra', '✅'),
    '14': ('pagina-degradada', '✅'),
}

FILAS_AUDITORIA = [
    ['MUE-01 Registro por interfaz (23/09)', 'agente/MUE-01 → auditado/registro-por-interfaz',
     'reescrito', '1, 2, 3, 4',
     'input[name="chn"] es CSS y ese campo no se llama asi; 4 waitForSelector; comillas desbalanceadas (no compila); CINCO pantallas en un test; inventa la ruta /clinic/samples/validado'],
    ['MUE-03 Validacion del registro (23/09)', 'agente/MUE-03 → auditado/registro-validacion',
     'reescrito', '1, 3',
     'expect(respuesta).toHaveText sobre la respuesta de goto, que no es un locator; afirma «El campo CHN es obligatorio», texto que el modelo invento'],
    ['MUE-07 Edicion de muestra (23/09)', 'agente/MUE-07 → auditado/edicion-muestra',
     'reescrito', '1, 2, 5',
     'chnUnico().id sobre un string: EL MISMO fallo que E2E-03 y E2E-06 del 11/09, seis semanas despues; page.waitForChange() no existe'],
    ['CON-05 Pagina de modo degradado (23/09)', 'agente/CON-05 → auditado/pagina-degradada',
     'reescrito', '1, 2',
     'anclas de otras pantallas y esperas fijas sobre una pagina estatica'],
]

DEFECTOS = [
    ('«[object Object]» en vez del motivo del error',
     'Los clientes HTTP hacian String(payload.detail). Cuando el backend responde VALIDATION_ERROR, '
     'detail no es una cadena sino el diccionario de errores por campo de DRF, y String() sobre un '
     'objeto devuelve «[object Object]». El analista veia eso, literalmente, en vez de «Fecha con '
     'formato erroneo». El dato estaba en la respuesta; se perdia al formatearlo. '
     'Arreglado con api/detalleError.ts, que aplana el arbol a «campo: mensaje».'),
    ('No se podia registrar sin rellenar un campo opcional',
     'El formulario manda collection_date y reception_date como cadena vacia y el serializador las '
     'rechaza. Pero «Fecha de recepcion en laboratorio» NO esta marcada como obligatoria en la '
     'pantalla: quien no la rellenaba —lo normal— no podia registrar, y por el defecto anterior ni '
     'siquiera sabia por que. Ahora las fechas vacias se omiten del cuerpo, que es lo que «no '
     'informada» significa en este contrato.'),
]

PIES = [
    ('captura1_anotada.png',
     'Captura 1 — Terminal: npx playwright test desde frontend-clinic/. Los 12 tests auditados, '
     '12 passed y el tiempo total, sin recortar el resumen.'),
    ('captura2_anotada.png',
     'Captura 2 — Reporte HTML de Playwright de esa misma corrida (npx playwright show-report): '
     'los 12 tests con su tick y su duracion.'),
    ('captura3_anotada.png',
     'Captura 3 — Rojo controlado: npx playwright test --config playwright.agente.config.ts. '
     'Los 15 generados por el agente, sin tocar.'),
]


def texto(el):
    return ''.join(t.text or '' for t in el.iter(qn('w:t')))


def poner(celda_o_parrafo, valor):
    p = celda_o_parrafo.paragraphs[0] if hasattr(celda_o_parrafo, 'paragraphs') else celda_o_parrafo
    if not p.runs:
        p.add_run(valor)
        return
    for r in p.runs[1:]:
        r._r.getparent().remove(r._r)
    p.runs[0].text = valor


def anadir_fila(tabla, valores):
    ultima = tabla.rows[-1]._tr
    ultima.addnext(copy.deepcopy(ultima))
    for celda, valor in zip(tabla.rows[-1].cells, valores):
        poner(celda, valor)


def tabla_con(doc, *inicio):
    for t in doc.tables:
        cab = [texto(c._tc).strip() for c in t.rows[0].cells]
        if tuple(cab[:len(inicio)]) == inicio:
            return t
    return None


def sustituir(doc, empieza, nuevo):
    for p in doc.paragraphs:
        if texto(p._p).strip().startswith(empieza):
            poner(p, nuevo)
            return 1
    return 0


def leer_corrida():
    s = (CAPTURAS / 'corrida.txt').read_text(encoding='utf-8')
    tiempos = {}
    for m in re.finditer(r'ok\s+\d+\s+.*?auditado[\\/](\S+?)\.spec\.ts.*?\((\d+\.\d)s\)', s):
        tiempos[m.group(1)] = m.group(2).replace('.', ',')
    total = re.search(r'(\d+) passed \(([\d.]+)(s|m)\)', s)
    return tiempos, total.group(2).replace('.', ','), total.group(3)


def quitar_capturas_viejas(doc):
    """La §9 anterior se rehace entera: sus pies hablan de 7 tests."""
    cuerpo = doc.element.body
    borrar, dentro = [], False
    for el in cuerpo.iterchildren():
        t = texto(el).strip()
        if t.startswith('9 · Capturas') or t.startswith('9 · Capturas'):
            dentro = True
        if dentro:
            borrar.append(el)
    for el in borrar:
        cuerpo.remove(el)
    return len(borrar)


def main():
    entrada, salida = Path(sys.argv[1]), Path(sys.argv[2])
    commit = sys.argv[3] if len(sys.argv) > 3 else 'PENDIENTE'
    doc = Document(str(entrada))
    tiempos, total, unidad = leer_corrida()
    total_txt = '%s %s' % (total, 'min' if unidad == 'm' else 's')
    n = 0

    # Cabecera
    t = tabla_con(doc, 'Equipo')
    for fila in t.rows:
        etiqueta = texto(fila.cells[0]._tc).strip()
        if etiqueta == 'Fecha':
            poner(fila.cells[1], '23 de septiembre de 2026 (codigo: 11/09, 16/09 y 23/09)'); n += 1
        elif etiqueta == 'Repositorio':
            for r in fila.cells[1].paragraphs[0].runs:
                if re.search(r'\b[0-9a-f]{7}\b', r.text):
                    r.text = re.sub(r'\b[0-9a-f]{7}\b', commit, r.text); n += 1

    # Resumen ejecutivo
    t = tabla_con(doc, '7 tests auditados')
    if t is not None:
        poner(t.rows[0].cells[0], '12 tests auditados'); poner(t.rows[0].cells[2], '15 generados')
        poner(t.rows[1].cells[0], '13 / 16 flujos')
        poner(t.rows[1].cells[2], '3 flujos → evals')
        poner(t.rows[1].cells[3], 'los tres dependen del modelo')
        n += 1
    n += sustituir(doc, 'Resultado clave:',
        'Resultado clave: 12 tests pasan contra el stack real en %s, cubriendo 13 de 16 flujos '
        '(81,25 %%). La Clase06 fija el umbral con palabras del docente —«cinco flujos cinco features '
        'minimamente deberias tener cinco en tu end» y «80%%... eso es lo minimo recomendable»—; la '
        'primera version de este entregable iba con 10 de 16 (62,5 %%). Los 15 tests generados por el '
        'agente se conservan intactos: 0 aceptados sin correccion. Al cubrir el registro por interfaz '
        'aparecieron DOS defectos reales del producto (§10).' % total_txt)

    # §1 inventario
    t = tabla_con(doc, '#', 'Flujo')
    cab = [texto(c._tc).strip() for c in t.rows[0].cells]
    col_test, col_estado = cab.index('Test'), cab.index('Estado')
    for fila in t.rows[1:]:
        num = texto(fila.cells[0]._tc).strip()
        if num in AHORA_VERDES:
            prueba, estado = AHORA_VERDES[num]
            poner(fila.cells[col_test], prueba)
            poner(fila.cells[col_estado], estado)
            n += 1
    n += sustituir(doc, '10 de 16 flujos en verde',
        '13 de 16 flujos en verde (81,25 %). Los 3 restantes van a evals (motivo en §7): los tres '
        'dependen de que el modelo de IA produzca un cariotipo real.')

    # §2 suite
    for p in doc.paragraphs:
        if texto(p._p).strip() == 'Suite auditada — 7 passed':
            poner(p, 'Suite auditada — 12 passed'); n += 1
    t = tabla_con(doc, '#', 'Test')
    cab = [texto(c._tc).strip() for c in t.rows[0].cells]
    col_dur = cab.index('Duración')
    for fila in t.rows[1:]:
        nombre = texto(fila.cells[1]._tc).split('.spec.ts')[0].strip()
        if nombre in tiempos:
            poner(fila.cells[col_dur], tiempos[nombre] + ' s'); n += 1
    orden = ['registro-por-interfaz', 'registro-validacion', 'edicion-muestra',
             'pagina-degradada', 'bandeja-supervisor']
    titulos = {
        'registro-por-interfaz': 'registro-por-interfaz.spec.ts — el analista registra con metafases desde el formulario',
        'registro-validacion': 'registro-validacion.spec.ts — con los obligatorios vacios no envia y dice cuales faltan',
        'edicion-muestra': 'edicion-muestra.spec.ts — al editar el paciente el cambio queda guardado',
        'pagina-degradada': 'pagina-degradada.spec.ts — la pagina anuncia la caida y ofrece que hacer',
        'bandeja-supervisor': 'bandeja-supervisor.spec.ts — el supervisor abre su bandeja y ve cuantos casos esperan',
    }
    i = len(t.rows)
    for clave in orden:
        anadir_fila(t, [str(i), titulos[clave], tiempos.get(clave, '?') + ' s', '✅ ok'])
        i += 1
    n += sustituir(doc, 'Tiempo total:',
        'Tiempo total: %s (corrida capturada del 23/09, 11 tests). Todos contra el stack real, no '
        'contra un mock: registro-por-interfaz sube tres metafases por el formulario; modo-degradado '
        'registra por API con backend-ml caido; consulta-fuera-de-alcance pasa por el modelo local '
        '—es el mas lento y el unico con presupuesto propio, declarado en su cabecera.' % total_txt)

    # §3 auditoria
    t = tabla_con(doc, 'Caso del plan')
    for fila in FILAS_AUDITORIA:
        anadir_fila(t, fila); n += 1
    n += sustituir(doc, 'Balance:',
        'Balance: Planner por seccion → 15 propuestos · 0 aceptados sin tocar · 9 corregidos · '
        '6 descartados · 6 anadidos por auditoria.  Generator → 15 generados · 0 aceptados · '
        '1 corregido · 14 descartados (7 reescritos). NINGUNO de los 15 salio aceptable sin '
        'intervencion humana, y los cuatro del 23/09 repiten los mismos defectos que los nueve de hace '
        'seis semanas — incluido chnUnico().id sobre un string, identico. El modelo no aprende entre '
        'tandas: lo que evita que eso llegue al repositorio es la auditoria, no el prompt.')

    # §4 tokens
    t = tabla_con(doc, '', 'Entrada (tokens)')
    if t is not None:
        for fila in t.rows[1:]:
            et = texto(fila.cells[0]._tc).strip()
            if et.startswith('Generator, promedio'):
                poner(fila.cells[0], 'Generator, promedio/test (15)')
                poner(fila.cells[1], '697'); poner(fila.cells[2], '349'); poner(fila.cells[3], '357 s')
                n += 1
            elif et.startswith('Generator, total'):
                poner(fila.cells[1], '10 458'); poner(fila.cells[2], '5 245'); poner(fila.cells[3], '89 min')
                n += 1

    # §5 anclas
    t = tabla_con(doc, 'Ancla')
    if t is not None:
        for fila in t.rows[1:]:
            if 'htmlFor' in texto(fila.cells[0]._tc):
                poner(fila.cells[0], 'htmlFor en 15 rotulos + data-testid="metafase-file-input" (ANADIDAS 23/09)')
                poner(fila.cells[2],
                      'Los <input> YA tenian id; faltaba el enlace, asi que getByLabel no encontraba nada y '
                      'conducir el formulario exigia CSS. Es ademas accesibilidad real: un lector de pantalla '
                      'tampoco sabia que rotulo corresponde a cada campo. El input de fichero esta oculto tras '
                      'un boton y no tiene rotulo visible, por eso lleva testid.')
                n += 1
        anadir_fila(t, ['(ninguna en el formulario de EDICION)', 'SampleFormModal',
                        'Correccion a la version anterior: ese formulario SIEMPRE tuvo htmlFor. El flujo 13 '
                        'estaba en evals por arrastrar el diagnostico del de registro sin comprobarlo.'])

    # §7 evals
    t = tabla_con(doc, 'Flujo', 'Motivo')
    if t is not None:
        for fila in list(t.rows[1:]):
            f = texto(fila.cells[0]._tc)
            if 'Registro/edicion' in f or 'Registro/edición' in f:
                fila._tr.getparent().remove(fila._tr); n += 1
    n += sustituir(doc, 'Patron:', 'Patron: lo que no entra en E2E es lo que depende del modelo.')
    n += sustituir(doc, 'Patrón:', 'Patron: lo que no entra en E2E es lo que depende del modelo. '
        'Los tres flujos que quedan exigen un cariotipo real (~32 s por metafase) y un resultado que '
        'el test no puede fijar. La firma MFA del supervisor sigue fuera por el secreto TOTP.')

    # §10 defectos + §9 capturas rehechas
    print('capturas viejas quitadas:', quitar_capturas_viejas(doc))
    doc.add_heading('9 · Capturas', level=1)
    doc.add_paragraph(
        'Las tres capturas van anotadas sobre la propia imagen (recuadro, flecha y nota). Las capturas '
        '1 y 2 son de la misma corrida, la del 23/09; la fecha y hora del reporte lo muestran. '
        'Anotacion reproducible con scripts/anotar_capturas_e2e.py.')
    for archivo, pie in PIES:
        ruta = CAPTURAS / archivo
        if not ruta.exists():
            raise SystemExit('falta ' + str(ruta))
        doc.add_picture(str(ruta), width=Cm(16))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        p = doc.add_paragraph()
        r = p.add_run(pie); r.font.size = Pt(9.5)
        p.paragraph_format.space_after = Pt(14)

    doc.add_heading('10 · Dos defectos del producto que encontro el E2E', level=1)
    doc.add_paragraph(
        'Cubrir el registro POR LA INTERFAZ —no por API, que es como estaba— destapo dos fallos que '
        'los 381 tests de componente no veian, porque sus dobles devuelven «detail» como cadena y el '
        'backend real usa las dos formas. Es el argumento de la piramide al reves: la capa de arriba '
        'es cara, pero ve lo que las de abajo no pueden ver.')
    for titulo, cuerpo in DEFECTOS:
        p = doc.add_paragraph()
        r = p.add_run(titulo); r.bold = True
        doc.add_paragraph(cuerpo)

    doc.save(str(salida))
    print('cambios aplicados:', n)
    print('escrito', salida)


if __name__ == '__main__':
    main()
