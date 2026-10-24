# -*- coding: utf-8 -*-
"""Detecta tests candidatos a duplicados comparando su AST, no su texto.

La consigna define duplicado como: **misma funcion bajo prueba, mismos datos de
entrada y mismo assert, aunque el nombre cambie**. Comparar texto no sirve —los
nombres y los comentarios cambian—, asi que se compara una huella del arbol
sintactico.

Huella de un test = (llamadas, literales, asserts normalizados)

  llamadas  nombres de lo que invoca, quitando el ruido de pytest/fixtures
  literales constantes que usa (los "datos de entrada")
  asserts   la forma del assert con los identificadores normalizados a _

CUIDADO, y la consigna lo avisa: **esto propone, no decide.** Dos tests con la
misma huella pueden ser deliberadamente distintos (p. ej. el mismo assert sobre
dos fixtures con datos opuestos). Cada grupo hay que mirarlo a mano.
"""
import ast
import glob
import io
import json
import os
import sys
from collections import defaultdict

# La raiz del repositorio, deducida de donde vive este fichero: el guion se
# versiona y tiene que correr en cualquier maquina, no solo en la del autor.
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Ruido que no distingue un test de otro.
IGNORAR_LLAMADAS = {
    'raises', 'approx', 'fixture', 'mark', 'parametrize', 'skip', 'xfail',
    'len', 'str', 'int', 'float', 'list', 'set', 'dict', 'tuple', 'sorted',
    'print', 'range', 'enumerate', 'zip', 'sum', 'any', 'all', 'getattr',
}


class Huella(ast.NodeVisitor):
    def __init__(self):
        self.llamadas = []
        self.literales = []
        self.asserts = []
        self.constantes = []      # URL, MODELS_ACTIVE_URL... el endpoint bajo prueba

    def visit_Name(self, nodo):
        if nodo.id.isupper() and len(nodo.id) > 2:
            self.constantes.append(nodo.id)
        self.generic_visit(nodo)

    def visit_Call(self, nodo):
        nombre = None
        f = nodo.func
        if isinstance(f, ast.Name):
            nombre = f.id
        elif isinstance(f, ast.Attribute):
            nombre = f.attr
        if nombre and nombre not in IGNORAR_LLAMADAS:
            self.llamadas.append(nombre)
        self.generic_visit(nodo)

    def visit_Constant(self, nodo):
        if isinstance(nodo.value, (str, int, float, bool)) and nodo.value != '':
            self.literales.append(repr(nodo.value))
        self.generic_visit(nodo)

    def visit_Assert(self, nodo):
        self.asserts.append(_normalizar(nodo.test))
        self.generic_visit(nodo)


def _normalizar(nodo):
    """Serializa una expresion sustituyendo identificadores por `_`.

    Asi `assert resultado == 5` y `assert salida == 5` cuentan como el mismo
    assert: lo que distingue es la FORMA y los valores, no como se llame la
    variable local.
    """
    if isinstance(nodo, ast.Name):
        # Las CONSTANTES de modulo (MAYUSCULAS) son datos de entrada, no
        # variables locales: `URL` y `MODELS_ACTIVE_URL` son endpoints
        # distintos. Normalizarlas a `_` producia 8 falsos positivos.
        return nodo.id if nodo.id.isupper() else '_'
    if isinstance(nodo, ast.Constant):
        return repr(nodo.value)
    if isinstance(nodo, ast.Attribute):
        return '%s.%s' % (_normalizar(nodo.value), nodo.attr)
    if isinstance(nodo, ast.Compare):
        ops = ''.join(type(o).__name__ for o in nodo.ops)
        return '(%s %s %s)' % (_normalizar(nodo.left), ops,
                               ' '.join(_normalizar(c) for c in nodo.comparators))
    if isinstance(nodo, ast.Call):
        f = nodo.func
        # Ruta COMPLETA: `AppearancePreference.objects.filter().count()` y
        # `NotificationPreference...` prueban modelos distintos. Quedarse con
        # `count` los hacia indistinguibles.
        nombre = f.id if isinstance(f, ast.Name) else _normalizar(f)
        return '%s(%s)' % (nombre, ','.join(_normalizar(a) for a in nodo.args))
    if isinstance(nodo, ast.BoolOp):
        return '(%s)' % (' %s ' % type(nodo.op).__name__).join(
            _normalizar(v) for v in nodo.values)
    if isinstance(nodo, ast.UnaryOp):
        return '%s(%s)' % (type(nodo.op).__name__, _normalizar(nodo.operand))
    if isinstance(nodo, (ast.Subscript,)):
        return '%s[]' % _normalizar(nodo.value)
    # Las comprensiones hay que abrirlas: `all(e.fuente for e in X)` y
    # `all(e.nombre and e.descripcion for e in X)` afirman cosas distintas.
    if isinstance(nodo, (ast.GeneratorExp, ast.ListComp, ast.SetComp)):
        return 'comp(%s)' % _normalizar(nodo.elt)
    if isinstance(nodo, ast.DictComp):
        return 'dictcomp(%s:%s)' % (_normalizar(nodo.key), _normalizar(nodo.value))
    return type(nodo).__name__


