"""Mide el RAG contra un banco de preguntas con fuente esperada.

    python manage.py eval_rag
    python manage.py eval_rag --umbral 0.6

Que el RAG "devuelva algo" no prueba nada: siempre devuelve el fragmento menos
malo. Lo que hay que medir es si devuelve el fragmento CORRECTO, y si se calla
cuando el corpus no cubre la pregunta.

Por eso el banco tiene dos mitades:

  CUBIERTAS  la respuesta esta en el corpus. Se declara que documento deberia
             salir, y se comprueba que aparezca en el top-k.
  FUERA      el corpus no las cubre. El acierto es NO responder: cualquier
             fragmento por encima del umbral es un falso positivo, y en clinica
             un falso positivo con cita de fuente es peor que un "no se",
             porque parece fundamentado.

Las seis primeras salen del banco de `eval_enrutado`: son exactamente las que
hoy caen en SIN_MATCH porque ninguna herramienta las cubre.

Salida en ASCII (consola Windows cp1252).
"""
from django.core.management.base import BaseCommand

from apps.samples.rag_index import RagError, UMBRAL_MINIMO, indice

FUERA = None

# (pregunta, patron que debe aparecer en la fuente del fragmento recuperado)
#
# OJO con las etiquetas: exigen una FUENTE, no comprueban que la respuesta sea
# correcta. Al revisar los fallos aparecieron dos casos donde el sistema
# acertaba y la etiqueta estaba mal (ver comentarios). Se corrigieron POR
# MERITO -verificando que ese documento contiene de verdad la respuesta-, no
# para subir el numero. Los demas fallos se dejan como estan.
BANCO = [
    # --- cubiertas por el corpus -------------------------------------------
    ('Que significa que un cromosoma este naranja?', 'AGENTS|ADR|FSD'),
    ('Por que el sistema marca cromosomas en naranja?', 'AGENTS|ADR|FSD'),
    # El BRD SI define el umbral ("85% de confianza (Softmax)", criterio
    # clinico-operativo). Excluirlo era un error de la etiqueta.
    ('Que umbral de confianza se usa para la semaforizacion?', 'AGENTS|ADR|FSD|BRD'),
    ('Quien tiene permiso para firmar un caso?', 'ADR|AGENTS|FSD'),
    ('Como se escribe la nomenclatura ISCN de una trisomia 21?', 'ISCN|ADR'),
    # ADR-0025 es el motor ISCN y explica la nomenclatura: es fuente legitima.
    ('Que significa 46,XY en nomenclatura ISCN?', 'ISCN|ADR'),
    ('Como se ordenan las anomalias en un cariotipo ISCN?', 'ISCN|ADR'),
    ('Que es una metafase?', 'ISCN|ADR|FSD|BRD'),
    ('Por que el analista debe validar antes de emitir el informe?', 'AGENTS|ADR|FSD'),
    ('Que arquitectura se eligio para el pipeline de IA?', 'ADR'),
    ('Como se protegen los datos personales del paciente?', 'ADR|AGENTS'),
    ('Que pasa si el servicio de IA no esta disponible?', 'ADR|AGENTS|FSD'),

    # --- fuera del corpus: el acierto es abstenerse -------------------------
    ('Cual es el presupuesto del laboratorio para 2027?', FUERA),
    ('Cuando vence el reactivo de tripsina?', FUERA),
    ('Quien es el jefe del servicio de genetica?', FUERA),
    ('Cual es el telefono del doctor Rojas?', FUERA),
    ('Cuantos empleados tiene el hospital?', FUERA),
    ('Que marca de microscopio conviene comprar?', FUERA),
]


