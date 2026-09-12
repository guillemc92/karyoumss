"""Siembra un cariotipo demo (46 cromosomas, ~3 naranjas) para una Sample.

Uso:
    python manage.py seed_karyotype <sample_id>
    python manage.py seed_karyotype --chn CHN-2026-07-13-0001

Ejercita la semaforización del visor (ADR-0021 P1, DD-KARYO-001 §6): la
mayoría verde (confianza alta) + 3 naranjas (18/5/13, por debajo de 0.85),
igual que el banner "3 cromosomas requieren revisión" del mockup.
"""
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError

from apps.samples.models import Chromosome, Karyotype, Sample

# 3 naranjas por debajo del umbral 0.85 — mismo set del mockup.
ORANGE_CONFIDENCES = {'18': Decimal('0.720'), '5': Decimal('0.800'), '13': Decimal('0.840')}


def build_demo_karyotype(sample: Sample) -> Karyotype:
    """Crea (o recrea) un cariotipo demo de 46 cromosomas para `sample`."""
    Karyotype.objects.filter(sample=sample).delete()
    karyotype = Karyotype.objects.create(sample=sample, image_path='demo/metaphase.png')

    order = 0
    for n in range(1, 23):
        label = str(n)
        for copy in range(2):  # par: 2 copias
            # Solo UNA copia del par baja de confianza (como el mockup: "18/5/13"
            # son 3 cromosomas puntuales, no 3 pares completos). La otra copia
            # queda verde.
            orange_conf = ORANGE_CONFIDENCES.get(label)
            is_orange = orange_conf is not None and copy == 0
            conf = orange_conf if is_orange else Decimal('0.960')
            Chromosome.objects.create(
                karyotype=karyotype,
                predicted_class=label,
                position_index=copy,
                confidence_score=conf,
                resolution_status='PENDING' if is_orange else 'AUTO',
                measures={'length_um': round(6.5 - n * 0.15, 2), 'centromeric_index': 0.42,
                          'band_count': 400 - n * 6, 'quality': 'alta'},
                bbox={'x': (n % 8) * 60, 'y': (n // 8) * 100, 'w': 40, 'h': 96},
                order=order,
            )
            order += 1

    # Par sexual XY (demo varón).
    for label in ('X', 'Y'):
        Chromosome.objects.create(
            karyotype=karyotype, predicted_class=label, position_index=0,
            confidence_score=Decimal('0.940'), resolution_status='AUTO',
            measures={'length_um': 5.0, 'centromeric_index': 0.40, 'band_count': 300, 'quality': 'alta'},
            bbox={'x': 480, 'y': 300, 'w': 40, 'h': 96}, order=order,
        )
        order += 1

    return karyotype


class Command(BaseCommand):
    help = 'Siembra un cariotipo demo (46 cromosomas, 3 naranjas) para una Sample.'

    def add_arguments(self, parser):
        parser.add_argument('sample_id', nargs='?', help='UUID de la Sample')
        parser.add_argument('--chn', help='CHN code de la Sample (alternativa al UUID)')

    def handle(self, *args, **options):
        sample_id = options.get('sample_id')
        chn = options.get('chn')
        if not sample_id and not chn:
            raise CommandError('Indique un sample_id o --chn')

        try:
            sample = Sample.objects.get(chn_code=chn) if chn else Sample.objects.get(pk=sample_id)
        except Sample.DoesNotExist:
            raise CommandError('Sample no encontrada')

        karyotype = build_demo_karyotype(sample)
        count = karyotype.chromosomes.count()
        self.stdout.write(self.style.SUCCESS(
            f'Cariotipo demo creado para {sample.chn_code}: {count} cromosomas (3 naranjas).'
        ))
