# -*- coding: utf-8 -*-
"""Agente PLANNER — audita la aplicacion y define el plan de pruebas E2E.

    python scripts/e2e_planner.py [--salida docs/M8_E2E/plan.json]

## Que hace, y sobre todo que NO hace

La clase separa el ciclo en dos agentes por una razon: **evitar que la IA
escriba codigo a ciegas**. El Planner audita y delimita QUE hay que probar,
apoyandose en la politica del equipo, la Definition of Done, los casos de uso y
los criterios de aceptacion. **No escribe ni una linea de test.** El Generator
viene despues y solo construye sobre el plan aprobado.

Separarlos evita la proliferacion de pruebas desordenadas o redundantes, que es
el fallo que la clase pone de ejemplo: cincuenta tests que recorren la misma
ruta logica cambiando datos irrelevantes.

## De donde saca el contexto

No se le inventa nada: se le dan los hechos del repositorio.

  rutas          `frontend-clinic/src/routes.tsx` — las 10 pantallas reales
  casos de uso   `docs/fsd/FSD_vFinal.md` — FSD-UC-001..007
  reglas         RN-01..RN-09 de `CLAUDE.md`, que son el ORACULO de cada test
  anclas         que `data-testid` existen ya, para no planificar sobre humo

## Tokens

Se reportan entrada y salida exactas del SDK, que es lo que pide la consigna.
Leerlos del panel del IDE seria una estimacion; esto es una medicion.

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
CLINIC_FRONT = RAIZ / 'frontend-clinic' / 'src'

BASE_URL = os.getenv('LOCALHOST_BASE_URL', 'http://localhost:11434/v1')
API_KEY = os.getenv('LOCALHOST_API_KEY', 'local')
MODEL = os.getenv('LOCALHOST_MODEL', 'llama3.2:3b')

#: Los casos de uso del FSD. Son el contrato funcional del producto, no una
#: lista que yo invente para esta tarea.
CASOS_DE_USO = [
    ('FSD-UC-001', 'Ingesta y anonimizacion de imagen'),
    ('FSD-UC-002', 'Segmentacion, clasificacion y semaforizacion'),
    ('FSD-UC-003', 'XAI y correccion manual'),
    ('FSD-UC-004', 'Bloqueo y validacion de Analista'),
    ('FSD-UC-005', 'Auditoria aleatoria del 5 %'),
    ('FSD-UC-006', 'Generacion de reporte ISCN con override manual'),
    ('FSD-UC-007', 'Modo degradado elegante'),
]

#: Las reglas de negocio son el ORACULO. Sin esto el Planner produce «navegar y
#: comprobar que carga», que es exactamente lo que la clase llama ejecucion y
#: no prueba.
REGLAS = """
RN-01 El analista debe validar manualmente los cromosomas naranjas antes de emitir.
RN-02 Confianza < 0,85 pinta naranja y BLOQUEA la emision del informe.
RN-03 Cero fuga de PII: los datos del paciente van cifrados y no salen en la UI.
RN-04 La nomenclatura ISCN es de solo lectura tras generarse; solo cambia por
      override justificado y con permiso case.override_iscn.
RN-05 La bitacora es append-only: no se edita ni se borra un evento.
RN-06 Segregacion de funciones: quien valida como analista no puede firmar como
      supervisor, y un analista no ve casos que no son suyos (403).
RN-07 Degradacion elegante: si la IA cae, la muestra se registra igual y la UI
      entra en modo manual en vez de romperse.
RN-08 Auditoria aleatoria del 5 % de los cromosomas verdes.
"""


def rutas():
    texto = io.open(CLINIC_FRONT / 'routes.tsx', encoding='utf-8').read()
    return re.findall(r'path="([^"]+)"', texto)


def anclas_existentes():
    """Que pantallas tienen ya `data-testid` y cuantos. El Planner necesita
    saberlo: planificar sobre una pantalla sin anclas obliga a anadirlas, y eso
    es parte del entregable."""
    salida = {}
    for carpeta in ('pages', 'components'):
        for ruta in sorted((CLINIC_FRONT / 'clinic' / carpeta).glob('*.tsx')):
            texto = io.open(ruta, encoding='utf-8').read()
            n = len(re.findall(r'data-testid', texto))
            if n:
                salida[ruta.stem] = n
    return salida


PROMPT = """Eres un agente PLANNER de pruebas end-to-end. Tu unica tarea es
DEFINIR QUE HAY QUE PROBAR. No escribes codigo de test: eso lo hace otro agente
despues.

