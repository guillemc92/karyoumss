"""Demo de la integración con el LLM (ADR-0024) — para la entrega del módulo de IA.

Muestra el peldaño 0 completo: una función que manda un prompt a un modelo de
lenguaje y recibe la respuesta, **con el prompt construido desde datos reales de
la aplicación** (un caso clínico de la base, no un texto de ejemplo).

    python manage.py demo_llm                    # usa un caso de la base
    python manage.py demo_llm --iscn 47,XY,+21   # fuerza un ISCN concreto
    python manage.py demo_llm --sin-guardar      # no persiste (solo muestra)

No imprime ninguna credencial: Ollama corre en localhost y no usa API key. Si en
el futuro se apunta a un proveedor de pago, la clave vive en el .env (gitignored)
y este comando sigue sin mostrarla.
"""
import time

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.samples.iscn import IscnError, generate_iscn
from apps.samples.llm_client import LlmServiceError, llm_client
from apps.samples.models import Chromosome, Karyotype, Sample
from apps.samples.services import generate_narrative


class Command(BaseCommand):
    help = 'Demuestra la llamada al LLM local con datos reales de la app (ADR-0024)'

    def add_arguments(self, parser):
        parser.add_argument('--iscn', default='', help='ISCN a narrar (por defecto se deriva del caso)')
        parser.add_argument('--chn', default='', help='código CHN del caso a usar')
        parser.add_argument('--sin-guardar', action='store_true', help='no persistir el borrador')

    def handle(self, *args, **opts):
        línea = '=' * 72
        self.stdout.write(línea)
        self.stdout.write('DEMO — Integración con LLM (ADR-0024)  |  BIOMED UMSS')
        self.stdout.write(línea)

        # --- 1. Configuración (sin secretos: Ollama local no usa API key) ---
        self.stdout.write('\n[1] Proveedor y modelo')
        self.stdout.write(f'    proveedor : Ollama (local, API compatible con el SDK de OpenAI)')
        self.stdout.write(f'    endpoint  : {settings.CLINIC_LLM_URL}')
        self.stdout.write(f'    modelo    : {settings.CLINIC_LLM_MODEL}')
        self.stdout.write(f'    habilitado: {settings.CLINIC_LLM_ENABLED}')
        if not settings.CLINIC_LLM_ENABLED:
            self.stdout.write(self.style.WARNING(
                '\n    El LLM está apagado. Activalo con CLINIC_LLM_ENABLED=true en el .env'))
            return

        # --- 2. Dato REAL de la aplicación (no un prompt de ejemplo) ---
        self.stdout.write('\n[2] Dato real de la aplicación')
        sample = (Sample.objects.filter(chn_code=opts['chn']).first() if opts['chn']
                  else Sample.objects.order_by('-created_at').first())
        if sample is None:
            self.stdout.write(self.style.ERROR(
                '    No hay muestras en la base. Corré: python manage.py seed_karyotype'))
            return

        counts = {}
        karyotype = Karyotype.objects.filter(sample=sample).first()
        if karyotype:
            for chromo in Chromosome.objects.filter(karyotype=karyotype, is_active=True):
                if chromo.predicted_class:
                    counts[chromo.predicted_class] = counts.get(chromo.predicted_class, 0) + 1

        # El ISCN sale del motor determinístico (S3, ADR-0025): del campo ya
        # persistido si el caso llegó a REPORTED, o calculado en el momento
        # sobre el mismo conteo. Nunca del LLM (ADR-0024 D1).
        if opts['iscn']:
            iscn, origen = opts['iscn'], 'forzado por --iscn'
        elif sample.iscn_nomenclature:
            iscn, origen = sample.iscn_nomenclature, 'campo persistido del caso (S3)'
        else:
            try:
                iscn, origen = generate_iscn(counts), 'calculado por generate_iscn()'
            except IscnError as exc:
                iscn, origen = '', f'no derivable: {exc}'

        self.stdout.write(f'    caso (CHN)  : {sample.chn_code}')
        self.stdout.write(f'    tipo muestra: {sample.sample_type or "no especificado"}')
        self.stdout.write(f'    cromosomas  : {sum(counts.values())} activos')
        self.stdout.write(f'    ISCN        : {iscn or "(sin ISCN)"}')
        self.stdout.write(f'    origen ISCN : {origen}')
        self.stdout.write(
            '    (lo calcula una función pura determinística, NO el LLM — ADR-0024 D1)')

        # --- 3. La llamada ---
        self.stdout.write('\n[3] Llamando al modelo...')
        self.stdout.write('    (en CPU sin GPU tarda 1-3 min; es normal)')
        t0 = time.time()

        if opts['sin_guardar']:
            try:
                r = llm_client.generate_narrative(
                    iscn=iscn,
                    sample_type=sample.sample_type or 'no especificado',
                    chn_code=sample.chn_code,
                    counts=counts,
                )
                resultado = {'generated': True, 'text': r['text']}
                tokens, latencia = r['tokens'], r['latency_ms']
            except LlmServiceError as exc:
                resultado, tokens, latencia = {'generated': False, 'reason': str(exc)}, 0, 0
        else:
            actor = sample.analyst
            resultado = generate_narrative(sample, actor, iscn)
            sample.refresh_from_db()
            tokens, latencia = 0, int((time.time() - t0) * 1000)

        # --- 4. Respuesta ---
        self.stdout.write('\n[4] Respuesta del modelo')
        if not resultado['generated']:
            self.stdout.write(self.style.WARNING(f'    Sin narrativa: {resultado["reason"]}'))
            self.stdout.write('    El informe se emite igual — la narrativa nunca bloquea (RN-07).')
            return

        self.stdout.write('-' * 72)
        for l in self._envolver(resultado['text'], 70):
            self.stdout.write(f'  {l}')
        self.stdout.write('-' * 72)
        if tokens:
            self.stdout.write(f'    tokens: {tokens}  |  latencia: {latencia} ms')
        else:
            self.stdout.write(f'    latencia total: {latencia} ms')

        if not opts['sin_guardar']:
            self.stdout.write('\n[5] Persistencia y auditoría')
            self.stdout.write(f'    Sample.narrative_draft : {len(sample.narrative_draft)} chars')
            self.stdout.write(f'    Sample.narrative_model : {sample.narrative_model}')
            ev = sample.audit_events.filter(event_type='NARRATIVE_GENERATED').last()
            if ev:
                self.stdout.write(f'    AuditEvent             : {ev.event_type}')
                self.stdout.write(f'    hash encadenado        : {ev.current_hash[:32]}...')

        self.stdout.write(self.style.SUCCESS('\nOK — llamada al LLM completada.\n'))

    @staticmethod
    def _envolver(texto: str, ancho: int) -> list[str]:
        palabras, líneas, actual = texto.split(), [], ''
        for p in palabras:
            if len(actual) + len(p) + 1 > ancho:
                líneas.append(actual)
                actual = p
            else:
                actual = f'{actual} {p}'.strip()
        if actual:
            líneas.append(actual)
        return líneas