class Command(BaseCommand):
    help = 'Mide precision del RAG y su capacidad de abstenerse.'

    def add_arguments(self, parser):
        parser.add_argument('--umbral', type=float, default=UMBRAL_MINIMO)
        parser.add_argument('-k', type=int, default=4)
        parser.add_argument('--ver', action='store_true',
                            help='muestra el fragmento recuperado')
        parser.add_argument('--con-juez', action='store_true',
                            help='evalua la cadena completa (indice + modelo juez), '
                                 'no solo la recuperacion. Tarda ~30s por pregunta.')

    def handle(self, *args, **opts):
        if opts['con_juez']:
            return self._con_juez()
        try:
            idx = indice()
        except RagError as exc:
            self.stderr.write(str(exc))
            return

        umbral, k = opts['umbral'], opts['k']
        self.stdout.write(f'indice: {len(idx)} fragmentos | modelo: {idx.modelo} | '
                          f'umbral: {umbral} | k: {k}')
        self.stdout.write('=' * 74)

        ok = {'cubierta': 0, 'fuera': 0}
        total = {'cubierta': 0, 'fuera': 0}
        fallos = []

        for pregunta, esperado in BANCO:
            grupo = 'fuera' if esperado is FUERA else 'cubierta'
            total[grupo] += 1
            res = idx.buscar(pregunta, k=k, umbral=umbral)

            if esperado is FUERA:
                bien = not res
                detalle = 'se abstuvo' if bien else f'RESPONDIO {res[0].como_cita()}'
            else:
                import re
                bien = any(re.search(esperado, r.fragmento.fuente) for r in res)
                if res:
                    detalle = f'{res[0].como_cita()}'
                else:
                    detalle = 'no recupero nada'

            ok[grupo] += bien
            if not bien:
                fallos.append((pregunta, esperado, detalle))

            marca = 'OK ' if bien else 'MAL'
            self.stdout.write(f'{marca} [{grupo:8}] {pregunta[:46]:<46} {detalle[:60]}')
            if opts['ver'] and res:
                self.stdout.write(f'         > {res[0].fragmento.texto[:150]}...')

        n = sum(ok.values())
        t = sum(total.values())
        self.stdout.write('=' * 74)
        self.stdout.write(f'GLOBAL              {n}/{t}  ({100 * n / t:.0f}%)')
        for g, etiqueta in (('cubierta', 'Cubiertas por corpus'), ('fuera', 'Fuera del corpus   ')):
            if total[g]:
                self.stdout.write(f'  {etiqueta}  {ok[g]}/{total[g]}  '
                                  f'({100 * ok[g] / total[g]:.0f}%)')
        self.stdout.write('=' * 74)

        if fallos:
            self.stdout.write('')
            self.stdout.write(f'Fallos ({len(fallos)}):')
            for pregunta, esperado, detalle in fallos:
                quiere = 'abstenerse' if esperado is FUERA else f'fuente ~ {esperado}'
                self.stdout.write(f'  {pregunta}')
                self.stdout.write(f'      esperado: {quiere}  |  obtenido: {detalle}')

    # ------------------------------------------------------------------
    def _con_juez(self):
        """Mide la cadena completa: indice recupera, modelo decide.

        Es lo que de verdad ve el usuario. La recuperacion sola no basta como
        metrica porque siempre devuelve el fragmento menos malo.
        """
        import re

        from apps.samples.rag_qa import responder_documental

        self.stdout.write('Cadena completa: indice + modelo juez  (~30s por pregunta)')
        self.stdout.write('=' * 74)

        ok = {'cubierta': 0, 'fuera': 0}
        total = {'cubierta': 0, 'fuera': 0}
        fallos = []

        for pregunta, esperado in BANCO:
            grupo = 'fuera' if esperado is FUERA else 'cubierta'
            total[grupo] += 1
            r = responder_documental(pregunta)

            if esperado is FUERA:
                bien = not r.responde
                detalle = 'se abstuvo' if bien else f'RESPONDIO: {r.texto[:50]}'
            else:
                bien = r.responde and any(
                    re.search(esperado, c.fragmento.fuente) for c in r.citas)
                if not r.responde:
                    detalle = f'se abstuvo ({r.motivo})'
                else:
                    fuentes = ', '.join(sorted({c.fragmento.fuente.split(':')[0]
                                                for c in r.citas}))
                    detalle = f'respondio citando {fuentes}'

            ok[grupo] += bien
            if not bien:
                fallos.append((pregunta, esperado, detalle))
            self.stdout.write(
                f'{"OK " if bien else "MAL"} [{grupo:8}] {pregunta[:44]:<44} '
                f'{detalle[:56]}  {r.latency_ms/1000:.0f}s')

        n, t = sum(ok.values()), sum(total.values())
        self.stdout.write('=' * 74)
        self.stdout.write(f'GLOBAL              {n}/{t}  ({100 * n / t:.0f}%)')
        for g, etiqueta in (('cubierta', 'Cubiertas por corpus'),
                            ('fuera', 'Fuera del corpus   ')):
            if total[g]:
                self.stdout.write(f'  {etiqueta}  {ok[g]}/{total[g]}  '
                                  f'({100 * ok[g] / total[g]:.0f}%)')
        self.stdout.write('=' * 74)
        if fallos:
            self.stdout.write('')
            self.stdout.write(f'Fallos ({len(fallos)}):')
            for pregunta, esperado, detalle in fallos:
                quiere = 'abstenerse' if esperado is FUERA else f'citar ~ {esperado}'
                self.stdout.write(f'  {pregunta}')
                self.stdout.write(f'      esperado: {quiere}  |  obtenido: {detalle}')
