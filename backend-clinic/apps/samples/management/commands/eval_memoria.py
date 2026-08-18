"""Mide si la memoria del nivel 5 sirve de algo — nivel 4 contra nivel 5.

    python manage.py eval_memoria

## Qué se mide, y por qué así

«Implementé LangGraph» no es un resultado. El resultado es: **¿resuelve
repreguntas que el nivel 4 no puede resolver?**

El banco son **pares**: una pregunta que sí tiene sentido sola, y una repregunta
que **no lo tiene** —«¿y el segundo?», «¿cuántos eran?»—. Están escritas a
propósito para que ninguna herramienta pueda contestarlas: no dicen el segundo
*de qué*. El referente solo existe en el turno anterior.

    nivel 4   cada pregunta es independiente: el referente se perdió
    nivel 5   mismo thread_id: el checkpoint conserva el turno anterior

## Cómo se decide si acertó, sin que la vara la ponga el modelo

El testigo se saca **en tiempo de ejecución** del turno 1: un dato concreto que
salió de la observación de la herramienta (un par de cromosoma, un código CHN).
Se comprueba si aparece en la respuesta a la repregunta. Fijar el testigo a mano
mediría lo que uno espera; sacarlo de la ejecución mide lo que hubo.

**Limitación declarada:** el nivel 4 podría acertar por casualidad si vuelve a
llamar a la herramienta y el testigo reaparece. No se corrige — se deja porque
juega EN CONTRA de la conclusión, y una conclusión que aguanta con el listón en
contra vale más que una ajustada a favor.

**Y hay dos clases de repregunta, que no valen igual.** Las que apuntan a la
conversación —«repite el último que *dijiste*»— solo se pueden contestar con
memoria: el referente no está en la base. Las que apuntan al dato —«dame el
código del primero»— el nivel 4 puede resolverlas volviendo a consultar, así
que ahí un acierto suyo no es casualidad, es una vía legítima distinta. Al leer
el resultado hay que mirar par por par, no solo el total.

**Corregido tras la primera corrida:** el testigo se extraía con `\\d{1,2}` y
producía «0», «1», «08». El par 3 dio OK en AMBOS niveles porque sus respuestas
contenían un cero, pese a que las dos hablaban de algo distinto de lo
preguntado. Un banco que se deja engañar así infla los dos lados y no mide
nada. Ver `LARGO_MINIMO`.

Tarda: son 4 llamadas al modelo por par, y `llama3.2:3b` en CPU va a ~100 s.
"""
import re
import time
import uuid

from django.core.management.base import BaseCommand

# (pregunta que abre contexto, repregunta SIN sentido por sí sola)
#
# Los pares 1 y 4 apuntan a la CONVERSACIÓN («mencionaste», «dijiste»): sin
# memoria no hay forma de contestarlos. Los pares 2 y 3 apuntan al DATO, y el
# nivel 4 puede resolverlos volviendo a consultar la herramienta — ahí un
# acierto suyo es legítimo, no ruido.
BANCO = [
    ('Que cromosomas hay pendientes de revisar?',
     'De esos, cual mencionaste primero?'),               # conversación
    ('Que casos estan pendientes de firma?',
     'Y cuantos eran en total?'),                          # dato
    ('Que casos estan en proceso ahora mismo?',
     'Dame el codigo del primero.'),                       # dato
    ('Que cromosomas hay pendientes de revisar?',
     'Repite solo el ultimo que dijiste.'),                # conversación
]

# Un testigo útil es un dato concreto que solo pudo salir de la observación.
TESTIGO = re.compile(r'\b(?:CHN-[\w-]+|ANON-[\w-]+|par \d{1,2})\b', re.I)

# Longitud mínima para que un testigo signifique algo. La primera versión
# aceptaba `\d{1,2}` y producía testigos como «0», «1» u «08»: cualquier
# respuesta que contuviera un cero —y un código CHN tiene varios— pasaba por
# acierto. Medido: con esos testigos el par 3 dio OK en AMBOS niveles pese a que
# los dos respondieron sobre algo distinto de lo que se preguntaba.
LARGO_MINIMO = 6


