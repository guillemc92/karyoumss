"""Evalua el enrutamiento contra un banco de preguntas etiquetadas.

    python manage.py eval_enrutado

No es un test de pytest: necesita Ollama corriendo y tarda ~9 minutos, porque
cada pregunta que no resuelve el vocabulario cuesta una llamada al modelo. Es un
banco de evaluacion, se corre a mano cuando se toca el prompt o el catalogo.

Las preguntas estan escritas como las diria un analista o un supervisor, NO como
las escribiria quien ya conoce el catalogo. Esa es la unica forma de que el
numero signifique algo: medir con el vocabulario propio seria hacer trampa.

El reparto dentro/fuera de alcance importa mas que el total. Fallar dentro de
alcance manda al usuario a "no se"; fallar FUERA de alcance le entrega datos
reales que no responden su pregunta, que es mucho peor.

Salida en ASCII puro: la consola de Windows (cp1252) rompe con Unicode.
"""
from django.core.management.base import BaseCommand

from apps.samples.tool_router import responder

FUERA = 'NINGUNA'

BANCO = [
    # --- CROMOSOMAS_PARA_REVISION -------------------------------------------
    ('Que cromosomas estan naranjas?', 'CROMOSOMAS_PARA_REVISION'),
    ('Cuales tienen baja confianza?', 'CROMOSOMAS_PARA_REVISION'),
    ('Cuales necesitan que el analista los mire de nuevo?', 'CROMOSOMAS_PARA_REVISION'),
    ('Que cromosomas dudosos me faltan por revisar?', 'CROMOSOMAS_PARA_REVISION'),
    ('Donde no confio en lo que dijo la IA?', 'CROMOSOMAS_PARA_REVISION'),
    ('Que quedo marcado para verificacion manual?', 'CROMOSOMAS_PARA_REVISION'),
    ('Hay cromosomas mal clasificados pendientes?', 'CROMOSOMAS_PARA_REVISION'),

    # --- CASOS_PENDIENTES_FIRMA ---------------------------------------------
    ('Que casos estan pendientes de firma?', 'CASOS_PENDIENTES_FIRMA'),
    ('Que me toca firmar hoy?', 'CASOS_PENDIENTES_FIRMA'),
    ('Cuales espera el supervisor?', 'CASOS_PENDIENTES_FIRMA'),
    ('Que informes ya valido el analista pero siguen abiertos?', 'CASOS_PENDIENTES_FIRMA'),
    ('Tengo algo esperando mi autorizacion?', 'CASOS_PENDIENTES_FIRMA'),
    # Ambigua a proposito: "ultima revision" puede leerse como la firma del
    # supervisor (etiqueta elegida) o como el ultimo repaso del analista. Se
    # deja en el banco porque los usuarios preguntan asi; quitarla porque el
    # sistema la falla seria maquillar el numero.
    ('Que esta listo para la ultima revision?', 'CASOS_PENDIENTES_FIRMA'),

    # --- CASOS_REPORTADOS ----------------------------------------------------
    ('Que casos estan reportados?', 'CASOS_REPORTADOS'),
    ('Cuales ya se entregaron al medico?', 'CASOS_REPORTADOS'),
    ('Que estudios ya tienen resultado final?', 'CASOS_REPORTADOS'),
    ('Muestrame los casos cerrados de esta semana', 'CASOS_REPORTADOS'),
    ('Que ya tiene nomenclatura emitida?', 'CASOS_REPORTADOS'),
    ('Cuales terminaron el proceso completo?', 'CASOS_REPORTADOS'),

    # --- CASOS_EN_PROCESO ----------------------------------------------------
    ('Que muestras estan en proceso?', 'CASOS_EN_PROCESO'),
    ('Que esta corriendo ahora en la maquina?', 'CASOS_EN_PROCESO'),
    ('Cuales todavia no terminan el analisis?', 'CASOS_EN_PROCESO'),
    ('Que hay en la cola de procesamiento?', 'CASOS_EN_PROCESO'),
    ('En que esta trabajando el sistema?', 'CASOS_EN_PROCESO'),

    # --- Fuera de alcance ----------------------------------------------------
    # Son las que de verdad ponen a prueba el enrutador: todas hablan del
    # laboratorio, asi que invitan al modelo a elegir por parecido tematico.
    ('Cual es el presupuesto del laboratorio para 2027?', FUERA),
    ('Cuantos pacientes atendimos el ano pasado?', FUERA),
    ('Quien es el jefe del servicio de genetica?', FUERA),
    ('Cuanto cuesta un cariotipo?', FUERA),
    ('Que dice el manual sobre el bandeo G?', FUERA),
    ('Cuando vence el reactivo de tripsina?', FUERA),
]


class Command(BaseCommand):
    help = 'Mide el acierto del enrutador sobre un banco de preguntas etiquetadas.'

    def handle(self, *args, **options):
        aciertos = {'dentro': 0, 'fuera': 0}
        totales = {'dentro': 0, 'fuera': 0}
        fallos = []

        for i, (pregunta, esperado) in enumerate(BANCO, 1):
            grupo = 'fuera' if esperado == FUERA else 'dentro'
            totales[grupo] += 1

            r = responder(pregunta)
            obtenido = r.tool or FUERA
            bien = obtenido == esperado
            aciertos[grupo] += bien
            if not bien:
                fallos.append((pregunta, esperado, obtenido, r.camino))

            marca = 'OK ' if bien else 'MAL'
            self.stdout.write(
                f'{i:>2}/{len(BANCO)} {marca} [{r.camino:<9}] '
                f'{pregunta[:50]:<50} -> {obtenido}'
            )

        total_ok = sum(aciertos.values())
        self.stdout.write('')
        self.stdout.write('=' * 66)
        self.stdout.write(f'GLOBAL          {total_ok}/{len(BANCO)}  '
                          f'({100 * total_ok / len(BANCO):.0f}%)')
        for grupo, etiqueta in (('dentro', 'Dentro de alcance'), ('fuera', 'Fuera de alcance ')):
            n, t = aciertos[grupo], totales[grupo]
            self.stdout.write(f'  {etiqueta}  {n}/{t}  ({100 * n / t:.0f}%)')
        self.stdout.write('=' * 66)

        if fallos:
            self.stdout.write('')
            self.stdout.write(f'Fallos ({len(fallos)}):')
            for pregunta, esperado, obtenido, camino in fallos:
                self.stdout.write(f'  [{camino}] {pregunta}')
                self.stdout.write(f'      esperado {esperado}  |  obtenido {obtenido}')
