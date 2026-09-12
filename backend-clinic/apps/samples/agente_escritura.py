"""La única acción de ESCRITURA del agente, con su guardrail dentro.

## El guardrail vive EN la herramienta, no en el agente

Podría comprobarse en el bucle, pero entonces solo protegería a *nuestro*
agente. Puesto aquí, viaja con la herramienta: cuando se publica por MCP, el
guardrail va con ella a cualquier cliente que la descubra —otro agente, un IDE,
Claude Desktop— sin que ese cliente tenga que saber nada.

## Qué política implementa

AGENTS.md, RN-01, literal:

    Ningún informe puede emitirse sin:
      (a) validación manual del analista de TODOS los cromosomas naranjas
      (b) firma digital del supervisor (MFA obligatorio)

Y RN-06 añade que Supervisor y Analista no pueden ser el mismo usuario.

Un proceso automático no cumple ninguna de las dos: no es un analista
identificado ni puede aportar un segundo factor. Por eso esta herramienta
**nunca ejecuta**, ni siquiera con `confirmado=true`.

Eso es más estricto que el ejemplo de clase, donde `confirmado=true` sí cancela
el pedido. La diferencia no es de implementación sino de dominio: cancelar una
compra es reversible y lo autoriza su dueño; validar un cariotipo es un acto
clínico que firma un profesional con su identidad. El guardrail implementa la
política, y la política aquí es más dura.

Lo que el agente SÍ puede hacer es preparar el trabajo: decir qué caso es, qué
bloquea la validación y qué pasaría — para que la persona decida con la
información delante en vez de ir a buscarla.
"""
from __future__ import annotations

from .models import CONFIDENCE_THRESHOLD, Chromosome, Sample, SampleStatus

NOMBRE = 'preparar_validacion_de_caso'

SCHEMA = {
    'type': 'function',
    'function': {
        'name': NOMBRE,
        'description': (
            'Prepara la validación de un caso: informa de qué bloquea la '
            'validación y qué ocurriría al validarlo. ESCRITURA: llamar '
            'siempre con confirmado=false para obtener el plan. La ejecución '
            'real la hace una persona identificada desde la aplicación — un '
            'agente no puede validar un cariotipo.'
        ),
        'parameters': {
            'type': 'object',
            'properties': {
                'chn_code': {
                    'type': 'string',
                    'description': 'Código CHN del caso, p. ej. CHN-2026-08-06-0001.',
                },
                'confirmado': {
                    'type': 'boolean',
                    'description': ('false para ver el plan. true está reservado '
                                    'a un humano identificado y el agente no debe '
                                    'usarlo.'),
                },
            },
            'required': ['chn_code'],
        },
    },
}


def preparar_validacion(chn_code: str, confirmado: bool = False) -> dict:
    """Devuelve el plan de validación. Nunca valida.

    El guardrail se comprueba ANTES de mirar los datos: si alguien llama con
    `confirmado=true`, lo que recibe es la negativa y el motivo, no la ejecución.
    """
    if confirmado:
        # No es un error del llamador: es la política respondiendo.
        return {
            'ejecutado': False,
            'motivo': 'RN-01',
            'detalle': (
                'Un agente no puede validar un caso. RN-01 exige validación '
                'manual del analista de todos los cromosomas naranjas y firma '
                'del supervisor con MFA; RN-06 exige además que no sean la '
                'misma persona. Un proceso automático no es un analista '
                'identificado ni puede aportar un segundo factor.'
            ),
            'que_hacer': ('Abrir el caso en la aplicación y validarlo desde la '
                          'sesión del analista.'),
        }

    caso = Sample.objects.filter(chn_code=chn_code, is_active=True).first()
    if caso is None:
        return {'ejecutado': False, 'error': f'no existe el caso {chn_code}'}

    naranjas = Chromosome.objects.filter(
        karyotype__sample=caso,
        is_active=True,
        resolution_status='PENDING',
        confidence_score__lt=CONFIDENCE_THRESHOLD,
    ).count()

    bloqueos = []
    if caso.status != SampleStatus.READY:
        bloqueos.append(f'el caso está en {caso.status}, no en READY')
    if naranjas:
        bloqueos.append(f'{naranjas} cromosoma(s) naranja sin resolver (RN-02)')

    return {
        'ejecutado': False,
        'plan': True,
        'caso': caso.chn_code,
        'estado_actual': caso.status,
        'naranjas_sin_resolver': naranjas,
        'bloqueos': bloqueos or ['ninguno: el caso puede validarse'],
        'efecto_si_se_valida': (
            'el caso pasaría a ANALYST_VALIDATED y quedaría a la espera de la '
            'firma del supervisor'),
        'quien_puede_hacerlo': (
            'un analista identificado, desde la aplicación. No el agente: RN-01.'),
    }


def ejecutar(argumentos: dict) -> dict:
    return preparar_validacion(
        chn_code=(argumentos or {}).get('chn_code') or '',
        confirmado=bool((argumentos or {}).get('confirmado')),
    )
