"""Tests del flujo P3 del cariotipo (ADR-0021 P3, DD-KARYO-003).

Cubre corrección manual: reclasificar (CORRECT_CLASS), separar (SPLIT), unir
(JOIN, soft-remove), resolver cruce (RESOLVE_CROSS), case-lock tras validación,
integridad de la cadena de audit y permisos.
"""
from decimal import Decimal

import pytest

from apps.samples.models import (
    AuditEvent,
    Chromosome,
    ChromosomeResolution,
    Karyotype,
    Sample,
)
from apps.samples.services import (
    CaseLockedError,
    InvalidClassError,
    JoinSelfError,
    SameClassError,
    join_chromosomes,
    reclassify_chromosome,
    resolve_cross,
    split_chromosome,
    validate_case,
    verify_audit_chain,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def own_sample(analyst_user):
    return Sample.objects.create(
        chn_code='CHN-2026-07-24-P300', patient_ref='ANON-P3', analyst=analyst_user, status='READY',
    )


@pytest.fixture
def other_sample(django_user_model):
    other = django_user_model.objects.create_user(username='otra_p3', password='x')
    return Sample.objects.create(chn_code='CHN-2026-07-24-P399', analyst=other, status='READY')


def _karyo(sample):
    """Cariotipo con un verde (par 1) y un naranja (par 18)."""
    k = Karyotype.objects.create(sample=sample)
    green = Chromosome.objects.create(
        karyotype=k, predicted_class='1', confidence_score=Decimal('0.96'),
        bbox={'x': 0, 'y': 0, 'w': 40, 'h': 96}, order=0,
    )
    orange = Chromosome.objects.create(
        karyotype=k, predicted_class='18', confidence_score=Decimal('0.72'),
        resolution_status=ChromosomeResolution.PENDING,
        bbox={'x': 100, 'y': 0, 'w': 40, 'h': 96}, order=1,
    )
    return k, green, orange


def _reclassify_url(s, c): return f'/api/clinic/samples/{s.id}/chromosomes/{c.id}/reclassify/'
def _split_url(s, c): return f'/api/clinic/samples/{s.id}/chromosomes/{c.id}/split/'
def _join_url(s, c): return f'/api/clinic/samples/{s.id}/chromosomes/{c.id}/join/'
def _cross_url(s, c): return f'/api/clinic/samples/{s.id}/chromosomes/{c.id}/cross/'


# ============================================================================
# Servicios de dominio
# ============================================================================
class TestReclassify:
    def test_reclassify_changes_class_and_resolves(self, own_sample, analyst_user):
        _, _, orange = _karyo(own_sample)
        reclassify_chromosome(own_sample, orange, '7', analyst_user)
        orange.refresh_from_db()
        assert orange.predicted_class == '7'
        assert orange.resolution_status == 'RESOLVED'
        ev = AuditEvent.objects.get(sample=own_sample, event_type='CORRECT_CLASS')
        assert ev.payload == {'from': '18', 'to': '7'}

    def test_reclassify_invalid_class_rejected(self, own_sample, analyst_user):
        _, green, _ = _karyo(own_sample)
        with pytest.raises(InvalidClassError):
            reclassify_chromosome(own_sample, green, '99', analyst_user)

    def test_reclassify_same_class_rejected(self, own_sample, analyst_user):
        _, green, _ = _karyo(own_sample)
        with pytest.raises(SameClassError):
            reclassify_chromosome(own_sample, green, '1', analyst_user)

    def test_reclassify_unblocks_case(self, own_sample, analyst_user):
        """Reclasificar un naranja lo marca RESOLVED → deja de bloquear."""
        _, _, orange = _karyo(own_sample)
        reclassify_chromosome(own_sample, orange, 'X', analyst_user)
        s = validate_case(own_sample, analyst_user)
        assert s.status == 'ANALYST_VALIDATED'


class TestSplit:
    def test_split_creates_second_chromosome(self, own_sample, analyst_user):
        k, green, _ = _karyo(own_sample)
        before = k.chromosomes.filter(is_active=True).count()
        created = split_chromosome(own_sample, green, analyst_user)
        assert k.chromosomes.filter(is_active=True).count() == before + 1
        assert created.predicted_class == '1'
        # bbox partido a la mitad: original izquierda, nuevo derecha.
        green.refresh_from_db()
        assert green.bbox['w'] == 20
        assert created.bbox['x'] == 20 and created.bbox['w'] == 20
        assert AuditEvent.objects.filter(sample=own_sample, event_type='SPLIT').count() == 1

    def test_split_new_index_is_next(self, own_sample, analyst_user):
        _, green, _ = _karyo(own_sample)
        created = split_chromosome(own_sample, green, analyst_user)
        assert created.position_index == green.position_index + 1


class TestJoin:
    def test_join_absorbs_and_unions_bbox(self, own_sample, analyst_user):
        _, green, orange = _karyo(own_sample)
        keep = join_chromosomes(own_sample, green, orange, analyst_user)
        orange.refresh_from_db()
        assert orange.is_active is False
        # unión de {0..40} y {100..140} → x=0, w=140.
        assert keep.bbox == {'x': 0, 'y': 0, 'w': 140, 'h': 96}
        assert AuditEvent.objects.filter(sample=own_sample, event_type='JOIN').count() == 1

    def test_join_self_rejected(self, own_sample, analyst_user):
        _, green, _ = _karyo(own_sample)
        with pytest.raises(JoinSelfError):
            join_chromosomes(own_sample, green, green, analyst_user)

    def test_joined_chromosome_excluded_from_summary(self, analyst_client, own_sample, analyst_user):
        _, green, orange = _karyo(own_sample)
        join_chromosomes(own_sample, green, orange, analyst_user)
        resp = analyst_client.get(f'/api/clinic/samples/{own_sample.id}/karyotype/')
        ids = [c['id'] for c in resp.data['chromosomes']]
        assert str(orange.id) not in ids
        assert resp.data['summary']['total'] == 1


class TestCross:
    def test_resolve_cross_marks_resolved(self, own_sample, analyst_user):
        _, _, orange = _karyo(own_sample)
        resolve_cross(own_sample, orange, analyst_user)
        orange.refresh_from_db()
        assert orange.resolution_status == 'RESOLVED'
        assert AuditEvent.objects.filter(sample=own_sample, event_type='RESOLVE_CROSS').count() == 1


class TestCaseLock:
    def test_edits_blocked_after_validation(self, own_sample, analyst_user):
        _, green, orange = _karyo(own_sample)
        reclassify_chromosome(own_sample, orange, 'X', analyst_user)  # resuelve el naranja
        validate_case(own_sample, analyst_user)
        with pytest.raises(CaseLockedError):
            reclassify_chromosome(own_sample, green, '7', analyst_user)
        with pytest.raises(CaseLockedError):
            split_chromosome(own_sample, green, analyst_user)

    def test_audit_chain_intact_after_p3_ops(self, own_sample, analyst_user):
        _, green, orange = _karyo(own_sample)
        reclassify_chromosome(own_sample, orange, '7', analyst_user)
        split_chromosome(own_sample, green, analyst_user)
        resolve_cross(own_sample, orange, analyst_user)
        assert verify_audit_chain(own_sample) is True


# ============================================================================
# Endpoints
# ============================================================================
class TestP3Endpoints:
    def test_reclassify_endpoint(self, analyst_client, own_sample):
        _, _, orange = _karyo(own_sample)
        resp = analyst_client.post(_reclassify_url(own_sample, orange), {'target_class': '7'}, format='json')
        assert resp.status_code == 200
        assert resp.data['predicted_class'] == '7'
        assert resp.data['resolution_status'] == 'RESOLVED'

    def test_reclassify_invalid_400(self, analyst_client, own_sample):
        _, green, _ = _karyo(own_sample)
        resp = analyst_client.post(_reclassify_url(own_sample, green), {'target_class': 'ZZ'}, format='json')
        assert resp.status_code == 400
        assert resp.data['code'] == 'INVALID_CLASS'

    def test_reclassify_same_400(self, analyst_client, own_sample):
        _, green, _ = _karyo(own_sample)
        resp = analyst_client.post(_reclassify_url(own_sample, green), {'target_class': '1'}, format='json')
        assert resp.status_code == 400
        assert resp.data['code'] == 'SAME_CLASS'

    def test_split_endpoint_201(self, analyst_client, own_sample):
        _, green, _ = _karyo(own_sample)
        resp = analyst_client.post(_split_url(own_sample, green))
        assert resp.status_code == 201
        assert resp.data['predicted_class'] == '1'

    def test_join_endpoint(self, analyst_client, own_sample):
        _, green, orange = _karyo(own_sample)
        resp = analyst_client.post(_join_url(own_sample, green), {'other_id': str(orange.id)}, format='json')
        assert resp.status_code == 200
        orange.refresh_from_db()
        assert orange.is_active is False

    def test_join_self_400(self, analyst_client, own_sample):
        _, green, _ = _karyo(own_sample)
        resp = analyst_client.post(_join_url(own_sample, green), {'other_id': str(green.id)}, format='json')
        assert resp.status_code == 400
        assert resp.data['code'] == 'JOIN_SELF'

    def test_join_other_not_found_404(self, analyst_client, own_sample):
        _, green, _ = _karyo(own_sample)
        resp = analyst_client.post(
            _join_url(own_sample, green),
            {'other_id': '00000000-0000-0000-0000-000000000000'}, format='json',
        )
        assert resp.status_code == 404

    def test_cross_endpoint(self, analyst_client, own_sample):
        _, _, orange = _karyo(own_sample)
        resp = analyst_client.post(_cross_url(own_sample, orange))
        assert resp.status_code == 200
        assert resp.data['resolution_status'] == 'RESOLVED'

    def test_case_locked_409(self, analyst_client, own_sample, analyst_user):
        _, green, orange = _karyo(own_sample)
        reclassify_chromosome(own_sample, orange, 'X', analyst_user)
        validate_case(own_sample, analyst_user)
        resp = analyst_client.post(_split_url(own_sample, green))
        assert resp.status_code == 409
        assert resp.data['code'] == 'CASE_LOCKED'

    def test_analista_ajena_403(self, analyst_client, other_sample):
        _, green, _ = _karyo(other_sample)
        resp = analyst_client.post(_split_url(other_sample, green))
        assert resp.status_code == 403

    def test_anonimo_401(self, api_client, own_sample):
        _, green, _ = _karyo(own_sample)
        resp = api_client.post(_split_url(own_sample, green))
        assert resp.status_code == 401
