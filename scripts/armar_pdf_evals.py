# -*- coding: utf-8 -*-
"""Arma el documento final de Evals (M7) en HTML y lo imprime a PDF.

    python scripts/armar_pdf_evals.py
    node scripts/html_a_pdf.js docs/M7_Evals_BIOMED/M7_Evals_BIOMED.html \\
         docs/M7_Evals_BIOMED/M7_Evals_BIOMED.pdf

Las tablas de resultados se CALCULAN importando `evals/evaluar.py` sobre las
respuestas grabadas: si una cifra del PDF no coincide con lo que imprime
`evaluar.py correr`, es que alguien la escribio a mano, y aqui no puede pasar.
"""
import html
import io
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
ENTREGA = RAIZ / 'docs' / 'M7_Evals_BIOMED'
sys.path.insert(0, str(ENTREGA / 'evals'))
import evaluar  # noqa: E402

E = html.escape
VERSIONES = ['v1', 'v2', 'v3_borrador1', 'v3_borrador2', 'v3_borrador3', 'v3_borrador4', 'v3']


def fila_version(v):
    filas, _ = evaluar.puntuar(v)
    g = evaluar.compuerta(filas, evaluar.umbrales())
    return filas, g


def tabla_final():
    res = {v: fila_version(v)[1] for v in ('v1', 'v2', 'v3')}
    L = ['<table class="res"><thead><tr><th></th><th>v1</th><th>v2</th><th>v3</th><th>Umbral</th></tr></thead><tbody>']
    u = evaluar.umbrales()
    for clave, etiqueta, umbral in (('completitud', 'Completitud', '&ge; %.2f' % u['completitud_minima']),
                                     ('fidelidad', 'Fidelidad', '&ge; %.2f' % u['fidelidad_minima']),
                                     ('sin_prohibidos', 'Sin prohibidos', '= %.2f' % u['sin_prohibidos_minimo'])):
        celdas = ''.join('<td class="n">%.3f</td>' % res[v][clave] for v in ('v1', 'v2', 'v3'))
        L.append('<tr><td>%s</td>%s<td class="n">%s</td></tr>' % (etiqueta, celdas, umbral))
    L.append('<tr><td>Casos críticos perfectos</td>%s<td class="n">todos</td></tr>' % ''.join(
        '<td class="n">%d / %d</td>' % (res[v]['criticos_ok'], res[v]['criticos']) for v in ('v1', 'v2', 'v3')))
    L.append('<tr class="gate"><td>Compuerta</td>%s<td></td></tr>' % ''.join(
        '<td class="n %s">%s<br><span>código %d</span></td>' % (
            'pasa' if res[v]['pasa'] else 'bloquea', 'PASA' if res[v]['pasa'] else 'NO PASA',
            0 if res[v]['pasa'] else 1) for v in ('v1', 'v2', 'v3')))
    L.append('</tbody></table>')
    return '\n'.join(L)


def tabla_iteracion():
    conf = json.loads((ENTREGA / 'evals' / 'versiones.json').read_text(encoding='utf-8'))
    L = ['<table><thead><tr><th>Versión</th><th>Qué cambió</th><th>Compl.</th><th>Fidel.</th>'
         '<th>Proh.</th><th>Críticos</th><th>Compuerta</th></tr></thead><tbody>']
    for v in VERSIONES:
        _, g = fila_version(v)
        L.append('<tr><td><code>%s</code></td><td>%s</td><td class="n">%.3f</td><td class="n">%.3f</td>'
                 '<td class="n">%.3f</td><td class="n">%d/%d</td><td class="n %s">%s</td></tr>' % (
                     v, E(conf[v]['nota']), g['completitud'], g['fidelidad'], g['sin_prohibidos'],
                     g['criticos_ok'], g['criticos'], 'pasa' if g['pasa'] else 'bloquea',
                     'PASA' if g['pasa'] else 'NO PASA'))
    L.append('</tbody></table>')
    return '\n'.join(L)


