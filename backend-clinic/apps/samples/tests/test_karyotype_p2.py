"""Tests del flujo P2 del cariotipo (ADR-0021 P2, ADR-0022, DD-KARYO-002).

Cubre: audit trail append-only + hash chain, XAI, resolución con gate BR-004,
marcar anomalía, validación con gating RN-01, permisos.
"""
from decimal import Decimal

import pytest

from apps.samples.models import (
    AuditEvent,
    AuditEventError,
    AuditEventType,
    Chromosome,
    ChromosomeResolution,
    Karyotype,
    Sample,
)
from apps.samples.services import (
    CaseBlockedError,
    NotOrangeError,
    XaiRequiredError,
    emit_audit_event,
    mark_anomaly,
    resolve_chromosome,
    validate_case,
    verify_audit_chain,
    view_xai,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def own_sample(analyst_user):
    return Sample.objects.create(chn_code='CHN-2026-07-23-P200', patient_ref='ANON-P2', analyst=analyst_user, status='READY')


@pytest.fixture
def other_sample(django_user_model):
    other = django_user_model.objects.create_user(username='otra_p2', password='x')
    return Sample.objects.create(chn_code='CHN-2026-07-23-P299', analyst=other, status='READY')


def _karyo_with_orange(sample):
    k = Karyotype.objects.create(sample=sample)
    green = Chromosome.objects.create(karyotype=k, predicted_class='1', confidence_score=Decimal('0.96'), order=0)
    orange = Chromosome.objects.create(
        karyotype=k, predicted_class='18', confidence_score=Decimal('0.72'),
        resolution_status=ChromosomeResolution.PENDING, order=1,
    )
    return k, green, orange


def _xai_url(s, c): return f'/api/clinic/samples/{s.id}/chromosomes/{c.id}/xai/'
def _resolve_url(s, c): return f'/api/clinic/samples/{s.id}/chromosomes/{c.id}/resolve/'
def _anomaly_url(s, c): return f'/api/clinic/samples/{s.id}/chromosomes/{c.id}/anomaly/'
def _validate_url(s): return f'/api/clinic/samples/{s.id}/validate/'
def _audit_url(s): return f'/api/clinic/samples/{s.id}/audit/'


# ============================================================================
# Audit trail (ADR-0022)
# ============================================================================
class TestAuditTrail:
    def test_hash_chain_links_events(self, own_sample, analyst_user):
        e1 = emit_audit_event(own_sample, analyst_user, AuditEventType.XAI_VIEWED)
        e2 = emit_audit_event(own_sample, analyst_user, AuditEventType.ANALYST_VALIDATED)
        assert e1.previous_hash == ''
        assert e1.current_hash != ''
        assert e2.previous_hash == e1.current_hash
        assert e2.current_hash != e1.current_hash

    def test_verify_chain_true_when_intact(self, own_sample, analyst_user):
        emit_audit_event(own_sample, analyst_user, AuditEventType.XAI_VIEWED)
        emit_audit_event(own_sample, analyst_user, AuditEventType.ANALYST_VALIDATED)
        assert verify_audit_chain(own_sample) is True

    def test_verify_chain_false_when_tampered_in_db(self, own_sample, analyst_user):
        emit_audit_event(own_sample, analyst_user, AuditEventType.XAI_VIEWED)
        ev = emit_audit_event(own_sample, analyst_user, AuditEventType.MARK_ANOMALY)
        # Manipular saltando el save() append-only (UPDATE crudo en DB).
        AuditEvent.objects.filter(id=ev.id).update(payload={'tampered': True})
        assert verify_audit_chain(own_sample) is False

    def test_append_only_blocks_update(self, own_sample, analyst_user):
        ev = emit_audit_event(own_sample, analyst_user, AuditEventType.XAI_VIEWED)
        ev.payload = {'hacked': True}
        with pytest.raises(AuditEventError):
            ev.save()

    def test_chain_is_per_sample(self, own_sample, other_sample, analyst_user):
        e_a = emit_audit_event(own_sample, analyst_user, AuditEventType.XAI_VIEWED)
        e_b = emit_audit_event(other_sample, analyst_user, AuditEventType.XAI_VIEWED)
        # Cadenas independientes: ambas arrancan en ''.
        assert e_a.previous_hash == ''
        assert e_b.previous_hash == ''


# ============================================================================
# Servicios de dominio
# ============================================================================
class TestKaryotypeP2Services:
    def test_view_xai_sets_flag_and_emits(self, own_sample, analyst_user):
        _, _, orange = _karyo_with_orange(own_sample)
        assert orange.xai_viewed is False
        view_xai(own_sample, orange, analyst_user)
        orange.refresh_from_db()
        assert orange.xai_viewed is True
        assert AuditEvent.objects.filter(sample=own_sample, event_type='XAI_VIEWED').count() == 1

    def test_resolve_requires_xai(self, own_sample, analyst_user):
        _, _, orange = _karyo_with_orange(own_sample)
        with pytest.raises(XaiRequiredError):
            resolve_chromosome(own_sample, orange, analyst_user)

    def test_resolve_after_xai_succeeds(self, own_sample, analyst_user):
        _, _, orange = _karyo_with_orange(own_sample)
        view_xai(own_sample, orange, analyst_user)
        orange.refresh_from_db()
        resolve_chromosome(own_sample, orange, analyst_user)
        orange.refresh_from_db()
        assert orange.resolution_status == 'RESOLVED'
        assert AuditEvent.objects.filter(sample=own_sample, event_type='ACCEPT_CHROMOSOME').count() == 1

    def test_resolve_non_orange_rejected(self, own_sample, analyst_user):
        _, green, _ = _karyo_with_orange(own_sample)
        with pytest.raises(NotOrangeError):
            resolve_chromosome(own_sample, green, analyst_user)

    def test_mark_anomaly(self, own_sample, analyst_user):
        _, _, orange = _karyo_with_orange(own_sample)
        mark_anomaly(own_sample, orange, analyst_user)
        orange.refresh_from_db()
        assert orange.is_anomaly is True
        assert AuditEvent.objects.filter(sample=own_sample, event_type='MARK_ANOMALY').count() == 1

    def test_validate_blocked_with_pending_orange(self, own_sample, analyst_user):
        _karyo_with_orange(own_sample)
        with pytest.raises(CaseBlockedError):
            validate_case(own_sample, analyst_user)

    def test_validate_succeeds_when_all_resolved(self, own_sample, analyst_user):
        _, _, orange = _karyo_with_orange(own_sample)
        view_xai(own_sample, orange, analyst_user)
        orange.refresh_from_db()
        resolve_chromosome(own_sample, orange, analyst_user)
        s = validate_case(own_sample, analyst_user)
        assert s.status == 'ANALYST_VALIDATED'
        assert AuditEvent.objects.filter(sample=own_sample, event_type='ANALYST_VALIDATED').count() == 1

    def test_validate_without_karyotype_blocked(self, own_sample, analyst_user):
        with pytest.raises(CaseBlockedError):
            validate_case(own_sample, analyst_user)


# ============================================================================
# Endpoints
# ============================================================================
class TestKaryotypeP2Endpoints:
    def test_xai_declara_si_hay_explicacion_o_por_que_no(self, analyst_client, own_sample):
        """El contrato es `xai_disponible`, no que siempre haya mapa.

        Antes se devolvía un PNG de 1x1 fijo, así que el test podía exigir
        `heatmap_base64` siempre. Ahora el mapa lo produce Grad-CAM real en
        backend-ml: si el cromosoma no tiene bbox, o el servicio no responde,
        **se dice** en vez de devolver una imagen que aparente ser una
        explicación. Un XAI falso es peor que ninguno, porque el gate BR-004
        obliga al analista a mirarlo antes de resolver.
        """
        _, _, orange = _karyo_with_orange(own_sample)

        resp = analyst_client.post(_xai_url(own_sample, orange))

        assert resp.status_code == 200
        assert 'xai_disponible' in resp.data
        if resp.data['xai_disponible']:
            assert resp.data.get('heatmap_base64')
            assert resp.data.get('metodo') == 'grad-cam'
        else:
            # Si no hay explicación, hay motivo. Nunca las dos cosas vacías.
            assert resp.data.get('motivo')
            assert 'heatmap_base64' not in resp.data

    def test_xai_marca_el_cromosoma_aunque_no_haya_mapa(self, analyst_client, own_sample):
        """El gate BR-004 tiene que poder cumplirse con el servicio caído.

        Si una caída de infraestructura impidiera marcar el cromosoma como
        visto, bloquearía la validación clínica de todos los casos — justo lo
        que RN-07 prohíbe.
        """
        _, _, orange = _karyo_with_orange(own_sample)

        analyst_client.post(_xai_url(own_sample, orange))

        orange.refresh_from_db()
        assert orange.xai_viewed is True

    def test_resolve_without_xai_returns_409(self, analyst_client, own_sample):
        _, _, orange = _karyo_with_orange(own_sample)
        resp = analyst_client.post(_resolve_url(own_sample, orange))
        assert resp.status_code == 409
        assert resp.data['code'] == 'XAI_REQUIRED'

    def test_resolve_after_xai_returns_200(self, analyst_client, own_sample):
        _, _, orange = _karyo_with_orange(own_sample)
        analyst_client.post(_xai_url(own_sample, orange))
        resp = analyst_client.post(_resolve_url(own_sample, orange))
        assert resp.status_code == 200
        assert resp.data['resolution_status'] == 'RESOLVED'

    def test_resolve_green_returns_400(self, analyst_client, own_sample):
        _, green, _ = _karyo_with_orange(own_sample)
        resp = analyst_client.post(_resolve_url(own_sample, green))
        assert resp.status_code == 400
        assert resp.data['code'] == 'NOT_ORANGE'

    def test_anomaly_endpoint(self, analyst_client, own_sample):
        _, _, orange = _karyo_with_orange(own_sample)
        resp = analyst_client.post(_anomaly_url(own_sample, orange))
        assert resp.status_code == 200
        assert resp.data['is_anomaly'] is True

    def test_validate_blocked_returns_409(self, analyst_client, own_sample):
        _karyo_with_orange(own_sample)
        resp = analyst_client.post(_validate_url(own_sample))
        assert resp.status_code == 409
        assert resp.data['code'] == 'CASE_BLOCKED'

    def test_validate_success(self, analyst_client, own_sample):
        _, _, orange = _karyo_with_orange(own_sample)
        analyst_client.post(_xai_url(own_sample, orange))
        analyst_client.post(_resolve_url(own_sample, orange))
        resp = analyst_client.post(_validate_url(own_sample))
        assert resp.status_code == 200
        assert resp.data['status'] == 'ANALYST_VALIDATED'

    def test_audit_endpoint_lists_events(self, analyst_client, own_sample):
        _, _, orange = _karyo_with_orange(own_sample)
        analyst_client.post(_xai_url(own_sample, orange))
        resp = analyst_client.get(_audit_url(own_sample))
        assert resp.status_code == 200
        assert len(resp.data) == 1
        assert resp.data[0]['event_type'] == 'XAI_VIEWED'
        assert resp.data[0]['current_hash']

    def test_chromosome_not_found_404(self, analyst_client, own_sample):
        Karyotype.objects.create(sample=own_sample)
        resp = analyst_client.post(
            f'/api/clinic/samples/{own_sample.id}/chromosomes/00000000-0000-0000-0000-000000000000/xai/'
        )
        assert resp.status_code == 404
        assert resp.data['code'] == 'CHROMOSOME_NOT_FOUND'

    def test_analista_no_ajena_403(self, analyst_client, other_sample):
        _, _, orange = _karyo_with_orange(other_sample)
        resp = analyst_client.post(_xai_url(other_sample, orange))
        assert resp.status_code == 403

    def test_anonimo_401(self, api_client, own_sample):
        resp = api_client.get(_audit_url(own_sample))
        assert resp.status_code == 401
