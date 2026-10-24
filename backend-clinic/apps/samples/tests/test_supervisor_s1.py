"""Tests del flujo del Supervisor S1 (ADR-0023 S1, DD-SUP-001).

Auditoría del 5% aleatorio determinista (RN-08) + decisiones + segregación
por permiso (RN-06, el Analista NO tiene case.audit).
"""
from decimal import Decimal

import pytest

from apps.samples.models import AuditEvent, AuditReview, Chromosome, Karyotype, Sample
from apps.samples.services import (
    InvalidDecisionError,
    NotAuditableError,
    audit_summary,
    decide_audit,
    select_audit_sample,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def validated_sample(analyst_user):
    """Caso validado por el analista con 40 verdes de alta confianza."""
    s = Sample.objects.create(
        chn_code='CHN-2026-07-24-S100', patient_ref='ANON-S1', analyst=analyst_user,
        status='ANALYST_VALIDATED',
    )
    k = Karyotype.objects.create(sample=s)
    for i in range(40):
        Chromosome.objects.create(
            karyotype=k, predicted_class=str((i % 22) + 1), position_index=i,
            confidence_score=Decimal('0.960'), order=i,
        )
    return s


def _review_url(s):
    return f'/api/clinic/samples/{s.id}/audit-review/'


def _decide_url(s, cid):
    return f'/api/clinic/samples/{s.id}/audit-review/{cid}/decide/'


class TestAuditSelection:
    def test_selects_five_percent_min_one(self, validated_sample):
        reviews = select_audit_sample(validated_sample)
        assert len(reviews) == 2  # ceil(0.05 * 40) = 2

    def test_selection_is_deterministic(self, validated_sample):
        first = {r.chromosome_id for r in select_audit_sample(validated_sample)}
        # Segundo acceso (idempotente): mismos cromosomas, sin duplicar.
        second = {r.chromosome_id for r in select_audit_sample(validated_sample)}
        assert first == second
        assert AuditReview.objects.filter(sample=validated_sample).count() == 2

    def test_pool_excludes_low_confidence(self, analyst_user):
        s = Sample.objects.create(chn_code='CHN-2026-07-24-S101', analyst=analyst_user, status='ANALYST_VALIDATED')
        k = Karyotype.objects.create(sample=s)
        # 1 alta (>0.86) + 3 bajas (naranja) → pool = 1 → 5% min 1 = 1.
        high = Chromosome.objects.create(karyotype=k, predicted_class='1', confidence_score=Decimal('0.960'), order=0)
        for i in range(3):
            Chromosome.objects.create(karyotype=k, predicted_class='2', confidence_score=Decimal('0.700'), order=i + 1)
        reviews = select_audit_sample(s)
        assert len(reviews) == 1
        assert reviews[0].chromosome_id == high.id

    def test_no_karyotype_returns_empty(self, analyst_user):
        s = Sample.objects.create(chn_code='CHN-2026-07-24-S102', analyst=analyst_user, status='ANALYST_VALIDATED')
        assert select_audit_sample(s) == []


class TestAuditDecision:
    def test_decide_confirms_and_emits_event(self, validated_sample, supervisor_user):
        review = select_audit_sample(validated_sample)[0]
        decide_audit(validated_sample, review, supervisor_user, 'CONFIRMED', 'ok')
        review.refresh_from_db()
        assert review.decision == 'CONFIRMED'
        assert review.reviewer_id == supervisor_user.id
        assert review.decided_at is not None
        assert AuditEvent.objects.filter(sample=validated_sample, event_type='AUDIT_DECISION').count() == 1

    def test_decide_invalid_rejected(self, validated_sample, supervisor_user):
        review = select_audit_sample(validated_sample)[0]
        with pytest.raises(InvalidDecisionError):
            decide_audit(validated_sample, review, supervisor_user, 'MAYBE')

    def test_decide_requires_analyst_validated(self, analyst_user, supervisor_user):
        s = Sample.objects.create(chn_code='CHN-2026-07-24-S103', analyst=analyst_user, status='READY')
        k = Karyotype.objects.create(sample=s)
        c = Chromosome.objects.create(karyotype=k, predicted_class='1', confidence_score=Decimal('0.96'), order=0)
        review = AuditReview.objects.create(sample=s, chromosome=c)
        with pytest.raises(NotAuditableError):
            decide_audit(s, review, supervisor_user, 'CONFIRMED')

    def test_summary_counts(self, validated_sample, supervisor_user):
        reviews = select_audit_sample(validated_sample)
        decide_audit(validated_sample, reviews[0], supervisor_user, 'CONFIRMED')
        summary = audit_summary(validated_sample)
        assert summary == {'total': 2, 'pending': 1, 'confirmed': 1, 'rejected': 0}


class TestAuditEndpoints:
    def test_supervisor_lists_selection(self, supervisor_client, validated_sample):
        resp = supervisor_client.get(_review_url(validated_sample))
        assert resp.status_code == 200
        assert len(resp.data['reviews']) == 2
        assert resp.data['summary']['total'] == 2
        assert resp.data['reviews'][0]['predicted_class']

    def test_supervisor_decides(self, supervisor_client, validated_sample):
        cid = supervisor_client.get(_review_url(validated_sample)).data['reviews'][0]['chromosome']
        resp = supervisor_client.post(_decide_url(validated_sample, cid), {'decision': 'REJECTED', 'comment': 'revisar'}, format='json')
        assert resp.status_code == 200
        assert resp.data['decision'] == 'REJECTED'

    def test_decide_unknown_chromosome_404(self, supervisor_client, validated_sample):
        select_audit_sample(validated_sample)
        resp = supervisor_client.post(
            _decide_url(validated_sample, '00000000-0000-0000-0000-000000000000'),
            {'decision': 'CONFIRMED'}, format='json',
        )
        assert resp.status_code == 404

    def test_analyst_forbidden_by_segregation(self, analyst_client, validated_sample):
        # RN-06: el Analista NO tiene case.audit → 403 aunque sea dueño.
        resp = analyst_client.get(_review_url(validated_sample))
        assert resp.status_code == 403

    def test_anonimo_401(self, api_client, validated_sample):
        resp = api_client.get(_review_url(validated_sample))
        assert resp.status_code == 401
