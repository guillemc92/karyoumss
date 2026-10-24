# -*- coding: utf-8 -*-
"""Separa las tres cifras de cobertura que `pytest-cov` mezcla en una sola.

El porcentaje que imprime pytest-cov no sirve para decidir donde trabajar,
porque mete en el mismo saco tres poblaciones distintas:

    los ficheros de test        estan al 100 % por construccion: inflan
    los management/commands     guiones de demo y evaluadores que se lanzan a
                                mano; cubrirlos con unit tests no protege nada
    el codigo de produccion     lo unico que un fallo de cobertura pone en
                                riesgo de verdad

Este guion imprime las tres y ordena los ficheros de produccion por lo que les
falta, que es la lista de trabajo.

    python scripts/cobertura_produccion.py cov.json [prefijo]

El informe se genera con:

    python -m pytest --cov=. --cov-report=json:cov.json --cov-fail-under=0

El `prefijo` opcional restringe el agregado a una parte del arbol —`apps/` para
comparar contra mediciones anteriores que solo cubrian el codigo de dominio, sin
`manage.py`, `wsgi/asgi` ni los guiones MCP sueltos—. Los porcentajes por
fichero no cambian; lo que cambia es sobre que poblacion se suma.
"""
import io
import json
import os
import sys

BARRA = chr(92)
HUECOS_ACTIVIDAD2 = ('rag_qa.py', 'rag_index.py', 'agente_acciones.py',
                     'admin_client.py', 'pipeline_client.py')


def norm(ruta):
    return ruta.replace(BARRA, '/')


def es_test(ruta):
    q = norm(ruta)
    return '/tests/' in q or os.path.basename(q).startswith('test_')


def es_cli(ruta):
    return '/management/commands/' in norm(ruta)


def produccion(informe, prefijo=''):
    """Los ficheros que importan: ni tests, ni CLI, ni modulos vacios."""
    return {k: v for k, v in informe['files'].items()
            if norm(k).startswith(prefijo) and not es_test(k) and not es_cli(k)
            and v['summary']['num_statements'] > 0}


def main(ruta_informe, prefijo='', top=10):
    informe = json.load(io.open(ruta_informe, encoding='utf-8'))
    prod = produccion(informe, prefijo)
    sentencias = sum(v['summary']['num_statements'] for v in prod.values())
    cubiertas = sum(v['summary']['covered_lines'] for v in prod.values())
    pct = 100.0 * cubiertas / sentencias

    print('informe completo   %6.2f %%   (todo lo que mide pytest-cov)'
          % informe['totals']['percent_covered'])
    print('produccion%-9s %6.2f %%   (%d ficheros, %d sentencias, %d cubiertas)'
          % (' ' + prefijo if prefijo else '', pct, len(prod), sentencias, cubiertas))

    print('\n--- los cinco huecos de la Actividad 2 ---')
    for nombre in HUECOS_ACTIVIDAD2:
        for k, v in prod.items():
            if norm(k).endswith('/' + nombre):
                print('  %-22s %6.1f %%   faltan %d'
                      % (nombre, v['summary']['percent_covered'],
                         v['summary']['missing_lines']))

    print('\n--- los %d peores que quedan ---' % top)
    peores = sorted(prod.items(),
                    key=lambda kv: kv[1]['summary']['percent_covered'])[:top]
    for k, v in peores:
        print('  %-52s %6.1f %%   faltan %d'
              % (norm(k), v['summary']['percent_covered'],
                 v['summary']['missing_lines']))
    return 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else ''))
