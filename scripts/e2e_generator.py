# -*- coding: utf-8 -*-
"""Agente GENERATOR — escribe los tests E2E, uno por caso del plan APROBADO.

    python scripts/e2e_generator.py --caso E2E-02
    python scripts/e2e_generator.py --todos

## Que hace, y sobre que trabaja

La clase separa Planner y Generator para que el segundo **no genere codigo a
ciegas**: construye los escenarios concretos basandose UNICAMENTE en el plan ya
aprobado. Por eso este guion no lee `plan.json` —la salida cruda del Planner—
sino `plan_auditado.json`, que es el plan despues de que una persona lo revisara
caso por caso.

Esa distincion no es burocracia. La auditoria del plan descarto un caso entero y
corrigio seis: **5 de los 8 casos del Planner emparejaban el caso de uso N con
la regla RN-0N por posicion**, no por significado. Generar sobre el plan crudo
habria producido tests que comprueban la regla equivocada con toda correccion
sintactica.

## Uno por vez

Se genera un fichero por caso, no todos de una tirada. Asi cada test se puede
auditar contra las cinco preguntas por separado, y un fallo del modelo en el
caso 7 no contamina los seis anteriores.

## Tokens

Se reporta entrada y salida por caso y el PROMEDIO POR TEST al final, que es lo
que pide la consigna.

Salida en ASCII puro (la consola de Windows rompe con Unicode).
"""
import argparse
import io
import json
import os
import re
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PLAN = RAIZ / 'docs' / 'M8_E2E' / 'plan_auditado.json'
DESTINO = RAIZ / 'frontend-clinic' / 'e2e'
CRUDOS = RAIZ / 'docs' / 'M8_E2E' / 'salida_generator'

BASE_URL = os.getenv('LOCALHOST_BASE_URL', 'http://localhost:11434/v1')
API_KEY = os.getenv('LOCALHOST_API_KEY', 'local')
MODEL = os.getenv('LOCALHOST_MODEL', 'llama3.2:3b')

#: Anclas que YA existen en el producto. Darselas evita que el modelo invente
#: selectores, que es el fallo numero uno del checklist (P1).
ANCLAS = """
En el visor de cariotipo (/clinic/samples/:id/karyotype) existen ya:
  data-testid="semaphore-legend"        la leyenda de colores
  data-testid="karyo-error"             el aviso de error al cargar
  data-testid="karyo-degraded-banner"   el banner de modo degradado
  data-testid="karyo-validated-banner"  el banner de caso validado
En la bandeja del supervisor (/clinic/supervisor):
  data-testid="inbox-forbidden"         el aviso de acceso denegado
  data-testid="inbox-total-pending"     el contador de pendientes
  data-testid="inbox-error"             el aviso de error
En consultas (/clinic/consultas):
  data-testid="tool-camino"             el camino que tomo la consulta
  data-testid="tool-fuente"             la tabla de procedencia del dato
"""

PLANTILLA = """Eres un agente GENERATOR de pruebas end-to-end con Playwright y
TypeScript. Escribes UN fichero de test para UN caso del plan ya aprobado.

CASO DEL PLAN:
  id       : %(id)s
  flujo    : %(flujo)s
  ruta     : %(ruta)s
  tipo     : %(tipo)s
  oraculo  : %(oraculo)s
  criterio : %(criterio)s

ANCLAS QUE YA EXISTEN EN LA APLICACION (usalas, no inventes otras):
%(anclas)s

AYUDANTES DISPONIBLES, importalos de '../fixtures/sesion':
  test, expect              (envoltorio de @playwright/test)
  pedirToken(request, cred) pide un JWT real a backend-admin
  sembrarSesion(page, tok)  deja el token antes de que cargue la app
  chnUnico()                devuelve un CHN nuevo, para que el test no choque
  ANALISTA, SUPERVISOR      credenciales

REGLAS OBLIGATORIAS:
1. SELECTORES: usa getByRole, getByLabel, getByText o data-testid. NUNCA XPath,
   nunca clases CSS de estilo, nunca posiciones.
2. ESPERAS: usa el auto-waiting de Playwright y expect(). NUNCA waitForTimeout
   ni sleep.
3. AISLAMIENTO: el test crea sus propios datos con chnUnico(). No depende de
   otro test ni del orden.
4. ORACULO: termina con al menos un expect() que compruebe el criterio contra
   la regla de negocio. Navegar sin comprobar no es un test.
5. Un solo test por fichero, con nombre que describa el comportamiento.

Devuelve SOLO el codigo TypeScript del fichero, sin explicaciones ni markdown.
"""


