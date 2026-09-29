# -*- coding: utf-8 -*-
"""Arma el entregable de Evals (M7 · Dia 10) en un solo Markdown.

    python scripts/armar_docx_evals.py [commit]
    cd docs && ../backend-clinic/.venv/Scripts/python md_a_word.py \\
        M7_EVALS/ENTREGABLE_EVALS.md

## Por que un guion y no copiar y pegar

La tabla de resultados se genera **leyendo `resultados/*.md`**, que a su vez los
genera `eval_calidad.py` leyendo `respuestas/*.jsonl`. Si una cifra del informe
no coincide con la evidencia, es porque alguien la escribio a mano — aqui no
puede pasar. Misma regla que el entregable de red teaming.

## La calibracion puede faltar, y se dice

Las 15 etiquetas humanas las pone una persona. Si todavia no estan, el documento
sale con el hueco marcado en vez de con una cifra inventada: un entregable que
presenta como medido algo que nadie midio vale menos que uno que declara lo que
le falta.

Salida en ASCII puro en consola; el Markdown va en UTF-8.
"""
import io
import json
import re
import unicodedata
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
BASE = RAIZ / 'docs' / 'M7_EVALS'
DESTINO = BASE / 'ENTREGABLE_EVALS.md'

VERSIONES = ('v1', 'v2', 'v3')

CABECERA = """# Entregable M7 · Dia 10 — Evaluaciones offline del asistente de BIOMED

| | |
|---|---|
| **Equipo** | **BIOMED UMSS** — Ing. Guillermo Mamani Chambi (individual, G04) |
| **Producto** | Plataforma de Cariotipado Asistido por IA — asistente documental de `backend-clinic` |
| **Modelo evaluado** | `llama3.2:3b` local sobre Ollama (ADR-0024), temperatura 0 |
| **Repositorio** | rama `feature/clinic-django-stack`, commit `%(commit)s` |
| **Carpetas** | `docs/M7_EVALS/` · `scripts/eval_calidad.py` |

> «Hoy no lo atacamos: lo medimos.» — M7 · Dia 10

**Alcance y etica.** Se evalua el propio sistema, en local, con el corpus
documental del proyecto. `docs/INFORMES CARIOTIPOS/` —los 462 informes clinicos
reales— no entra aqui ni como lectura.

## Resumen

| | |
|---|---|
| **17 casos** | dataset dorado, **9 criticos** en 5 categorias |
| **3 versiones** | del prompt, evaluadas con las mismas metricas |
| **3 compuertas** | las tres **BLOQUEAN**: ninguna sale a produccion |
| **3 fallos del instrumento** | cazados y corregidos antes de creerse las cifras |

La consigna pedia **15** casos, **4** criticos y **2** versiones de prompt.

"""


def seccion(ruta, nivel_extra=1):
    """Inserta un Markdown bajando sus encabezados un nivel."""
    texto = (BASE / ruta).read_text(encoding='utf-8')
    salida = []
    for linea in texto.split('\n'):
        if linea.startswith('#'):
            linea = '#' * nivel_extra + linea
        salida.append(linea)
    return '\n'.join(salida)


def _sin_tildes(t):
    d = unicodedata.normalize('NFD', t)
    return ''.join(c for c in d if unicodedata.category(c) != 'Mn')


def corte(texto, desde, hasta=None):
    """Trozo de un Markdown entre dos encabezados, sin el encabezado inicial.

    La busqueda ignora los acentos: los encabezados del README llevan tilde
    («Como se construyo») y este fichero se escribe en ASCII puro porque su
    salida va a la consola de Windows. Emparejarlos por la forma sin tildes
    evita mantener las mismas cadenas escritas de dos maneras, que es como se
    rompen los ensambladores al retocar un titulo.
    """
    plano = _sin_tildes(texto)
    a = plano.index(_sin_tildes(desde))
    b = plano.index(_sin_tildes(hasta)) if hasta else len(texto)
    return texto[a:b].split('\n', 1)[1].strip()


def tabla_resultados():
    """Lee la compuerta de cada informe en vez de transcribirla."""
    filas = {}
    for v in VERSIONES:
        ruta = BASE / 'resultados' / ('%s_heuristico.md' % v)
        if not ruta.exists():
            raise SystemExit('falta el informe de %s: corre «correr %s»' % (v, v))
        txt = ruta.read_text(encoding='utf-8')
        datos = {}
        for clave in ('completitud', 'fidelidad', 'sin_prohibidos'):
            m = re.search(r'\|\s*%s\s*\|\s*([^|]+?)\s*\|' % clave, txt)
            datos[clave] = m.group(1) if m else '?'
        m = re.search(r'\|\s*criticos perfectos\s*\|\s*([^|]+?)\s*\|', txt)
        datos['criticos'] = m.group(1) if m else '?'
        datos['pasa'] = 'PASA' if 'devuelve 0' in txt else 'BLOQUEA'
        # Cuantas respondio, leido de la propia corrida.
        rs = [json.loads(l) for l in
              io.open(BASE / 'respuestas' / ('%s.jsonl' % v), encoding='utf-8')]
        datos['responde'] = '%d/%d' % (sum(1 for r in rs if r['responde']), len(rs))
        filas[v] = datos

    orden = [('responde', 'preguntas respondidas'),
             ('completitud', 'completitud'),
             ('fidelidad', 'fidelidad'),
             ('sin_prohibidos', 'sin prohibidos'),
             ('criticos', 'criticos perfectos'),
             ('pasa', '**compuerta**')]
    out = ['| | %s |' % ' | '.join(VERSIONES),
           '|---|%s' % ('---|' * len(VERSIONES))]
    for clave, etiqueta in orden:
        out.append('| %s | %s |' % (etiqueta,
                                    ' | '.join(filas[v][clave] for v in VERSIONES)))
    return '\n'.join(out)


