# -*- coding: utf-8 -*-
"""Vuelve a medir TODO lo que afirma el documento de la Actividad 2.

    python scripts/verificar_entrega_m7.py

Un informe de pruebas que hay que creerse no es un informe de pruebas. Este
guion recorre cada cifra del entregable, la mide de nuevo desde cero y la
compara con lo que el documento dice. Termina imprimiendo una tabla
AFIRMADO / MEDIDO / VEREDICTO y sale con codigo 1 si alguna no cuadra.

Tarda unos 12 minutos: la suite completa son ~10, y se corre entera a
proposito. Medir solo una parte seria el mismo atajo que este modulo enseña a
no tomar.

No necesita modelo ni red: `CLINIC_LLM_ENABLED=false` y `CLINIC_LLM_URL`
apuntando a un puerto muerto, igual que la corrida final del documento.
"""
import io
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CLINIC = RAIZ / 'backend-clinic'
ADMIN = RAIZ / 'backend-admin'


def interprete(proyecto):
    py = proyecto / '.venv' / 'Scripts' / 'python.exe'
    return py if py.exists() else proyecto / '.venv' / 'bin' / 'python'


PY = interprete(CLINIC)
PY_ADMIN = interprete(ADMIN)

# Lo que el documento afirma. Cambiar una cifra aqui sin volver a medir es
# exactamente lo que este guion existe para impedir.
AFIRMADO = {
    'tests_verdes': 868,
    'tests_omitidos': 1,
    'produccion_pct': 96.33,
    'informe_apps_pct': 88.59,
    'produccion_ficheros': 47,
    'produccion_sentencias': 2809,
    'produccion_cubiertas': 2706,
    'grupos_duplicados': 0,
    'tests_auditados': 5,
    'tests_sin_auditar': 0,
    'huecos_al_100': ['rag_qa.py', 'rag_index.py', 'agente_acciones.py',
                      'admin_client.py', 'pipeline_client.py'],
}

ENTORNO_SIN_IA = dict(os.environ,
                      CLINIC_LLM_ENABLED='false',
                      CLINIC_LLM_URL='http://127.0.0.1:1/v1')


