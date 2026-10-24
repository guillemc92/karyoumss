"""Tests del visor de cariotipo P1 (ADR-0021, DD-KARYO-001).

Cubre RN-09 ≥90% de: modelo Chromosome.semaphore, KaryotypeSerializer
(summary derivado), KaryotypeView (200/404/403/401).
"""
from decimal import Decimal

import pytest

from apps.samples.models import (
    Chromosome,
    ChromosomeResolution,
    Karyotype,
    Sample,
)
from apps.samples.serializers import KaryotypeSerializer

pytestmark = pytest.mark.django_db


def _karyotype_url(sample):
    return f'/api/clinic/samples/{sample.id}/karyotype/'


@pytest.fixture
def own_sample(analyst_user):
    return Sample.objects.create(chn_code='CHN-2026-07-23-0001', patient_ref='ANON-K1', analyst=analyst_user)


@pytest.fixture
def other_sample(django_user_model):
    other = django_user_model.objects.create_user(username='otra_analista', password='x')
    return Sample.objects.create(chn_code='CHN-2026-07-23-0002', patient_ref='ANON-K2', analyst=other)


def _add_chromosome(karyotype, label, conf, resolution=ChromosomeResolution.AUTO, order=0):
    return Chromosome.objects.create(
        karyotype=karyotype, predicted_class=label, position_index=0,
        confidence_score=conf, resolution_status=resolution, order=order,
    )


# ============================================================================
# Modelo: semaforización derivada (RN-02)
# ============================================================================
class TestChromosomeSemaphore:
    def test_green_above_threshold(self, own_sample):
        k = Karyotype.objects.create(sample=own_sample)
        assert _add_chromosome(k, '1', Decimal('0.960')).semaphore == 'green'

    def test_green_exactly_at_threshold(self, own_sample):
        """Borde exacto 0.850 → verde (>=, no >)."""
        k = Karyotype.objects.create(sample=own_sample)
        assert _add_chromosome(k, '2', Decimal('0.850')).semaphore == 'green'

    def test_orange_below_threshold(self, own_sample):
        k = Karyotype.objects.create(sample=own_sample)
        assert _add_chromosome(k, '18', Decimal('0.720')).semaphore == 'orange'

    def test_orange_just_below_threshold(self, own_sample):
        k = Karyotype.objects.create(sample=own_sample)
        assert _add_chromosome(k, '13', Decimal('0.849')).semaphore == 'orange'

    def test_red_when_confidence_null(self, own_sample):
        k = Karyotype.objects.create(sample=own_sample)
        assert _add_chromosome(k, '21', None).semaphore == 'red'

    def test_str_representations(self, own_sample):
        k = Karyotype.objects.create(sample=own_sample)
        assert own_sample.chn_code in str(k)
        chromo = _add_chromosome(k, '7', Decimal('0.90'))
        assert '7' in str(chromo)


# ============================================================================
# Serializer: summary derivado
# ============================================================================
class TestKaryotypeSerializer:
    def test_summary_counts(self, own_sample):
        k = Karyotype.objects.create(sample=own_sample)
        _add_chromosome(k, '1', Decimal('0.96'), order=0)
        _add_chromosome(k, '2', Decimal('0.90'), order=1)
        _add_chromosome(k, '18', Decimal('0.72'), ChromosomeResolution.PENDING, order=2)
        _add_chromosome(k, '5', Decimal('0.80'), ChromosomeResolution.PENDING, order=3)
        _add_chromosome(k, '21', None, order=4)

        summary = KaryotypeSerializer(k).data['summary']
        assert summary['total'] == 5
        assert summary['green'] == 2
        assert summary['orange'] == 2
        assert summary['red'] == 1
        assert summary['unresolved_orange'] == 2
        assert summary['is_blocked'] is True

    def test_resolved_orange_not_counted_as_unresolved(self, own_sample):
        k = Karyotype.objects.create(sample=own_sample)
        _add_chromosome(k, '18', Decimal('0.72'), ChromosomeResolution.RESOLVED, order=0)
        summary = KaryotypeSerializer(k).data['summary']
        assert summary['orange'] == 1
        assert summary['unresolved_orange'] == 0

    def test_not_blocked_when_all_green(self, own_sample):
        k = Karyotype.objects.create(sample=own_sample)
        _add_chromosome(k, '1', Decimal('0.96'), order=0)
        _add_chromosome(k, '2', Decimal('0.95'), order=1)
        summary = KaryotypeSerializer(k).data['summary']
        assert summary['is_blocked'] is False
        assert summary['unresolved_orange'] == 0

    def test_serializer_exposes_semaphore_and_sample_id(self, own_sample):
        k = Karyotype.objects.create(sample=own_sample)
        _add_chromosome(k, '18', Decimal('0.72'), ChromosomeResolution.PENDING, order=0)
        data = KaryotypeSerializer(k).data
        assert str(data['sample_id']) == str(own_sample.id)
        assert data['chromosomes'][0]['semaphore'] == 'orange'
        assert data['chromosomes'][0]['predicted_class'] == '18'


# ============================================================================
# Endpoint: GET /samples/{id}/karyotype/
# ============================================================================
class TestKaryotypeView:
    def test_analista_ve_propio_200(self, analyst_client, own_sample):
        k = Karyotype.objects.create(sample=own_sample)
        _add_chromosome(k, '1', Decimal('0.96'), order=0)
        resp = analyst_client.get(_karyotype_url(own_sample))
        assert resp.status_code == 200
        assert resp.data['summary']['total'] == 1
        assert len(resp.data['chromosomes']) == 1

    def test_sin_cariotipo_404(self, analyst_client, own_sample):
        resp = analyst_client.get(_karyotype_url(own_sample))
        assert resp.status_code == 404
        assert resp.data['code'] == 'NO_KARYOTYPE'

    def test_analista_no_ve_ajena_403(self, analyst_client, other_sample):
        Karyotype.objects.create(sample=other_sample)
        resp = analyst_client.get(_karyotype_url(other_sample))
        assert resp.status_code == 403
        assert resp.data['code'] == 'NOT_OWNER'

    def test_supervisor_ve_cualquiera_200(self, supervisor_client, other_sample):
        Karyotype.objects.create(sample=other_sample)
        resp = supervisor_client.get(_karyotype_url(other_sample))
        assert resp.status_code == 200

    def test_anonimo_401(self, api_client, own_sample):
        Karyotype.objects.create(sample=own_sample)
        resp = api_client.get(_karyotype_url(own_sample))
        assert resp.status_code == 401

    def test_muestra_inexistente_404(self, analyst_client):
        resp = analyst_client.get('/api/clinic/samples/00000000-0000-0000-0000-000000000000/karyotype/')
        assert resp.status_code == 404
        assert resp.data['code'] == 'NOT_FOUND'


# ============================================================================
# Seed command
# ============================================================================
class TestSeedKaryotype:
    def test_seed_creates_46_chromosomes_with_3_oranges(self, own_sample):
        from apps.samples.management.commands.seed_karyotype import build_demo_karyotype
        k = build_demo_karyotype(own_sample)
        assert k.chromosomes.count() == 46
        oranges = [c for c in k.chromosomes.all() if c.semaphore == 'orange']
        assert len(oranges) == 3

    def test_seed_is_idempotent(self, own_sample):
        from apps.samples.management.commands.seed_karyotype import build_demo_karyotype
        build_demo_karyotype(own_sample)
        k2 = build_demo_karyotype(own_sample)
        assert Karyotype.objects.filter(sample=own_sample).count() == 1
        assert k2.chromosomes.count() == 46
