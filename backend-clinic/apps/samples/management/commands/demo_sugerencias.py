"""Paso 6 del RAG: el CODIGO que compara similitudes y su SALIDA, juntos.

    python manage.py demo_sugerencias

Pensado para una sola captura. El codigo no esta copiado aqui: se lee de la
fuente real con `inspect.getsource`, asi que no puede quedar desincronizado del
que se ejecuta un segundo despues.

Se corren DOS preguntas a proposito, porque el paso 6 hace cosas distintas
segun el corpus responda o no, y la segunda es la que justifica la funcion:
convierte un "no se" en una pista para reformular.

Salida en ASCII puro (la consola de Windows en cp1252 rompe con Unicode).
"""
import inspect
import unicodedata

from django.core.management.base import BaseCommand

from apps.samples import rag_sugerencias
from apps.samples.rag_qa import responder_documental

CUBIERTA = 'Por que el sistema marca cromosomas en naranja?'
FUERA = 'Cual es el telefono del doctor Rojas?'
ANCHO = 78


def ascii_puro(texto: str) -> str:
    """Sin acentos ni simbolos raros: la consola de Windows los rompe."""
    plano = unicodedata.normalize('NFKD', texto)
    return ''.join(c for c in plano if ord(c) < 128)


class Command(BaseCommand):
    help = 'Paso 6 del RAG: comparacion de similitudes y sugerencias, con su codigo.'

    def _regla(self, titulo=''):
        if titulo:
            self.stdout.write('-' * ANCHO)
            self.stdout.write(titulo)
        self.stdout.write('-' * ANCHO)

    def _caso(self, pregunta: str, etiqueta: str):
        self._regla(etiqueta)
        self.stdout.write(f'  PREGUNTA: {ascii_puro(pregunta)}')
        r = responder_documental(pregunta)
        self.stdout.write(f'  responde={r.responde}  '
                          f'juez_vio={len(r.candidatos)}  '
                          f'vecinos={len(r.vecinos)}  citas={len(r.citas)}')
        if r.responde:
            self.stdout.write(f'  RESPUESTA: {ascii_puro(r.texto)[:200]}')
        else:
            self.stdout.write(f'  MOTIVO   : {ascii_puro(r.motivo)}')
        self.stdout.write('')
        self.stdout.write('  --- PASO 6: comparacion de similitud ---')
        salida = rag_sugerencias.texto(r.sugerencias)
        for linea in (salida or '(sin sugerencias)').splitlines():
            self.stdout.write(f'  {ascii_puro(linea)}')
        self.stdout.write('')

    def handle(self, *args, **opts):
        self._regla('PASO 6 DEL RAG  |  comparar porcentajes y sugerir donde mirar')
        self.stdout.write('  Medido antes de construirlo: NI la similitud, NI el margen,')
        self.stdout.write('  NI la dispersion separan las preguntas cubiertas de las que no.')
        self.stdout.write('  Por eso ninguna sugerencia afirma pertinencia: solo dice que')
        self.stdout.write('  es lo mas parecido que hay. Ver ADR-0029 D7.')

        self._regla('CODIGO  (apps/samples/rag_sugerencias.py, leido en vivo)')
        for linea in inspect.getsource(rag_sugerencias.sugerir).rstrip().splitlines():
            self.stdout.write('  ' + ascii_puro(linea))

        self._caso(CUBIERTA, 'CASO 1 - el corpus SI responde  ->  sugerencias de AMPLIAR')
        self._caso(FUERA, 'CASO 2 - el corpus NO responde  ->  sugerencias de EXPLORAR')

        self._regla()
        self.stdout.write('  El caso 2 es el que justifica el paso 6: sin el, un "no se"')
        self.stdout.write('  es un callejon sin salida y el usuario no sabe si reformular.')
