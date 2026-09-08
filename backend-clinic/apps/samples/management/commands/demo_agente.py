"""Demo del bucle agentico (nivel 4) con la traza completa a la vista.

    python manage.py demo_agente
    python manage.py demo_agente -p "tu pregunta"

Los niveles anteriores decidian UNA cosa. El agente encadena: puede consultar el
estado, despues la documentacion, y combinar ambas en una respuesta. Lo que hay
que ver aqui es la TRAZA -accion, observacion, accion...- porque es la evidencia
que pide la consigna y lo unico que permite auditar por que dijo lo que dijo.

Lento: cada paso del bucle es una llamada al modelo (~30-200 s en CPU).

Salida en ASCII (consola Windows cp1252).
"""
from django.core.management.base import BaseCommand

from apps.samples.agente import AgenteError, MAX_PASOS, ejecutar_agente
from apps.samples.agente_acciones import INSTRUCCIONES, ejecutar, schemas

ANCHO = 78

# Tres casos que muestran las tres formas de resolver del agente.
CASOS = [
    ('SOLO ESTADO',
     'Que casos estan pendientes de firma?',
     'Se resuelve con una herramienta: una accion y responde.'),
    ('SOLO DOCUMENTACION',
     'Que significa que un cromosoma este marcado en naranja?',
     'No es estado, es una regla: el agente va al RAG y cita la fuente.'),
    ('ENCADENADO',
     'Hay cromosomas pendientes de revisar, y por que hay que revisarlos?',
     'Necesita las DOS cosas: consultar el estado y consultar la regla. '
     'Esto es lo que un solo tool call no puede hacer.'),
]


class Command(BaseCommand):
    help = 'Corre el bucle agentico mostrando la traza paso a paso.'

    def add_arguments(self, parser):
        parser.add_argument('-p', '--pregunta', default='',
                            help='una consulta suelta en vez de los tres casos')
        parser.add_argument('--max-pasos', type=int, default=MAX_PASOS)
        parser.add_argument('--mcp', action='store_true',
                            help='usa las herramientas DESCUBIERTAS por protocolo '
                                 'en vez de las importadas. El bucle es el mismo.')

    def _regla(self, titulo=''):
        if titulo:
            self.stdout.write('-' * ANCHO)
            self.stdout.write(titulo)
        self.stdout.write('-' * ANCHO)

    def _correr(self, etiqueta, pregunta, nota, max_pasos, acciones=None):
        self._regla(f'[{etiqueta}]')
        if nota:
            self.stdout.write(f'   {nota}')
        self.stdout.write(f'   Pregunta: "{pregunta}"')
        self._regla()

        # Aqui esta la gracia de la fase 5: el bucle recibe (schemas, ejecutar)
        # y le da igual si vienen de un import o del protocolo.
        mis_schemas, mi_ejecutar = acciones or (schemas(), ejecutar)

        try:
            r = ejecutar_agente(pregunta, mis_schemas, mi_ejecutar,
                                INSTRUCCIONES, max_pasos=max_pasos)
        except AgenteError as exc:
            self.stdout.write(f'   AGENTE NO DISPONIBLE: {exc}')
            self.stdout.write('   (el sistema degrada, no cae: RN-07)')
            return

        self.stdout.write('   TRAZA:')
        self.stdout.write(r.traza.resumen())
        self.stdout.write('')
        self.stdout.write(f'   Pasos       : {len(r.traza.pasos)} '
                          f'(tope {max_pasos})')
        self.stdout.write(f'   Tokens      : {r.traza.tokens_entrada} entrada / '
                          f'{r.traza.tokens_salida} salida')
        self.stdout.write(f'   Latencia    : {r.traza.latency_ms / 1000:.0f} s')
        self.stdout.write(f'   Completado  : {"si" if r.completado else "NO (corte por tope)"}')
        self.stdout.write('')
        self.stdout.write('   RESPUESTA:')
        for linea in (r.respuesta or '(vacia)').splitlines():
            self.stdout.write(f'     {linea}')
        self.stdout.write('')

    def handle(self, *args, **opts):
        if opts['mcp']:
            from apps.samples.mcp_conexion import ConexionMCP

            with ConexionMCP() as conexion:
                acciones = (conexion.descubrir_tools(), conexion.ejecutar_tool)
                self._cabecera(opts, acciones[0], via='MCP (descubiertas por protocolo)')
                self._todos(opts, acciones)
            return

        acciones = (schemas(), ejecutar)
        self._cabecera(opts, acciones[0], via='import local')
        self._todos(opts, acciones)

    def _cabecera(self, opts, mis_schemas, via):
        self._regla('DEMO - Bucle agentico (ReAct)  |  BIOMED UMSS')
        self.stdout.write(f'   herramientas: {len(mis_schemas)}  via {via}')
        for s in mis_schemas:
            self.stdout.write(f'     - {s["function"]["name"]}')
        self.stdout.write(f'   tope de pasos: {opts["max_pasos"]}  '
                          f'(un agente sin tope es un bucle infinito con factura)')
        self.stdout.write('')

    def _todos(self, opts, acciones):
        if opts['pregunta']:
            self._correr('CONSULTA', opts['pregunta'], '',
                         opts['max_pasos'], acciones)
            return
        for etiqueta, pregunta, nota in CASOS:
            self._correr(etiqueta, pregunta, nota, opts['max_pasos'], acciones)
