"""Tests del flujo P4 del cariotipo (ADR-0021 P4, DD-KARYO-004).

Cubre el modo degradado (FSD-UC-007): flag mode='degradado' en el audit trail
vía el header X-Biomed-Mode, endpoint de salud del pipeline, e integridad de la
cadena de hash con el nuevo campo `mode`.
"""
import time
from decimal import Decimal

import pytest

from apps.samples.models import AuditEvent, Chromosome, ChromosomeResolution, Karyotype, Sample
from apps.samples.pipeline_client import pipeline_client
from apps.samples.services import emit_audit_event, reclassify_chromosome, verify_audit_chain
from apps.samples.models import AuditEventType

pytestmark = pytest.mark.django_db


@pytest.fixture
def own_sample(analyst_user):
    return Sample.objects.create(
        chn_code='CHN-2026-07-24-P400', patient_ref='ANON-P4', analyst=analyst_user, status='READY',
    )


def _karyo(sample):
    k = Karyotype.objects.create(sample=sample)
    orange = Chromosome.objects.create(
        karyotype=k, predicted_class='18', confidence_score=Decimal('0.72'),
        resolution_status=ChromosomeResolution.PENDING, order=0,
    )
    return k, orange


def _reclassify_url(s, c):
    return f'/api/clinic/samples/{s.id}/chromosomes/{c.id}/reclassify/'


HEALTH_URL = '/api/clinic/pipeline/health/'


# ============================================================================
# Flag de modo en el audit trail
# ============================================================================
class TestDegradedMode:
    def test_service_records_mode_degradado(self, own_sample, analyst_user):
        _, orange = _karyo(own_sample)
        reclassify_chromosome(own_sample, orange, '7', analyst_user, mode='degradado')
        ev = AuditEvent.objects.get(sample=own_sample, event_type='CORRECT_CLASS')
        assert ev.mode == 'degradado'

    def test_service_defaults_to_auto(self, own_sample, analyst_user):
        ev = emit_audit_event(own_sample, analyst_user, AuditEventType.XAI_VIEWED)
        assert ev.mode == 'auto'

    def test_header_marks_event_degradado(self, analyst_client, own_sample):
        _, orange = _karyo(own_sample)
        resp = analyst_client.post(
            _reclassify_url(own_sample, orange), {'target_class': '7'}, format='json',
            HTTP_X_BIOMED_MODE='degradado',
        )
        assert resp.status_code == 200
        ev = AuditEvent.objects.get(sample=own_sample, event_type='CORRECT_CLASS')
        assert ev.mode == 'degradado'

    def test_no_header_defaults_auto(self, analyst_client, own_sample):
        _, orange = _karyo(own_sample)
        analyst_client.post(_reclassify_url(own_sample, orange), {'target_class': '7'}, format='json')
        ev = AuditEvent.objects.get(sample=own_sample, event_type='CORRECT_CLASS')
        assert ev.mode == 'auto'

    def test_mode_is_part_of_hash_chain(self, own_sample, analyst_user):
        emit_audit_event(own_sample, analyst_user, AuditEventType.XAI_VIEWED, mode='degradado')
        emit_audit_event(own_sample, analyst_user, AuditEventType.MARK_ANOMALY, mode='auto')
        assert verify_audit_chain(own_sample) is True

    def test_mode_exposed_in_serializer(self, analyst_client, own_sample):
        _, orange = _karyo(own_sample)
        analyst_client.post(
            _reclassify_url(own_sample, orange), {'target_class': '7'}, format='json',
            HTTP_X_BIOMED_MODE='degradado',
        )
        resp = analyst_client.get(f'/api/clinic/samples/{own_sample.id}/audit/')
        assert resp.status_code == 200
        assert resp.data[0]['mode'] == 'degradado'


# ============================================================================
# Endpoint de salud del pipeline (FSD-UC-007 §8)
# ============================================================================
class TestPipelineHealth:
    def test_health_available_when_circuit_closed(self, analyst_client):
        pipeline_client._circuit_open_until = 0.0
        resp = analyst_client.get(HEALTH_URL)
        assert resp.status_code == 200
        assert resp.data == {'available': True, 'mode': 'auto'}

    def test_health_degraded_when_circuit_open(self, analyst_client):
        pipeline_client._circuit_open_until = time.time() + 60
        try:
            resp = analyst_client.get(HEALTH_URL)
            assert resp.status_code == 200
            assert resp.data == {'available': False, 'mode': 'degradado'}
        finally:
            pipeline_client._circuit_open_until = 0.0

    def test_health_requires_auth(self, api_client):
        resp = api_client.get(HEALTH_URL)
        assert resp.status_code == 401
