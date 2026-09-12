"""Desactiva (borrado logico) una muestra, o la vuelve a activar.

    python manage.py desactivar_muestra CHN-SMOKE-P2
    python manage.py desactivar_muestra CHN-SMOKE-P2 --reactivar

Sirve para sacar de la lista casos de prueba que no deben verse en una demo,
sin perder nada: es el mismo mecanismo con el que ya se retiro CHN-2026-08-06-2574.

## Que NO hace, y es lo importante

No toca la tabla de auditoria. Los AuditEvent son append-only (RN-05) y se
quedan donde estan: la muestra deja de listarse, pero su bitacora sigue
existiendo y sigue siendo verificable. Un borrado logico no puede convertirse en
una via para hacer desaparecer evidencia.

La restriccion de la tabla exige que is_active=False venga siempre con un
deleted_at, asi que se escriben los dos campos juntos.

Salida en ASCII puro (la consola de Windows rompe con Unicode).
"""
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = 'Desactiva o reactiva una muestra por su CHN, sin tocar la auditoria.'

    def add_arguments(self, parser):
        parser.add_argument('chn', help='codigo CHN de la muestra')
        parser.add_argument('--reactivar', action='store_true',
                            help='vuelve a activarla en vez de desactivarla')

    def handle(self, *args, **opts):
        from apps.samples.models import AuditEvent, Sample

        chn = opts['chn']
        muestra = Sample.objects.filter(chn_code=chn).first()
        if muestra is None:
            self.stderr.write(f'no existe la muestra {chn}')
            return

        eventos_antes = AuditEvent.objects.filter(sample=muestra).count()

        if opts['reactivar']:
            muestra.is_active = True
            muestra.deleted_at = None
        else:
            muestra.is_active = False
            muestra.deleted_at = timezone.now()
        muestra.save(update_fields=['is_active', 'deleted_at'])
        muestra.refresh_from_db()

        eventos_despues = AuditEvent.objects.filter(sample=muestra).count()
        self.stdout.write(
            f'{chn} -> is_active={muestra.is_active} deleted_at={muestra.deleted_at}')
        self.stdout.write(
            f'auditoria intacta: {eventos_despues} eventos (antes {eventos_antes}) '
            f'-- RN-05, no se borra nada')
