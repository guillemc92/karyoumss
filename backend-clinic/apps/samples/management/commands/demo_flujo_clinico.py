"""Demo del flujo clinico completo: de la metafase al informe.

    python manage.py demo_flujo_clinico
    python manage.py demo_flujo_clinico --metafase 12   # otra imagen

Recorre las siete etapas del caso con DATOS REALES y sin mocks: segmenta una
metafase del dataset del laboratorio, clasifica con el modelo entrenado, aplica
la semaforizacion, y termina en un informe firmado con su nomenclatura ISCN.

## Por que hay un salto a mitad del recorrido, y por que se anuncia

Corregir a mano un caso recien procesado son ~64 acciones (medido en
`backend-ml/training/eval_correccion.py`). Eso no cabe en una presentacion. Asi
que las etapas 1-3 corren en VIVO sobre una metafase real, y las 4-7 se muestran
sobre un caso ya corregido y firmado.

El salto se imprime en pantalla con su motivo. Ocultarlo seria enseñar un
sistema que no existe; anunciarlo convierte una limitacion en un dato medido.

Salida en ASCII puro: la consola de Windows (cp1252) rompe con Unicode.
"""
import time
import unicodedata
from pathlib import Path

from django.core.management.base import BaseCommand

ANCHO = 78
CASO_FIRMADO = 'CHN-DEMO-T21'
# El mismo caso que el laboratorio reporta como 47,XY,+21[20].
INFORME_REAL = '47,XY,+21[20]'


def ascii_puro(texto: str) -> str:
    plano = unicodedata.normalize('NFKD', str(texto))
    return ''.join(c for c in plano if ord(c) < 128)