def correr(argumentos, cwd, entorno=None, py=None):
    r = subprocess.run([str(py or PY)] + argumentos, cwd=str(cwd), env=entorno or os.environ,
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    return (r.stdout or '') + (r.returncode and (r.stderr or '') or '')


def norm(ruta):
    return ruta.replace(chr(92), '/')


def es_test(ruta):
    q = norm(ruta)
    return '/tests/' in q or os.path.basename(q).startswith('test_')


def es_cli(ruta):
    return '/management/commands/' in norm(ruta)


# --- las mediciones ---------------------------------------------------------

def medir_suite(destino_json):
    """La corrida completa con cobertura, sin modelo ni red."""
    salida = correr(['-m', 'pytest', '-p', 'no:randomly', '--cov=.',
                     '--cov-report=json:' + str(destino_json),
                     '--cov-fail-under=0', '-q'], CLINIC, ENTORNO_SIN_IA)
    m = re.search(r'(\d+) passed', salida)
    if not m:
        print(salida[-3000:])
        raise SystemExit('la suite no reporto resultados')
    fallos = re.search(r'(\d+) failed', salida)
    return {
        'tests_verdes': int(m.group(1)),
        'fallos': int(fallos.group(1)) if fallos else 0,
        'tiempo': re.search(r'in ([\d.]+)s', salida).group(1) if re.search(r'in ([\d.]+)s', salida) else '?',
    }


def medir_cobertura(ruta_json):
    d = json.load(io.open(ruta_json, encoding='utf-8'))
    apps = {k: v for k, v in d['files'].items() if norm(k).startswith('apps/')}
    prod = {k: v for k, v in apps.items()
            if not es_test(k) and not es_cli(k) and v['summary']['num_statements'] > 0}
    st = sum(v['summary']['num_statements'] for v in prod.values())
    cv = sum(v['summary']['covered_lines'] for v in prod.values())
    st_a = sum(v['summary']['num_statements'] for v in apps.values())
    cv_a = sum(v['summary']['covered_lines'] for v in apps.values())
    por_fichero = {os.path.basename(norm(k)): round(v['summary']['percent_covered'], 1)
                   for k, v in prod.items()}
    return {
        'produccion_pct': round(100.0 * cv / st, 2),
        'informe_apps_pct': round(100.0 * cv_a / st_a, 2),
        'produccion_ficheros': len(prod),
        'produccion_sentencias': st,
        'produccion_cubiertas': cv,
        'por_fichero': por_fichero,
    }


def medir_duplicados():
    salida = correr([str(RAIZ / 'scripts' / 'detectar_duplicados.py')], RAIZ)
    g = re.search(r'grupos con huella repetida\s*:\s*(\d+)', salida)
    t = re.search(r'tests con assert analizados\s*:\s*(\d+)', salida)
    return {'grupos_duplicados': int(g.group(1)) if g else -1,
            'tests_con_assert': int(t.group(1)) if t else -1}


def medir_omitidos():
    """El test omitido vive en backend-admin, no en el clinico.

    La primera version de este guion contaba los `skipped` de la corrida del
    clinico y reportaba 0 frente al 1 que afirma el documento. **El documento
    tenia razon**: la §3.1 dice explicitamente que el omitido esta en
    `backend-admin/apps/audit/tests/`. El que medía mal era el medidor.

    Se deja escrito porque es la quinta vez que pasa en este modulo, y es la
    leccion que el modulo enseña: la primera medicion falla por el instrumento.
    """
    salida = correr(['-m', 'pytest', 'apps/audit/tests/test_audit_endpoint.py',
                     '-q', '--no-cov', '-p', 'no:randomly'],
                    ADMIN, ENTORNO_SIN_IA, py=PY_ADMIN)
    m = re.search(r'(\d+) skipped', salida)
    return {'tests_omitidos': int(m.group(1)) if m else 0}


def medir_marcas():
    def cuenta(marca):
        salida = correr(['-m', 'pytest', '-m', marca, '-q', '--no-cov',
                         '-p', 'no:randomly'], CLINIC, ENTORNO_SIN_IA)
        m = re.search(r'(\d+) passed', salida)
        return int(m.group(1)) if m else 0
    return {'tests_auditados': cuenta('auditado'), 'tests_sin_auditar': cuenta('agente')}


# --- el informe -------------------------------------------------------------

def comparar(clave, afirmado, medido, tolerancia=0.0):
    if isinstance(afirmado, float):
        ok = abs(afirmado - medido) <= tolerancia
    else:
        ok = afirmado == medido
    return ok, '%-24s  %-14s  %-14s  %s' % (
        clave, afirmado, medido, 'OK' if ok else '*** NO CUADRA ***')


def main():
    if not PY.exists():
        raise SystemExit('no encuentro el interprete del venv en %s' % PY)

    t0 = time.time()
    tmp = RAIZ / 'docs' / '_verificacion_cov.json'
    print('== 1/5  suite completa, sin modelo ni red (esto tarda ~10 min)')
    suite = medir_suite(tmp)
    print('   %d pasan, %d fallos, %s s'
          % (suite['tests_verdes'], suite['fallos'], suite['tiempo']))

    print('== 2/5  cobertura sobre apps/')
    cob = medir_cobertura(tmp)
    print('   produccion %.2f %%   informe %.2f %%'
          % (cob['produccion_pct'], cob['informe_apps_pct']))

    print('== 3/5  detector de duplicados')
    dup = medir_duplicados()
    print('   %d grupos sobre %d tests con assert'
          % (dup['grupos_duplicados'], dup['tests_con_assert']))

    print('== 4/5  marcas del LabX')
    marcas = medir_marcas()
    print('   auditados %d, sin auditar %d'
          % (marcas['tests_auditados'], marcas['tests_sin_auditar']))

    print('== 5/5  tests omitidos (viven en backend-admin, no en el clinico)')
    omitidos = medir_omitidos()
    print('   %d omitido(s)' % omitidos['tests_omitidos'])

    medido = {}
    medido.update(suite)
    medido.update(cob)
    medido.update(dup)
    medido.update(marcas)
    medido.update(omitidos)

    print('\n' + '=' * 74)
    print('%-24s  %-14s  %-14s  %s' % ('AFIRMA EL DOCUMENTO', 'AFIRMADO', 'MEDIDO', ''))
    print('=' * 74)
    todo_ok = True
    for clave, esperado in AFIRMADO.items():
        if clave == 'huecos_al_100':
            continue
        ok, linea = comparar(clave, esperado, medido.get(clave), tolerancia=0.01)
        todo_ok = todo_ok and ok
        print(linea)

    print('-' * 74)
    for fichero in AFIRMADO['huecos_al_100']:
        pct = cob['por_fichero'].get(fichero)
        ok = pct == 100.0
        todo_ok = todo_ok and ok
        print('%-24s  %-14s  %-14s  %s' % (fichero, '100 %',
                                           '%s %%' % pct, 'OK' if ok else '*** NO ***'))

    print('-' * 74)
    ok_fallos = suite['fallos'] == 0
    todo_ok = todo_ok and ok_fallos
    print('%-24s  %-14s  %-14s  %s' % ('fallos', 0, suite['fallos'],
                                       'OK' if ok_fallos else '*** NO ***'))
    print('=' * 74)
    print('verificacion completa en %d min %d s' % ((time.time() - t0) // 60,
                                                    (time.time() - t0) % 60))
    try:
        tmp.unlink()
    except OSError:
        pass

    if todo_ok:
        print('\nTODAS LAS CIFRAS DEL DOCUMENTO CUADRAN CON LA MEDICION.')
        return 0
    print('\nHAY CIFRAS QUE NO CUADRAN: corregir el documento, no la medicion.')
    return 1


if __name__ == '__main__':
    sys.exit(main())