def tests_de(ruta):
    try:
        arbol = ast.parse(io.open(ruta, 'rb').read().decode('utf-8', errors='replace'))
    except SyntaxError:
        return
    for nodo in ast.walk(arbol):
        if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                and nodo.name.startswith('test_'):
            h = Huella()
            for hijo in nodo.body:
                h.visit(hijo)
            # Sin asserts no hay nada que comparar (suelen ser smoke).
            if not h.asserts:
                continue
            # Las FIXTURES son el dato de entrada en pytest: dos tests que
            # solo se diferencian en que reciben `analyst_client` o
            # `supervisor_client` NO son duplicados, prueban roles distintos.
            # Omitirlas producia falsos positivos en masa (medido: 9 grupos,
            # todos falsos).
            fixtures = tuple(sorted(a.arg for a in nodo.args.args
                                    if a.arg not in ('self',)))
            # `parametrize` tambien aporta datos de entrada distintos.
            params = []
            for dec in nodo.decorator_list:
                params.append(ast.dump(dec))
            huella = (
                tuple(sorted(set(h.llamadas))),
                tuple(sorted(set(h.literales))),
                tuple(sorted(h.asserts)),
                tuple(sorted(set(h.constantes))),
                fixtures,
                tuple(sorted(params)),
            )
            yield {
                'fichero': os.path.relpath(ruta, RAIZ).replace('\\', '/'),
                'nombre': nodo.name,
                'linea': nodo.lineno,
                'huella': huella,
                'n_asserts': len(h.asserts),
            }


def main():
    patrones = [
        'backend-clinic/apps/**/test_*.py',
        'backend-admin/**/test_*.py',
        'backend-ml/tests/**/test_*.py',
    ]
    todos = []
    for pat in patrones:
        for ruta in glob.glob(os.path.join(RAIZ, pat), recursive=True):
            todos.extend(tests_de(ruta))

    grupos = defaultdict(list)
    for t in todos:
        grupos[t['huella']].append(t)

    dups = {k: v for k, v in grupos.items() if len(v) > 1}
    n_dup = sum(len(v) for v in dups.values())

    print('tests con assert analizados : %d' % len(todos))
    print('grupos con huella repetida  : %d' % len(dups))
    print('tests implicados            : %d' % n_dup)
    print()
    print('=' * 78)
    print('CANDIDATOS A DUPLICADO (hay que confirmarlos uno a uno)')
    print('=' * 78)
    for i, (huella, miembros) in enumerate(
            sorted(dups.items(), key=lambda kv: -len(kv[1])), 1):
        print('\n--- grupo %d: %d tests' % (i, len(miembros)))
        print('    assert: %s' % ' | '.join(huella[2])[:110])
        if huella[1]:
            print('    datos : %s' % ', '.join(huella[1])[:110])
        for m in miembros:
            print('      %s:%d  %s' % (m['fichero'], m['linea'], m['nombre']))

    salida = os.path.join(RAIZ, 'docs', 'M7_duplicados.json')
    io.open(salida, 'w', encoding='utf-8').write(json.dumps(
        [{'assert': list(k[2]), 'datos': list(k[1]),
          'miembros': [{'f': m['fichero'], 'l': m['linea'], 'n': m['nombre']} for m in v]}
         for k, v in dups.items()], indent=1, ensure_ascii=False))
    print('\ndetalle en', salida)
    return 0


if __name__ == '__main__':
    sys.exit(main())
