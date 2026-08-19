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

# (apertura, repregunta SIN sentido por sí sola, grupo)
#
# CONVERSACION: la repregunta apunta a lo que el agente DIJO —«mencionaste»,
# «dijiste», «tu respuesta anterior»—. El referente no está en la base: sin
# memoria no hay forma de contestarla. Son las que miden el nivel 5.
#
# DATO: la repregunta apunta al dato. El nivel 4 puede resolverla volviendo a
# consultar la herramienta, así que un acierto suyo NO es ruido: es una vía
# legítima distinta. Se conservan **a propósito, como grupo de control** — para
# mostrar dónde el nivel 4 compite de verdad. Quitarlas dejaría un banco que
# solo puede dar la razón al nivel 5.
#
# Las aperturas están verificadas: las tres herramientas devuelven filas con
# códigos CHN. `CASOS_EN_PROCESO` se excluyó porque devuelve 0 filas y sus
# pares se descartaban por falta de testigo.
CONVERSACION, DATO = 'conversacion', 'dato'

BANCO = [
    ('Que cromosomas hay pendientes de revisar?',
     'De esos, cual mencionaste primero?', CONVERSACION),
    ('Que cromosomas hay pendientes de revisar?',
     'Repite solo el ultimo que dijiste.', CONVERSACION),
    ('Que cromosomas hay pendientes de revisar?',
     'De tu respuesta anterior, dame solo el primer codigo.', CONVERSACION),
    ('Que casos estan pendientes de firma?',
     'Cual nombraste en primer lugar?', CONVERSACION),
    ('Que casos estan pendientes de firma?',
     'Repite el primer caso que citaste, sin anadir nada mas.', CONVERSACION),
    ('Que casos estan pendientes de firma?',
     'Del listado que acabas de darme, dime el primero.', CONVERSACION),
    ('Que casos ya fueron reportados?',
     'Cual mencionaste al principio?', CONVERSACION),
    ('Que casos ya fueron reportados?',
     'Vuelve a decirme el primero que dijiste.', CONVERSACION),

    # --- control: resolubles volviendo a consultar --------------------------
    ('Que casos estan pendientes de firma?',
     'Dame el codigo del primero.', DATO),
    ('Que casos ya fueron reportados?',
     'Y cuantos eran en total?', DATO),
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
        # Desglosado por grupo: el total mezcla lo que mide el nivel 5 con lo
        # que el nivel 4 puede resolver por otra vía, y leerlo junto engaña.
        aciertos = {CONVERSACION: {'n4': 0, 'n5': 0}, DATO: {'n4': 0, 'n5': 0}}
        medidos = {CONVERSACION: 0, DATO: 0}
        caidos = 0
        inicio = time.time()

        self.stdout.write(f'pares: {len(pares)}  |  4 llamadas al modelo por par\n')
        self.stdout.write('=' * 74)

        for i, (abre, repregunta, grupo) in enumerate(pares, 1):
            self.stdout.write(f'\n[{i}] ({grupo}) {abre}')
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
            medidos[grupo] += 1
            n5 = any(t.lower() in t2.respuesta.lower() for t in esperados)
            n4 = any(t.lower() in r4.respuesta.lower() for t in esperados)
            aciertos[grupo]['n5'] += n5
            aciertos[grupo]['n4'] += n4

            self.stdout.write(f'    testigos del turno 1: {esperados[:4]}')
            self.stdout.write(f'    nivel 4 (sin memoria): {"OK " if n4 else "MAL"}  '
                              f'{r4.respuesta[:70]!r}')
            self.stdout.write(f'    nivel 5 (con memoria): {"OK " if n5 else "MAL"}  '
                              f'{t2.respuesta[:70]!r}')

        total = sum(medidos.values())
        self.stdout.write('\n' + '=' * 74)
        self.stdout.write(f'Pares medidos           {total}/{len(pares)}'
                          + (f'   ({caidos} caidos por timeout)' if caidos else ''))
        self.stdout.write('-' * 74)
        for grupo, etiqueta in ((CONVERSACION, 'CONVERSACION (exigen memoria)'),
                                (DATO, 'DATO (control: reconsultables) ')):
            n = medidos[grupo]
            if not n:
                self.stdout.write(f'{etiqueta}  sin pares medidos')
                continue
            a = aciertos[grupo]
            self.stdout.write(f'{etiqueta}   nivel 4: {a["n4"]}/{n}   '
                              f'nivel 5: {a["n5"]}/{n}')
        self.stdout.write('=' * 74)

        # El veredicto se lee SOLO sobre el grupo que aísla la memoria.
        conv, n = aciertos[CONVERSACION], medidos[CONVERSACION]
        if n and conv['n5'] <= conv['n4']:
            self.stdout.write(
                'La memoria NO mejoro el resultado en el grupo que la aisla. Es un '
                'dato, no un fallo del experimento: hay que decirlo tal cual.')
        if n and n < 6:
            self.stdout.write(
                f'AVISO: solo {n} pares de conversacion medidos. Con esa n no se '
                'sostiene ninguna afirmacion fuerte.')
        self.stdout.write(f'({time.time() - inicio:.0f}s)')