def main():
    commit = sys.argv[1] if len(sys.argv) > 1 else 'PENDIENTE'
    readme = (BASE / 'README.md').read_text(encoding='utf-8')
    partes = [CABECERA % {'commit': commit}]

    partes.append('# 1 · El dataset dorado\n')
    partes.append(corte(readme, '## Como se construyo el dataset',
                        '## Las metricas'))

    partes.append('\n\n# 2 · Las metricas y la compuerta\n')
    partes.append(corte(readme, '## Las metricas', '## El resultado'))
    partes.append('\n\n## Los umbrales, y por que estos\n')
    u = json.loads((BASE / 'umbrales.json').read_text(encoding='utf-8'))
    partes.append('| Umbral | Valor | Por que |\n|---|---|---|')
    etiquetas = {'completitud_minima': 'completitud',
                 'fidelidad_minima': 'fidelidad',
                 'sin_prohibidos_minimo': 'sin prohibidos',
                 'criticos_perfectos': 'criticos perfectos'}
    for clave, etiqueta in etiquetas.items():
        valor = u[clave]
        valor = 'todos' if valor is True else ('%.2f' % valor)
        partes.append('| %s | %s | %s |'
                      % (etiqueta, valor, u['por_que'][clave].replace('\n', ' ')))
    partes.append('\n%s\n' % u['de_donde_salen'])

    partes.append('\n\n# 3 · Resultados\n')
    partes.append('Tabla generada por `scripts/armar_docx_evals.py` **leyendo '
                  '`resultados/*.md`**: si una cifra no coincide con los '
                  'informes, es porque alguien la escribio a mano.\n')
    partes.append(tabla_resultados())
    partes.append('\n\n' + corte(readme, '## El resultado',
                                 '## La calibracion del juez'))

    partes.append('\n\n# 4 · Calibracion del juez\n')
    calib = sorted((BASE / 'resultados').glob('calibracion_*.md'))
    if calib:
        # Primero las cifras que genera `eval_calidad.py calibrar` (tabla y
        # desacuerdos crudos), y despues la lectura del anotador. En ese orden
        # porque la interpretacion tiene que poder contrastarse con el dato, no
        # sustituirlo.
        partes.append(seccion('resultados/' + calib[0].name).split('\n', 1)[1].lstrip())
        partes.append('\n\n## Lectura de los desacuerdos\n')
        partes.append(corte(readme, '## La calibracion del juez',
                            '## Lo que este ejercicio dice')
                      .split('### Los cuatro desacuerdos', 1)[-1]
                      .split('\n', 1)[-1].lstrip())
    else:
        partes.append(
            '**PENDIENTE.** Las 15 etiquetas humanas las pone una persona, y la '
            'plantilla (`datos/etiquetas_humanas.csv`, 22 oraciones de las tres '
            'corridas) todavia no esta rellenada.\n\n'
            'No se rellena con otro modelo a proposito: la calibracion compara '
            'al juez **con un humano**, y hacerlo con una maquina mediria el '
            'acuerdo entre dos maquinas sin decir nada de si el juez sirve. '
            'Mientras no este, `APOYO_MINIMO = 0,55` es una **suposicion '
            'declarada** y la fidelidad de la tabla anterior hereda ese error.\n\n'
            'Se cierra con:\n\n'
            '```\n'
            'python scripts/eval_calidad.py calibrar v2\n'
            '```\n')

    partes.append('\n\n# 5 · Lo que este ejercicio dice, y lo que no\n')
    partes.append(corte(readme, '## Lo que este ejercicio dice',
                        '## Los tres fallos del instrumento'))

    partes.append('\n\n# 6 · Los tres fallos del instrumento\n')
    partes.append(corte(readme, '## Los tres fallos del instrumento',
                        '## Nota sobre el prompt v1'))

    partes.append('\n\n# 7 · Reproducibilidad y coste\n')
    partes.append(corte(readme, '## Como se reproduce', '## Como se construyo'))
    partes.append('\n' + corte(readme, '## Nota sobre el prompt v1'))
    for v in VERSIONES:
        txt = (BASE / 'resultados' / ('%s_heuristico.md' % v)).read_text(encoding='utf-8')
        partes.append('\n\n## Coste de la corrida %s\n' % v)
        partes.append(corte(txt, '## Coste de una corrida completa'))

    DESTINO.write_text('\n'.join(partes), encoding='utf-8')
    n = len(DESTINO.read_text(encoding='utf-8').split('\n'))
    print('escrito %s (%d lineas)' % (DESTINO.relative_to(RAIZ), n))
    if not calib:
        print('AVISO: sin calibracion. El documento lo dice en la seccion 4.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