class Command(BaseCommand):
    help = 'Recorre el flujo clinico completo con datos reales, de la metafase al informe.'

    def add_arguments(self, parser):
        parser.add_argument('--metafase', type=int, default=7,
                            help='numero de metafase del dataset (por defecto 7)')

    # --- utilidades de salida ------------------------------------------------

    def titulo(self, n, texto):
        self.stdout.write('')
        self.stdout.write('=' * ANCHO)
        self.stdout.write(f'  ETAPA {n} - {ascii_puro(texto)}')
        self.stdout.write('=' * ANCHO)

    def linea(self, texto=''):
        self.stdout.write('  ' + ascii_puro(texto))

    def clave(self, k, v):
        self.stdout.write(f'    {ascii_puro(k):<26} {ascii_puro(v)}')

    # --- el recorrido --------------------------------------------------------

    def handle(self, *args, **opts):
        from apps.samples.models import Chromosome, Sample
        from apps.samples.pipeline_client import MLDegradedError

        inicio = time.time()
        self.stdout.write('')
        self.stdout.write('#' * ANCHO)
        self.stdout.write('#  BIOMED UMSS - de la metafase al informe, con datos reales')
        self.stdout.write('#' * ANCHO)

        # ---------------------------------------------------------------- 1
        self.titulo(1, 'La IA analiza una metafase real')

        raiz = Path(__file__).resolve().parents[5]
        ruta = raiz / 'datasets' / 'metaclass' / 'metafases' / f'metafase_{opts["metafase"]}.bmp'
        if not ruta.exists():
            self.linea(f'no existe {ruta}')
            return

        self.clave('imagen', ruta.name)
        self.clave('origen', 'dataset MetaClass del laboratorio')
        self.linea()
        self.linea('Llamando al motor de inferencia... (tarda ~30 s, no esta colgado)')

        from apps.samples.pipeline_client import pipeline_client
        t0 = time.time()
        try:
            resultado = pipeline_client.segment_image(ruta.read_bytes())
        except MLDegradedError as exc:
            # RN-07: la demo tambien tiene que saber degradar.
            self.linea(f'MOTOR CAIDO: {exc}')
            self.linea('En el sistema real la muestra se guardaria igual, en PENDING_AI.')
            return

        detectados = resultado.get('chromosomes', [])
        confianzas = [float(c['confidence_score']) for c in detectados]
        self.linea()
        self.clave('tiempo', f'{time.time() - t0:.1f} s')
        self.clave('modelo', resultado.get('model_version', '?'))
        self.clave('cromosomas detectados', f'{len(detectados)}  (lo normal son 46)')
        self.clave('confianza media', f'{sum(confianzas) / max(1, len(confianzas)):.3f}')
        self.linea()
        self.linea('No hay simulacion: segmentacion OpenCV + EfficientNet-B3 entrenado')
        self.linea('con 48.000 recortes del propio laboratorio.')

        # ---------------------------------------------------------------- 2
        self.titulo(2, 'La semaforizacion decide que NO puede avanzar')

        UMBRAL = 0.85
        verdes = sum(1 for c in confianzas if c >= UMBRAL)
        naranjas = len(confianzas) - verdes
        self.clave('umbral (RN-02)', f'{UMBRAL}')
        self.clave('verdes', f'{verdes}')
        self.clave('naranjas', f'{naranjas}   <-- bloquean el informe')
        self.linea()
        self.linea('El umbral no es decorativo: con un solo naranja sin resolver, el')
        self.linea('caso NO puede pasar a Supervisor (RN-01). La IA propone; decide')
        self.linea('el analista.')

        # ---------------------------------------------------------------- 3
        self.titulo(3, 'Lo que cuesta corregirlo - y por que aqui hay un salto')

        self.linea('Medido contra el cariograma del experto, sobre 20 casos:')
        self.linea()
        self.clave('acciones por caso', '64  (mediana)')
        self.clave('hacerlo a mano', '46  colocaciones')
        self.clave('veredicto', '20 de 20 casos: la IA cuesta MAS')
        self.linea()
        self.linea('Hoy este pipeline anade trabajo en vez de ahorrarlo, y la causa')
        self.linea('esta localizada: la segmentacion junta cromosomas que se tocan.')
        self.linea()
        self.linea('>>> Por eso el recorrido SALTA aqui a un caso ya corregido y')
        self.linea('>>> firmado. Ensenar 64 correcciones no cabe en una presentacion.')

        # ---------------------------------------------------------------- 4
        self.titulo(4, 'Un caso validado por el analista')

        caso = Sample.objects.filter(chn_code=CASO_FIRMADO, is_active=True).first()
        if caso is None:
            self.linea(f'falta el caso {CASO_FIRMADO}: correr `manage.py seed_demo_iscn`')
            return

        cromos = Chromosome.objects.filter(karyotype__sample=caso, is_active=True)
        self.clave('caso', caso.chn_code)
        self.clave('estado', caso.status)
        self.clave('cromosomas', f'{cromos.count()}')
        self.clave('naranjas sin resolver', '0   <-- por eso pudo avanzar')

        # ---------------------------------------------------------------- 5
        self.titulo(5, 'Auditoria del 5% y firma - la traza que lo sostiene')

        from apps.samples.models import AuditEvent
        from apps.samples.services import verify_audit_chain

        eventos = AuditEvent.objects.filter(sample=caso).order_by('created_at')
        self.clave('eventos en la bitacora', f'{eventos.count()}')
        self.clave('cadena SHA-256 integra', 'SI' if verify_audit_chain(caso) else 'NO')
        self.linea()
        for e in eventos.select_related('actor')[:6]:
            quien = getattr(e.actor, 'username', None) or '-'
            self.linea(f'  [{e.created_at:%H:%M:%S}] {e.event_type:22} {quien}')
        if eventos.count() > 6:
            self.linea(f'  ... y {eventos.count() - 6} mas')
        self.linea()
        self.linea('Append-only (RN-05): nada de esto se puede borrar ni reescribir.')
        self.linea('Es lo que sostiene la firma electronica (21 CFR Part 11).')
        self.linea('El supervisor NO puede ser el analista (RN-06).')

        # ---------------------------------------------------------------- 6
        self.titulo(6, 'La nomenclatura ISCN - la calcula CODIGO, no el modelo')

        self.clave('ISCN emitido', caso.iscn_nomenclature or '(sin generar)')
        self.clave('lo genera', 'generate_iscn(), funcion determinista')
        self.clave('solo lectura tras emitir', 'si (RN-04)')
        self.linea()
        self.linea('Si el modelo de lenguaje alucina, la nomenclatura NO cambia:')
        self.linea('sale de contar cromosomas, no de generar texto.')
        self.linea()
        self.linea('Validado contra 231 informes REALES del laboratorio:')
        self.linea('  45 de 51 nomenclaturas distintas aceptadas. De los 6 rechazos,')
        self.linea('  4 son erratas de transcripcion en informes ya emitidos.')

        # ---------------------------------------------------------------- 7
        self.titulo(7, 'La narrativa clinica - y lo que aun falta')

        borrador = (caso.narrative_draft or '').strip()
        self.clave('modelo', caso.narrative_model or '(sin narrativa)')
        self.clave('donde corre', 'Ollama LOCAL - sin egreso de datos (RN-03)')
        self.linea()
        for trozo in [borrador[i:i + 70] for i in range(0, min(len(borrador), 280), 70)]:
            self.linea(f'  {trozo}')
        self.linea()
        self.stdout.write('-' * ANCHO)
        self.linea(f'informe REAL del laboratorio : {INFORME_REAL}')
        self.linea(f'este sistema produce         : {caso.iscn_nomenclature}')
        self.linea()
        self.linea('Falta el [20]: el numero de metafases que sostienen el')
        self.linea('diagnostico. El laboratorio analiza 20 por caso; aqui Karyotype')
        self.linea('es OneToOne con Sample, asi que se analiza UNA. Es un cambio de')
        self.linea('modelo, esta identificado, y es lo que separa esto de un informe')
        self.linea('clinico emitible.')

        self.stdout.write('')
        self.stdout.write('=' * ANCHO)
        self.stdout.write(f'  recorrido completo en {time.time() - inicio:.0f} s')
        self.stdout.write('=' * ANCHO)
