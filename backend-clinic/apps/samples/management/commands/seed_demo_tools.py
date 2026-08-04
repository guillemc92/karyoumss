"""Siembra un caso con cromosomas naranjas para la demo de tool calling.

Los escenarios 1, 2 y 4 consultan cromosomas pendientes de revisión (RN-02).
Sin ninguno en la base, la demo corre pero no muestra datos — y el punto de la
consigna es justamente ver de qué tabla sale cada resultado.

    python manage.py seed_demo_tools
    python manage.py demo_tools
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.samples.models import Chromosome, Karyotype, Sample, SampleStatus

CHN = 'CHN-DEMO-TOOLS'
# Naranjas: bajo el umbral de 0.85 (RN-02) y sin resolver.
NARANJAS = [('9', '0.612'), ('13', '0.704'), ('21', '0.783'), ('X', '0.548')]


class Command(BaseCommand):
    help = 'Siembra un caso con cromosomas naranjas para demo_tools'

    def handle(self, *args, **opts):
        User = get_user_model()
        analista, _ = User.objects.get_or_create(username='demo_analista')

        Sample.objects.filter(chn_code=CHN).delete()
        sample = Sample.objects.create(
            chn_code=CHN, analyst=analista,
            status=SampleStatus.READY, sample_type='sangre',
        )
        karyotype = Karyotype.objects.create(sample=sample)

        for orden, (clase, conf) in enumerate(NARANJAS):
            Chromosome.objects.create(
                karyotype=karyotype, predicted_class=clase, position_index=0,
                confidence_score=Decimal(conf),
                resolution_status='PENDING',   # pendiente de revisión del analista
                order=orden,
            )

        self.stdout.write(self.style.SUCCESS(
            f'Caso {CHN}: {len(NARANJAS)} cromosomas naranjas (confianza < 0.85)'))
        self.stdout.write('Ahora: python manage.py demo_tools')
