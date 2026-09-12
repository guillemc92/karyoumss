"""Crea el caso de demostración con trisomía 21 (para la entrega del módulo de IA).

Deja un caso en estado REPORTED con su ISCN generado por el motor determinístico
(S3, ADR-0025), listo para que `demo_llm` lo narre. Idempotente: recrea el caso
si ya existe.

    python manage.py seed_demo_iscn
    python manage.py demo_llm --chn CHN-DEMO-T21
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.samples.models import Chromosome, Karyotype, Sample, SampleStatus
from apps.samples.services import generate_case_iscn

CHN = 'CHN-DEMO-T21'
AUTOSOMAS = [str(n) for n in range(1, 23)]


class Command(BaseCommand):
    help = 'Siembra el caso de demo (trisomía 21) con su ISCN generado por S3'

    def add_arguments(self, parser):
        parser.add_argument('--trisomia', default='21', help='clase con 3 copias (por defecto 21)')
        parser.add_argument('--sexo', default='XY', choices=['XX', 'XY'])

    def handle(self, *args, **opts):
        User = get_user_model()
        supervisor, _ = User.objects.get_or_create(
            username='demo_supervisor', defaults={'is_staff': True})
        if not supervisor.is_staff:
            supervisor.is_staff = True
            supervisor.save(update_fields=['is_staff'])

        Sample.objects.filter(chn_code=CHN).delete()
        sample = Sample.objects.create(
            chn_code=CHN, analyst=supervisor,
            status=SampleStatus.SIGNED,     # el ISCN se reporta tras la firma
            sample_type='sangre',
        )
        karyotype = Karyotype.objects.create(sample=sample)

        orden = 0
        for clase in AUTOSOMAS:
            for i in range(3 if clase == opts['trisomia'] else 2):
                Chromosome.objects.create(
                    karyotype=karyotype, predicted_class=clase, position_index=i,
                    confidence_score=Decimal('0.950'), order=orden)
                orden += 1
        for clase in (['X', 'X'] if opts['sexo'] == 'XX' else ['X', 'Y']):
            Chromosome.objects.create(
                karyotype=karyotype, predicted_class=clase, position_index=0,
                confidence_score=Decimal('0.950'), order=orden)
            orden += 1

        generate_case_iscn(sample, supervisor)
        sample.refresh_from_db()

        self.stdout.write(self.style.SUCCESS(
            f'Caso {sample.chn_code}: ISCN={sample.iscn_nomenclature} '
            f'estado={sample.status} ({orden} cromosomas)'))
        self.stdout.write(f'Ahora: python manage.py demo_llm --chn {CHN}')
