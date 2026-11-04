"""Seed fijo del experimento E3 (DD-E3-001 D6).

    python manage.py sembrar_bench --semilla 42 --muestras 1000 --salida /k6data

Llena la base con casos ficticios. No hay PII (RN-03): ni pacientes ni nombres,
solo códigos CHN sintéticos. Escribe en `--salida/ids.json` los ids de muestra
que k6 va a pedir: k6 no inventa datos.

**Qué es determinista** con la misma semilla:
- los ids de las muestras;
- cuántos eventos tiene cada caso;
- el tipo, el cromosoma y el payload de cada evento.

**Qué no es determinista:** las horas y los ids de los eventos. Los pone
`emit_audit_event()`, como en producción, y por eso las cadenas de hashes son
válidas.

**Volumen:** imita la base de demo medida el 2026-11-02 (434 eventos en 32
casos, con una media de 13,6 y un máximo de 70). Cada caso tiene entre 3 y 70
eventos, con una media de unos 14, y 46 cromosomas.
"""
import json
import random
import uuid
from decimal import Decimal
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.samples.models import AuditEventType, Chromosome, Karyotype, Sample
from apps.samples.services import emit_audit_event

USUARIO_BENCH = 'bench.analista@biomed.test'
EVENTOS_MIN, EVENTOS_MAX, EVENTOS_MEDIA = 3, 70, 14
CLASES = [str(n) for n in range(1, 23) for _ in (0, 1)] + ['X', 'X']  # 46: un cariotipo 46,XX
TIPOS = [
    AuditEventType.XAI_VIEWED, AuditEventType.ACCEPT_CHROMOSOME, AuditEventType.CORRECT_CLASS,
    AuditEventType.RECLASSIFY, AuditEventType.MARK_ANOMALY, AuditEventType.ORIENT, AuditEventType.RECROP,
]


def eventos_del_caso(rng: random.Random) -> int:
    """Cola larga como la de la base real: la mayoría pocos, algunos muchos."""
    return min(EVENTOS_MAX, EVENTOS_MIN + int(rng.expovariate(1 / (EVENTOS_MEDIA - EVENTOS_MIN))))


class Command(BaseCommand):
    help = 'Seed fijo y sin PII para el experimento E3 (DD-E3-001).'

    def add_arguments(self, parser):
        parser.add_argument('--semilla', type=int, default=42)
        parser.add_argument('--muestras', type=int, default=1000)
        parser.add_argument('--salida', type=Path, required=True, help='Carpeta donde escribir ids.json')

    def handle(self, *args, semilla, muestras, salida, **opts):
        if Sample.objects.filter(chn_code__startswith='CHN-BENCH-').exists():
            raise CommandError('La base ya tiene el seed del banco: se parte de una vacía (docker compose down -v).')
        rng = random.Random(semilla)
        User = get_user_model()
        analista = User.objects.create_user(username=USUARIO_BENCH, email=USUARIO_BENCH)

        ids, total_eventos = [], 0
        for i in range(muestras):
            with transaction.atomic():
                sample = Sample.objects.create(
                    id=uuid.UUID(int=rng.getrandbits(128), version=4),
                    chn_code=f'CHN-BENCH-{i:05d}', patient_ref=f'ANON-BENCH-{i:05d}',
                    analyst=analista, status='READY',
                )
                karyo = Karyotype.objects.create(sample=sample)
                cromosomas = Chromosome.objects.bulk_create([
                    Chromosome(karyotype=karyo, predicted_class=clase, order=n, position_index=n % 2,
                               confidence_score=Decimal(rng.randint(700, 999)) / 1000)
                    for n, clase in enumerate(CLASES)
                ])
                for _ in range(eventos_del_caso(rng)):
                    c = rng.choice(cromosomas)
                    emit_audit_event(sample, analista, rng.choice(TIPOS), chromosome=c,
                                     payload={'clase': c.predicted_class, 'n': rng.randint(1, 9)})
                    total_eventos += 1
            ids.append(str(sample.id))

        salida.mkdir(parents=True, exist_ok=True)
        (salida / 'ids.json').write_text(json.dumps(ids), encoding='utf-8')
        self.stdout.write(f'{muestras} muestras, {muestras * len(CLASES)} cromosomas, '
                          f'{total_eventos} eventos (semilla {semilla}); ids en {salida / "ids.json"}')
