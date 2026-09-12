# -*- coding: utf-8 -*-
"""agente_generador.py — el agente del LabX, apuntado al producto real.

Misma anatomia que el del laboratorio y sin nada mas adentro: lee los archivos
de contexto, arma el prompt, llama al modelo por el SDK, escribe el fichero de
tests y REPORTA LOS TOKENS.

    python docs/M7_UNIT_AGENTE/agente_generador.py iscn
    python docs/M7_UNIT_AGENTE/agente_generador.py endpoint

Las dos diferencias con el del laboratorio, y las dos son a proposito:

1. El contexto son ficheros del producto (`iscn.py`, `contratos.py`), no de un
   ejercicio de juguete. El modelo es el mismo llama3.2:3b del M6.
2. **No se corrige nada de lo que devuelve.** El generador del LabX anade
   `import pytest` cuando el modelo lo olvida; aqui no, porque ese olvido es
   justamente lo que la auditoria tiene que encontrar. Lo que el modelo escriba
   se guarda tal cual en `salida_agente/` antes de tocarlo.
"""
import io
import os
import re
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
CLINIC = RAIZ / 'backend-clinic'
AQUI = Path(__file__).resolve().parent

BASE_URL = os.getenv('LOCALHOST_BASE_URL', 'http://localhost:11434/v1')
API_KEY = os.getenv('LOCALHOST_API_KEY', 'local')
MODEL = os.getenv('LOCALHOST_MODEL', 'llama3.2:3b')

EJERCICIOS = {
    'iscn': {
        'prompt': 'PROMPT_AGENTE_iscn.md',
        'contexto': ['apps/samples/iscn.py', 'apps/samples/tests/test_iscn.py'],
        'salida': 'apps/samples/tests/test_iscn_agente.py',
    },
    'endpoint': {
        'prompt': 'PROMPT_AGENTE_endpoint.md',
        'contexto': ['apps/samples/contratos.py',
                     'apps/samples/tests/test_contrato_karyotype.py'],
        'salida': 'apps/samples/tests/test_karyotype_endpoint_agente.py',
    },
}


def leer_prompt(nombre):
    """El bloque entre ``` ``` del PROMPT_AGENTE, igual que en el LabX."""
    texto = io.open(AQUI / nombre, encoding='utf-8').read()
    bloque = re.search(r'```\n(.*?)```', texto, re.S)
    return bloque.group(1).strip() if bloque else texto


def extraer_codigo(respuesta):
    """Saca el bloque de codigo y NO lo arregla. Ver el docstring del modulo."""
    bloque = re.search(r'```(?:python)?\n(.*?)```', respuesta, re.S)
    return (bloque.group(1) if bloque else respuesta).strip() + '\n'


def main(clave):
    from openai import OpenAI

    ej = EJERCICIOS[clave]
    contexto = '\n\n'.join(
        '### %s\n```python\n%s\n```' % (ruta, io.open(CLINIC / ruta, encoding='utf-8').read())
        for ruta in ej['contexto'])
    mensajes = [
        {'role': 'system', 'content': (
            'Eres un asistente que escribe tests unitarios con pytest. Devuelve SOLO '
            'un bloque de codigo Python completo, sin explicaciones.')},
        {'role': 'user', 'content': 'ARCHIVOS DEL PROYECTO:\n\n%s\n\nTAREA:\n%s'
                                    % (contexto, leer_prompt(ej['prompt']))},
    ]
    print('agente -> modelo=%s via %s' % (MODEL, BASE_URL))
    print('contexto: %s  (~%s tokens estimados)'
          % (', '.join(ej['contexto']),
             format(sum(len(m['content']) for m in mensajes) // 4, ',d')))

    t0 = time.time()
    cliente = OpenAI(base_url=BASE_URL, api_key=API_KEY, timeout=600.0)
    r = cliente.chat.completions.create(model=MODEL, temperature=0, messages=mensajes)
    segundos = round(time.time() - t0, 1)

    codigo = extraer_codigo(r.choices[0].message.content)

    # Copia intacta de lo que devolvio el modelo: es la evidencia de la
    # auditoria. Si despues se corrige un test, se corrige el del repositorio,
    # nunca esta.
    crudo = AQUI / 'salida_agente' / ('%s_crudo.py' % clave)
    crudo.parent.mkdir(exist_ok=True)
    io.open(crudo, 'w', encoding='utf-8', newline='\n').write(codigo)

    destino = CLINIC / ej['salida']
    io.open(destino, 'w', encoding='utf-8', newline='\n').write(codigo)

    u = r.usage
    print('escrito: %s' % ej['salida'])
    print('crudo:   %s' % crudo.relative_to(RAIZ))
    print('tokens: entrada=%s salida=%s  tiempo=%ss'
          % (u.prompt_tokens if u else '?', u.completion_tokens if u else '?', segundos))
    print('ahora: pytest %s -q --no-cov   y despues, la auditoria' % ej['salida'])


if __name__ == '__main__':
    if len(sys.argv) != 2 or sys.argv[1] not in EJERCICIOS:
        sys.exit('uso: python agente_generador.py [%s]' % ' | '.join(EJERCICIOS))
    main(sys.argv[1])