APLICACION: plataforma clinica de cariotipado asistido por IA. El analista
registra una muestra con metafases, la IA segmenta y clasifica los cromosomas,
el analista corrige lo que la IA marco dudoso, y un supervisor firma el informe.

PANTALLAS REALES (rutas de la aplicacion):
%(rutas)s

CASOS DE USO DEL DOCUMENTO FUNCIONAL:
%(casos)s

REGLAS DE NEGOCIO — son el ORACULO de cada test. Un test sin una de estas
detras no prueba nada:
%(reglas)s

TAREA:
Para cada flujo de la aplicacion, define los casos de prueba E2E. Por cada caso
indica:
  - id: un identificador corto, por ejemplo E2E-01
  - flujo: que flujo de negocio cubre
  - ruta: la pantalla donde empieza
  - tipo: "happy" | "error" | "limite"
  - oraculo: la regla de negocio concreta contra la que se compara el resultado
  - criterio: que tiene que ser verdad al final para que el test pase

REGLAS PARA TI:
- Cubre las tres capas: camino feliz, casos de error y valores limite.
- NO propongas varios casos que recorran la misma ruta logica cambiando solo
  datos irrelevantes. Un caso por comportamiento distinto.
- Todo caso debe tener un oraculo de la lista de reglas. Si un flujo no tiene
  regla de negocio detras, dilo en vez de inventarla.
- Maximo 12 casos en total.

Devuelve SOLO un JSON con esta forma, sin explicaciones:
{"casos": [{"id": "...", "flujo": "...", "ruta": "...", "tipo": "...",
            "oraculo": "...", "criterio": "..."}]}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--salida', default=str(RAIZ / 'docs' / 'M8_E2E' / 'plan.json'))
    opts = ap.parse_args()

    from openai import OpenAI

    lista_rutas = rutas()
    contexto = {
        'rutas': '\n'.join('  %s' % r for r in lista_rutas),
        'casos': '\n'.join('  %s %s' % (c, d) for c, d in CASOS_DE_USO),
        'reglas': REGLAS.strip(),
    }
    prompt = PROMPT % contexto

    print('PLANNER -> modelo=%s via %s' % (MODEL, BASE_URL))
    print('contexto: %d rutas, %d casos de uso, %d reglas'
          % (len(lista_rutas), len(CASOS_DE_USO),
             len([l for l in REGLAS.strip().split('\n') if l.startswith('RN')])))
    anclas = anclas_existentes()
    print('anclas ya existentes: %d ficheros, %d data-testid'
          % (len(anclas), sum(anclas.values())))
    print()

    t0 = time.time()
    cliente = OpenAI(base_url=BASE_URL, api_key=API_KEY, timeout=900.0)
    r = cliente.chat.completions.create(
        model=MODEL, temperature=0,
        messages=[
            {'role': 'system', 'content': 'Devuelve SOLO JSON valido, sin texto alrededor.'},
            {'role': 'user', 'content': prompt},
        ])
    segundos = round(time.time() - t0, 1)
    contenido = r.choices[0].message.content or ''

    destino = Path(opts.salida)
    destino.parent.mkdir(parents=True, exist_ok=True)

    # La respuesta cruda se guarda ANTES de intentar parsearla: es la evidencia
    # de lo que produjo el Planner, y la auditoria se hace sobre ella.
    crudo = destino.with_name(destino.stem + '_crudo.txt')
    io.open(crudo, 'w', encoding='utf-8', newline='\n').write(contenido)

    bloque = re.search(r'\{.*\}', contenido, re.S)
    casos = []
    if bloque:
        try:
            casos = json.loads(bloque.group(0)).get('casos', [])
        except json.JSONDecodeError as exc:
            print('AVISO: el Planner no devolvio JSON valido (%s)' % exc)

    io.open(destino, 'w', encoding='utf-8', newline='\n').write(
        json.dumps({'modelo': MODEL, 'casos': casos}, indent=1, ensure_ascii=False) + '\n')

    u = r.usage
    print('casos propuestos : %d' % len(casos))
    for c in casos:
        print('  %-8s %-8s %-34s %s'
              % (c.get('id', '?'), c.get('tipo', '?'),
                 (c.get('flujo') or '')[:34], (c.get('oraculo') or '')[:28]))
    print()
    print('TOKENS PLANNER: entrada=%s salida=%s  tiempo=%ss'
          % (u.prompt_tokens if u else '?', u.completion_tokens if u else '?', segundos))
    print('plan  : %s' % destino.relative_to(RAIZ))
    print('crudo : %s' % crudo.relative_to(RAIZ))
    return 0


if __name__ == '__main__':
    sys.exit(main())
