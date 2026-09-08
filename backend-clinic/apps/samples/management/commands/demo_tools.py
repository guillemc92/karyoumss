"""Demo de tool calling - los cuatro escenarios de la consigna (Módulo 6).

Muestra que el modelo ELIGE la herramienta pero el CÓDIGO produce la respuesta.
En cada escenario se imprime qué herramienta se usó, de qué tabla salió el dato
y por qué camino se resolvió.

    python manage.py demo_tools              # los cuatro escenarios
    python manage.py demo_tools --sin-ia     # fuerza el interruptor apagado
    python manage.py demo_tools -p "texto"   # una pregunta suelta

No imprime credenciales: Ollama corre en localhost y no usa API key.
"""
from django.conf import settings
from django.core.management.base import BaseCommand

from apps.samples.tool_router import responder

# La MISMA pregunta de fondo en 1, 2 y 4; una distinta en el 3 (consigna).
PREGUNTA_BASE = '¿Qué cromosomas están naranjas?'
PREGUNTA_SINONIMO = '¿Cuáles necesitan que el analista los mire de nuevo?'
PREGUNTA_FUERA = '¿Cuál es el presupuesto del laboratorio para 2027?'

ANCHO = 74


class Command(BaseCommand):
    help = 'Demuestra tool calling: el modelo elige, el código responde'

    def add_arguments(self, parser):
        parser.add_argument('-p', '--pregunta', default='', help='consulta suelta')
        parser.add_argument('--sin-ia', action='store_true', help='simula el interruptor apagado')

    def handle(self, *args, **opts):
        if opts['sin_ia']:
            settings.CLINIC_LLM_ENABLED = False

        self._titulo('DEMO - Tool calling  |  BIOMED UMSS')
        self.stdout.write(f'  modelo    : {settings.CLINIC_LLM_MODEL}  (versión fija, nunca "latest")')
        self.stdout.write(f'  proveedor : Ollama local - {settings.CLINIC_LLM_URL}')
        self.stdout.write(self.style.WARNING(f'  IA        : {"ENCENDIDA" if settings.CLINIC_LLM_ENABLED else "APAGADA (feature flag)"}'))

        if opts['pregunta']:
            self._escenario('Consulta suelta', opts['pregunta'], '')
            return

        self._escenario(
            '1. CONTROLADO', PREGUNTA_BASE,
            'Usa "naranjas", palabra del catálogo -> se resuelve SIN llamar al modelo.',
        )
        self._escenario(
            '2. SINÓNIMO', PREGUNTA_SINONIMO,
            'El dato existe pero la palabra no está en el catálogo -> escala al modelo.\n'
            '   Debe devolver LO MISMO que el escenario 1.',
        )
        self._escenario(
            '3. FUERA DE ALCANCE', PREGUNTA_FUERA,
            'Ninguna herramienta responde eso -> dice que no sabe y publica el catálogo.\n'
            '   No es un error ni una respuesta inventada.',
        )

        # Escenario 4: la misma del 1, con el interruptor apagado.
        previo = settings.CLINIC_LLM_ENABLED
        settings.CLINIC_LLM_ENABLED = False
        self._escenario(
            '4. MODELO APAGADO', PREGUNTA_BASE,
            'La misma pregunta del 1 con CLINIC_LLM_ENABLED=false.\n'
            '   Los datos salen igual: la respuesta la produce el código.',
        )
        # Y la medición que pide la consigna: qué se pierde al apagar la IA.
        self._escenario(
            '4-bis. SINÓNIMO SIN IA', PREGUNTA_SINONIMO,
            'La pregunta del escenario 2, ahora sin modelo. Cae en "no sé" -\n'
            '   eso es exactamente lo que aporta la IA, medido.',
        )
        settings.CLINIC_LLM_ENABLED = previo

    # ------------------------------------------------------------------
    def _titulo(self, texto: str):
        self.stdout.write('=' * ANCHO)
        self.stdout.write(texto)
        self.stdout.write('=' * ANCHO)

    def _escenario(self, etiqueta: str, pregunta: str, nota: str):
        self.stdout.write('')
        self.stdout.write('-' * ANCHO)
        self.stdout.write(self.style.MIGRATE_HEADING(f'[{etiqueta}]'))
        if nota:
            self.stdout.write(f'   {nota}')
        self.stdout.write(f'   Pregunta: "{pregunta}"')
        self.stdout.write('-' * ANCHO)

        r = responder(pregunta)

        # La procedencia: qué herramienta y de qué tabla salió el dato.
        self.stdout.write(f'   Camino      : {r.camino}')
        self.stdout.write(f'   Herramienta : {r.tool or "-"}')
        self.stdout.write(f'   Fuente      : {r.source or "-"}')
        if r.motivo:
            self.stdout.write(f'   Motivo (LLM): {r.motivo}')
        self.stdout.write(f'   Latencia    : {r.latency_ms} ms')
        self.stdout.write(f'   {r.mensaje}')

        for fila in r.filas[:5]:
            self.stdout.write('     - ' + '  |  '.join(f'{k}={v}' for k, v in fila.items()))
        if len(r.filas) > 5:
            self.stdout.write(f'     ... y {len(r.filas) - 5} más')

        if r.catalogo:
            self.stdout.write('   Lo que SÍ puedo responder:')
            for c in r.catalogo:
                self.stdout.write(f'     - {c["herramienta"]}  ({c["fuente"]})')
