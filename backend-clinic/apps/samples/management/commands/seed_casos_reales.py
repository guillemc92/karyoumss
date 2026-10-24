"""Carga casos REALES del archivo del laboratorio para la defensa.

    python manage.py seed_casos_reales
    python manage.py seed_casos_reales --casos 18,131,123

Registra en la base de la demo unas cuantas metafases del dataset MetaClass,
las procesa con el pipeline real, y deja anotado **cuál es el cariograma que el
citogenetista produjo a mano para ese mismo caso**.

## Por qué esto importa en una presentación

`metafase_N` y `cario_N` son el mismo caso: uno es la entrada y el otro es la
salida que un humano produjo. Poner las dos cosas en pantalla permite enseñar
contra qué se está midiendo el sistema, en vez de mostrar solo su propia salida
y pedir que se confíe en ella.

Los casos por defecto se eligieron mirando el ground truth del experto:

    18   47,XX,+21   trisomía 21 — síndrome de Down, se ve en el cariograma
    131  46,XY       varón normal
    123  46,XX       mujer normal

El primero es el que conviene enseñar: la anomalía es visible a simple vista en
el cariograma del experto, tres cromosomas en el par 21 en vez de dos.

Salida en ASCII puro (la consola de Windows rompe con Unicode).
"""
import base64
import sys
import time
import unicodedata
from datetime import date
from pathlib import Path

from django.core.management.base import BaseCommand

# Elegidos por su ground truth, no al azar (ver docstring).
POR_DEFECTO = '18,131,123'
ANCHO = 78


def ascii_puro(t):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(t)) if ord(c) < 128)


class Command(BaseCommand):
    help = 'Carga casos reales del archivo del laboratorio, con su cariograma del experto.'

    def add_arguments(self, parser):
        parser.add_argument('--casos', default=POR_DEFECTO,
                            help='numeros de caso del dataset, separados por coma')
        parser.add_argument('--analista', default='demo.analista@biomed.umss.bo')

    def linea(self, t=''):
        self.stdout.write('  ' + ascii_puro(t))

    def handle(self, *args, **opts):
        from collections import Counter

        from django.contrib.auth import get_user_model

        from apps.samples.models import Chromosome, Sample
        from apps.samples.services import SampleRegistrationService

        raiz = Path(__file__).resolve().parents[5]
        metafases = raiz / 'datasets' / 'metaclass' / 'metafases'
        cariogramas = raiz / 'datasets' / 'metaclass' / 'cariogramas'
        if not metafases.exists():
            self.linea(f'no existe el dataset en {metafases}')
            return 1

        # Ground truth del experto, para poder comparar en pantalla.
        sys.path.insert(0, str(raiz / 'backend-ml' / 'training'))
        try:
            from eval_correccion import ground_truth
            gts = ground_truth()
        except Exception:                                  # noqa: BLE001
            gts = {}

        User = get_user_model()
        analista = User.objects.filter(username=opts['analista']).first()
        if analista is None:
            self.linea(f'no existe el usuario {opts["analista"]}')
            return 1

        servicio = SampleRegistrationService()
        hoy = date.today().strftime('%Y-%m-%d')

        self.stdout.write('=' * ANCHO)
        self.stdout.write('  CASOS REALES DEL ARCHIVO DEL LABORATORIO')
        self.stdout.write('=' * ANCHO)

        for n in [int(x) for x in opts['casos'].split(',') if x.strip()]:
            img = metafases / f'metafase_{n}.bmp'
            cario = cariogramas / f'cario_{n}.bmp'
            if not img.exists():
                self.linea(f'caso {n}: no existe {img.name}')
                continue

            chn = f'CHN-{hoy}-R{n:03d}'
            if Sample.objects.filter(chn_code=chn, is_active=True).exists():
                self.linea(f'caso {n}: {chn} ya existe, se omite')
                continue

            self.stdout.write('')
            self.linea(f'--- caso {n}  ->  {chn}')
            gt = gts.get(n)
            if gt:
                tri = [k for k, v in gt.items() if v == 3 and k.isdigit()]
                sexo = 'XY' if gt.get('Y') else 'XX'
                dice = f'{sum(gt.values())},{sexo}' + (f',+{tri[0]}' if tri else '')
                self.linea(f'    el EXPERTO dice : {dice}   (cario_{n}.bmp)')

            datos = base64.b64encode(img.read_bytes()).decode()
            t0 = time.time()
            r = servicio.register(
                {'patient': {'full_name': f'CASO ARCHIVO {n}', 'document_id': '0000000'},
                 'sample': {'chn_code': chn, 'sample_type': 'sangre'},
                 'clinical_history': {}, 'analysis_requests': [],
                 'images': [{'filename': img.name, 'data_base64': datos, 'source': 'upload'}],
                 'is_draft': False},
                analista,
            )

            muestra = Sample.objects.get(chn_code=chn)
            cr = list(Chromosome.objects.filter(karyotype__sample=muestra, is_active=True))
            naranjas = sum(1 for c in cr if float(c.confidence_score) < 0.85)
            self.linea(f'    la IA propone   : {len(cr)} cromosomas, {naranjas} naranjas '
                       f'({time.time() - t0:.0f} s)')
            if cr:
                top = Counter(c.predicted_class for c in cr).most_common(3)
                self.linea(f'    clases mas vistas: {dict(top)}')
            if r.get('degraded'):
                self.linea('    OJO: el motor de IA no respondio (modo degradado)')
            self.linea(f'    cariograma del experto: {cario if cario.exists() else "no disponible"}')

        self.stdout.write('')
        self.stdout.write('=' * ANCHO)
        self.linea('En la defensa: abrir el caso en el visor y, al lado, el .bmp del')
        self.linea('cariograma. Uno es lo que propone la IA; el otro, lo que un')
        self.linea('citogenetista produjo a mano para esa MISMA metafase.')
        self.stdout.write('=' * ANCHO)
