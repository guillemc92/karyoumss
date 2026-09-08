"""Tests de SampleDetailView (GET/PATCH/DELETE /samples/{id}/) — ADR-0018,
cierre de SPEC-008 §6 (tabla de 3 roles x 6 endpoints)."""
import pytest
from django.urls import reverse

from apps.samples.models import Sample, SampleStatus

pytestmark = pytest.mark.django_db


def _detail_url(sample):
    return reverse('samples:sample-detail', kwargs={'pk': sample.pk})


@pytest.fixture
def own_sample(analyst_user):
    return Sample.objects.create(chn_code='CHN-2026-07-13-0001', patient_ref='ANON-OWN', analyst=analyst_user)


@pytest.fixture
def other_sample(django_user_model):
    other = django_user_model.objects.create_user(username='other_analyst2', password='x')
    return Sample.objects.create(chn_code='CHN-2026-07-13-0002', patient_ref='ANON-OTHER', analyst=other)


class TestGet:
    def test_analista_ve_propia(self, analyst_client, own_sample):
        resp = analyst_client.get(_detail_url(own_sample))
        assert resp.status_code == 200
        assert resp.data['chn_code'] == own_sample.chn_code

    def test_analista_no_ve_ajena_403(self, analyst_client, other_sample):
        resp = analyst_client.get(_detail_url(other_sample))
        assert resp.status_code == 403

    def test_supervisor_ve_cualquiera(self, supervisor_client, other_sample):
        resp = supervisor_client.get(_detail_url(other_sample))
        assert resp.status_code == 200

    def test_admin_ve_cualquiera(self, admin_client, other_sample):
        resp = admin_client.get(_detail_url(other_sample))
        assert resp.status_code == 200

    def test_no_existe_404(self, analyst_client):
        import uuid
        url = reverse('samples:sample-detail', kwargs={'pk': uuid.uuid4()})
        resp = analyst_client.get(url)
        assert resp.status_code == 404

    def test_anonimo_401(self, api_client, own_sample):
        resp = api_client.get(_detail_url(own_sample))
        assert resp.status_code == 401


class TestPatch:
    def test_analista_edita_propia(self, analyst_client, own_sample):
        resp = analyst_client.patch(_detail_url(own_sample), {'patient_ref': 'ANON-UPDATED'}, format='json')
        assert resp.status_code == 200
        own_sample.refresh_from_db()
        assert own_sample.patient_ref == 'ANON-UPDATED'

    def test_analista_no_edita_ajena_403(self, analyst_client, other_sample):
        resp = analyst_client.patch(_detail_url(other_sample), {'patient_ref': 'X'}, format='json')
        assert resp.status_code == 403

    def test_supervisor_edita_cualquiera(self, supervisor_client, other_sample):
        resp = supervisor_client.patch(_detail_url(other_sample), {'patient_ref': 'ANON-SUP'}, format='json')
        assert resp.status_code == 200

    def test_rechaza_status_field_not_allowed(self, analyst_client, own_sample):
        resp = analyst_client.patch(_detail_url(own_sample), {'status': 'VALIDATED'}, format='json')
        assert resp.status_code == 400
        assert 'status' in resp.data

    def test_rechaza_chn_code_field_not_allowed(self, analyst_client, own_sample):
        resp = analyst_client.patch(_detail_url(own_sample), {'chn_code': 'CHN-HACKED'}, format='json')
        assert resp.status_code == 400
        assert 'chn_code' in resp.data


class TestDelete:
    def test_admin_elimina(self, admin_client, own_sample):
        resp = admin_client.delete(_detail_url(own_sample))
        assert resp.status_code == 204
        own_sample.refresh_from_db()
        assert own_sample.is_active is False
        assert own_sample.deleted_at is not None

    def test_analista_no_puede_eliminar_403(self, analyst_client, own_sample):
        resp = analyst_client.delete(_detail_url(own_sample))
        assert resp.status_code == 403

    def test_supervisor_no_puede_eliminar_403(self, supervisor_client, other_sample):
        resp = supervisor_client.delete(_detail_url(other_sample))
        assert resp.status_code == 403

    def test_no_elimina_validated_409(self, admin_client, own_sample):
        own_sample.status = SampleStatus.VALIDATED
        own_sample.save(update_fields=['status'])
        resp = admin_client.delete(_detail_url(own_sample))
        assert resp.status_code == 409
        own_sample.refresh_from_db()
        assert own_sample.is_active is True

    def test_anonimo_401(self, api_client, own_sample):
        resp = api_client.delete(_detail_url(own_sample))
        assert resp.status_code == 401

    def test_eliminada_no_aparece_en_get_posterior(self, admin_client, own_sample):
        admin_client.delete(_detail_url(own_sample))
        resp = admin_client.get(_detail_url(own_sample))
        assert resp.status_code == 404