def cargar_casos():
    d = json.load(io.open(PLAN, encoding='utf-8'))
    return [c for c in d['casos'] if c.get('veredicto') != 'descartado']


def nombre_fichero(caso):
    slug = re.sub(r'[^a-z0-9]+', '-', (caso.get('flujo') or '').lower()).strip('-')
    return '%s-%s.spec.ts' % (caso['id'].lower(), slug[:40])


def extraer_codigo(respuesta):
    bloque = re.search(r'```(?:typescript|ts)?\n(.*?)```', respuesta, re.S)
    return (bloque.group(1) if bloque else respuesta).strip() + '\n'


def generar(cliente, caso):
    prompt = PLANTILLA % {
        'id': caso['id'], 'flujo': caso['flujo'], 'ruta': caso['ruta'],
        'tipo': caso['tipo'], 'oraculo': caso['oraculo'],
        'criterio': caso['criterio'], 'anclas': ANCLAS.strip(),
    }
    t0 = time.time()
    r = cliente.chat.completions.create(
        model=MODEL, temperature=0,
        messages=[
            {'role': 'system', 'content': (
                'Escribes tests de Playwright en TypeScript. Devuelves SOLO codigo.')},
            {'role': 'user', 'content': prompt},
        ])
    segundos = round(time.time() - t0, 1)
    codigo = extraer_codigo(r.choices[0].message.content or '')
    u = r.usage
    return codigo, (u.prompt_tokens if u else 0), (u.completion_tokens if u else 0), segundos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--caso', default=None, help='un id concreto, p.ej. E2E-02')
    ap.add_argument('--todos', action='store_true')
    opts = ap.parse_args()

    from openai import OpenAI

    casos = cargar_casos()
    if opts.caso:
        casos = [c for c in casos if c['id'] == opts.caso]
        if not casos:
            raise SystemExit('no existe el caso %s en el plan aprobado' % opts.caso)
    elif not opts.todos:
        casos = casos[:1]

    CRUDOS.mkdir(parents=True, exist_ok=True)
    cliente = OpenAI(base_url=BASE_URL, api_key=API_KEY, timeout=900.0)

    print('GENERATOR -> modelo=%s via %s' % (MODEL, BASE_URL))
    print('plan aprobado: %d casos (los descartados no se generan)\n' % len(casos))

    entradas, salidas, tiempos = [], [], []
    for caso in casos:
        codigo, t_in, t_out, seg = generar(cliente, caso)
        entradas.append(t_in)
        salidas.append(t_out)
        tiempos.append(seg)

        # La salida cruda se guarda intacta ANTES de tocarla: es la evidencia
        # sobre la que se hace la auditoria de las cinco preguntas.
        # Solo se escribe el CRUDO. El fichero que acaba en `e2e/` lo pone la
        # persona tras auditar: si el generador escribiera ahi directamente,
        # una segunda tanda pisaria los tests ya corregidos y se perderia el
        # trabajo de auditoria.
        io.open(CRUDOS / ('%s_crudo.ts' % caso['id']), 'w',
                encoding='utf-8', newline='\n').write(codigo)

        print('%-8s %-46s in=%-6d out=%-6d %ss'
              % (caso['id'], nombre_fichero(caso)[:46], t_in, t_out, seg))

    n = max(1, len(casos))
    print()
    print('=' * 68)
    print('  tests generados            : %d' % len(casos))
    print('  tokens entrada  total/med  : %d / %d' % (sum(entradas), sum(entradas) // n))
    print('  tokens salida   total/med  : %d / %d' % (sum(salidas), sum(salidas) // n))
    print('  PROMEDIO POR TEST          : %d entrada + %d salida'
          % (sum(entradas) // n, sum(salidas) // n))
    print('  tiempo total               : %.1f s' % sum(tiempos))
    print('=' * 68)
    print('\n  crudos en %s' % CRUDOS.relative_to(RAIZ))
    print('  los tests auditados los escribe la persona en frontend-clinic/e2e/')
    print('\n  SIGUIENTE: auditar cada uno contra las cinco preguntas.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