def testigos_de(traza) -> list[str]:
    """Datos concretos que aparecieron en las OBSERVACIONES del turno 1."""
    vistos = []
    for paso in traza.pasos:
        if paso['tipo'] != 'observacion':
            continue
        for t in TESTIGO.findall(paso['detalle']):
            if len(t) >= LARGO_MINIMO and t not in vistos:
                vistos.append(t)
    return vistos


class Command(BaseCommand):
    help = 'Compara nivel 4 (sin memoria) contra nivel 5 (con checkpoint).'

    def add_arguments(self, parser):
        parser.add_argument('--pares', type=int, default=len(BANCO))

    def handle(self, *args, **opts):
        from apps.samples.agente import AgenteError, ejecutar_agente
        from apps.samples.agente_acciones import INSTRUCCIONES, ejecutar, schemas
        from apps.samples.agente_grafo import conversar, olvidar

        pares = BANCO[:opts['pares']]
        aciertos = {'nivel4': 0, 'nivel5': 0}
        caidos = 0
        medidos = 0
        inicio = time.time()

        self.stdout.write(f'pares: {len(pares)}  |  4 llamadas al modelo por par\n')
        self.stdout.write('=' * 74)

        for i, (abre, repregunta) in enumerate(pares, 1):
            self.stdout.write(f'\n[{i}] {abre}')
            self.stdout.write(f'    -> {repregunta}')

            # --- nivel 5: mismo hilo, el checkpoint conserva el turno 1 -------
            hilo = f'eval-{uuid.uuid4().hex[:8]}'
            try:
                t1 = conversar(abre, hilo)
                t2 = conversar(repregunta, hilo)
            except AgenteError as exc:
                # Un timeout del modelo NO puede borrar la medición: se anota el
                # par como caído y se sigue. Perder tres pares buenos porque el
                # cuarto tardó de más sería el instrumento arruinando el
                # experimento.
                self.stdout.write(f'    CAIDO (nivel 5): {exc}')
                caidos += 1
                olvidar(hilo)
                continue

            esperados = testigos_de(t1.traza)
            if not esperados:
                self.stdout.write('    (sin testigo en la observacion: par descartado)')
                olvidar(hilo)
                continue

            olvidar(hilo)

            # --- nivel 4: la repregunta llega huerfana ------------------------
            try:
                r4 = ejecutar_agente(repregunta, schemas(), ejecutar, INSTRUCCIONES)
            except AgenteError as exc:
                self.stdout.write(f'    CAIDO (nivel 4): {exc}')
                caidos += 1
                continue

            # El par solo cuenta si AMBOS niveles respondieron: comparar uno que
            # corrió contra otro que se cayó no compara nada.
            medidos += 1
            n5 = any(t.lower() in t2.respuesta.lower() for t in esperados)
            n4 = any(t.lower() in r4.respuesta.lower() for t in esperados)
            aciertos['nivel5'] += n5
            aciertos['nivel4'] += n4

            self.stdout.write(f'    testigos del turno 1: {esperados[:4]}')
            self.stdout.write(f'    nivel 4 (sin memoria): {"OK " if n4 else "MAL"}  '
                              f'{r4.respuesta[:70]!r}')
            self.stdout.write(f'    nivel 5 (con memoria): {"OK " if n5 else "MAL"}  '
                              f'{t2.respuesta[:70]!r}')

        self.stdout.write('\n' + '=' * 74)
        self.stdout.write(f'Pares medidos           {medidos}/{len(pares)}'
                          + (f'   ({caidos} caidos por timeout)' if caidos else ''))
        if medidos:
            self.stdout.write(f'Nivel 4 - sin memoria   {aciertos["nivel4"]}/{medidos}')
            self.stdout.write(f'Nivel 5 - con memoria   {aciertos["nivel5"]}/{medidos}')
        self.stdout.write('=' * 74)
        if aciertos['nivel5'] <= aciertos['nivel4']:
            self.stdout.write(
                'La memoria NO mejoro el resultado. Es un dato, no un fallo del '
                'experimento: hay que decirlo tal cual.')
        self.stdout.write(f'({time.time() - inicio:.0f}s)')