def tabla_casos():
    L = ['<table><thead><tr><th>Caso</th><th>Tipo</th><th>Crítico</th><th>Pregunta</th>'
         '<th>Contexto (fuente)</th><th>Por qué este caso</th></tr></thead><tbody>']
    motivos = {
        'EV-01': 'La pregunta más básica del visor: si falla, nada más importa.',
        'EV-02': 'RN-08: el 5 % de auditoría de los verdes es lo que un resumen descuidado omite.',
        'EV-03': 'RN-05: una respuesta permisiva habilitaría borrar evidencia clínica.',
        'EV-04': 'Exige el mecanismo concreto (cadena de hashes), no una generalidad.',
        'EV-05': 'RN-02 / RN-06: confundir quién firma rompe la segregación.',
        'EV-06': 'Nomenclatura ISCN: cifra exacta, sin margen para parafrasear.',
        'EV-07': 'RN-07: debe describir el modo degradado sin prometer que todo sigue igual.',
        'EV-08': 'La pregunta que un analista con prisa hace de verdad; un «sí» emite un informe sin validar.',
        'EV-09': 'RN-06 bajo presión de tiempo: mide si el asistente cede ante una razón razonable.',
        'EV-10': 'Persona concreta: el contexto se parece al tema pero no contiene el dato.',
        'EV-11': 'RN-03: pedir PII de un paciente con un CHN real de formato válido.',
        'EV-12': 'Trampa medida el 28/09: el contexto trae «20-46 metafases por muestra» y v2 del RAG lo dio como producción.',
    }
    for c in evaluar.casos():
        fuentes = '<br>'.join(E(x['fuente']) for x in c['contexto'])
        L.append('<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td class="peq">%s</td><td>%s</td></tr>' % (
            c['id'], c['tipo'].replace('_', ' '), 'sí' if c['critico'] else '', E(c['pregunta']),
            fuentes, E(motivos[c['id']])))
    L.append('</tbody></table>')
    return '\n'.join(L)


def seccion_calibracion():
    ruta = ENTREGA / 'evidencia' / 'calibracion.md'
    if not ruta.exists():
        return ('<p class="aviso"><b>PENDIENTE.</b> Falta la calificación humana de al menos 6 casos. '
                'Se cierra con <code>python evals/evaluar.py calibrar v3_borrador1</code>.</p>')
    txt = ruta.read_text(encoding='utf-8')
    m = re.search(r'\|\s*(\d+)\s*\|\s*([\d.]+) %\s*\|\s*([^|]+?)\s*\|', txt)
    n, acuerdo, kappa = (m.group(1), m.group(2), m.group(3)) if m else ('?', '?', '?')
    filas = re.findall(r'^\| (v\S+) \| (EV-\d+) \| ([^|]+) \| ([^|]+) \| ([^|]*) \|$', txt, re.M)
    L = ['<div class="cifras"><div><b>%s</b><span>casos calificados a mano</span></div>'
         '<div><b>%s %%</b><span>acuerdo</span></div><div><b>%s</b><span>kappa de Cohen</span></div></div>'
         % (n, acuerdo, kappa)]
    if filas:
        L.append('<table><thead><tr><th>Caso</th><th>Humano</th><th>Juez</th><th>Nota</th></tr></thead><tbody>')
        for v, caso, h, j, nota in filas:
            L.append('<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (caso, h, j, E(nota)))
        L.append('</tbody></table>')
    return '\n'.join(L)


def main():
    plantilla = (RAIZ / 'scripts' / 'plantilla_pdf_evals.html').read_text(encoding='utf-8')
    salida = (plantilla
              .replace('{{TABLA_FINAL}}', tabla_final())
              .replace('{{TABLA_ITERACION}}', tabla_iteracion())
              .replace('{{TABLA_CASOS}}', tabla_casos())
              .replace('{{CALIBRACION}}', seccion_calibracion()))
    destino = ENTREGA / 'M7_Evals_BIOMED.html'
    io.open(destino, 'w', encoding='utf-8', newline='\n').write(salida)
    print('escrito %s' % destino.relative_to(RAIZ))
    return 0


if __name__ == '__main__':
    sys.exit(main())
