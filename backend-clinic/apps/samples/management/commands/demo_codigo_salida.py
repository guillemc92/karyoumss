"""Muestra el CODIGO que llama al modelo y su SALIDA en la misma pantalla.

    python manage.py demo_codigo_salida

Pensado para una sola captura: la consigna valora ver el codigo junto a su
resultado, y dos capturas pegadas no prueban que sean la misma ejecucion.

El codigo NO esta copiado aqui: se lee de la fuente real con `inspect.getsource`,
asi que no puede quedar desincronizado del que se ejecuta un segundo despues.

Tarda ~3 minutos: el escenario 2 no coincide con ninguna palabra clave, asi que
va por el modelo. Esa espera es justamente lo que se quiere demostrar.

Salida en ASCII puro (la consola de Windows en cp1252 rompe con Unicode).
"""
import inspect

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.samples import tool_router
from apps.samples.tool_router import responder

PREGUNTA = '¿Cuáles necesitan que el analista los mire de nuevo?'
ANCHO = 78


class Command(BaseCommand):
    help = 'Escenario 2 (sinonimo): imprime el codigo que elige la herramienta y su salida.'

    def _regla(self, titulo=''):
        if titulo:
            self.stdout.write('-' * ANCHO)
            self.stdout.write(titulo)
        self.stdout.write('-' * ANCHO)

    def handle(self, *args, **opts):
        self._regla('ESCENARIO 2 - SINONIMO  |  el MODELO elige la herramienta')
        self.stdout.write(f'  modelo    : {settings.CLINIC_LLM_MODEL}   (version fija, nunca "latest")')
        self.stdout.write(f'  proveedor : {settings.CLINIC_LLM_URL}')
        self.stdout.write(f'  IA        : {"ENCENDIDA" if settings.CLINIC_LLM_ENABLED else "APAGADA"}')

        # --- el codigo, leido de la fuente real --------------------------------
        self._regla('CODIGO  (apps/samples/tool_router.py, leido en vivo)')
        for linea in inspect.getsource(tool_router._elegir_con_modelo).rstrip().splitlines():
            self.stdout.write('  ' + linea)

        # --- la salida de ejecutarlo -------------------------------------------
        self._regla('SALIDA  (ejecutando ese mismo codigo, ahora)')
        self.stdout.write(f'  Pregunta: "{PREGUNTA}"')
        self.stdout.write('  (ninguna palabra del catalogo coincide -> escala al modelo)')
        self.stdout.write('')

        r = responder(PREGUNTA)

        self.stdout.write(f'  Camino      : {r.camino}')
        self.stdout.write(f'  Herramienta : {r.tool or "-"}      <- la eligio el MODELO')
        self.stdout.write(f'  Fuente      : {r.source or "-"}    <- tabla real, no inventada')
        if r.motivo:
            self.stdout.write(f'  Motivo (LLM): {r.motivo}')
        self.stdout.write(f'  Latencia    : {r.latency_ms} ms')
        self.stdout.write(f'  {r.mensaje}')
        for fila in r.filas[:3]:
            self.stdout.write('    - ' + '  |  '.join(f'{k}={v}' for k, v in fila.items()))
        if len(r.filas) > 3:
            self.stdout.write(f'    ... y {len(r.filas) - 3} mas')

        self._regla()
        self.stdout.write('  El modelo devolvio UN NOMBRE. Las filas las produjo Django ORM:')
        self.stdout.write('  son las mismas que da el escenario 1 sin llamar al modelo.')
        self._regla()
