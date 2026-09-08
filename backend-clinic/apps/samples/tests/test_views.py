import pytest
from django.urls import reverse

from apps.samples.models import Sample


@pytest.mark.django_db
class TestSampleListCreate:
    def test_create_sample_success(self, analyst_client, analyst_user):
        url = reverse('samples:sample-list-create')
        payload = {
            'chn_code': 'CHN-2026-07-12-0001',
            'patient_ref': 'ANON-001',
            'image_path': 's3://biomed/CHN-2026-07-12-0001.tiff',
            'metadata': {'gender': 'M', 'age': 28},
        }
        resp = analyst_client.post(url, payload, format='json')
        assert resp.status_code == 201
        assert resp.data['chn_code'] == 'CHN-2026-07-12-0001'
        assert Sample.objects.filter(chn_code='CHN-2026-07-12-0001', analyst=analyst_user).exists()

    def test_create_duplicate_chn_rejected(self, analyst_client, analyst_user):
        Sample.objects.create(chn_code='CHN-DUP-001', patient_ref='ANON-X', analyst=analyst_user)
        url = reverse('samples:sample-list-create')
        resp = analyst_client.post(url, {'chn_code': 'CHN-DUP-001', 'patient_ref': 'ANON-Y'}, format='json')
        assert resp.status_code == 400

    def test_create_unauthenticated_rejected(self, api_client):
        url = reverse('samples:sample-list-create')
        resp = api_client.post(url, {'chn_code': 'CHN-X', 'patient_ref': 'Y'}, format='json')
        assert resp.status_code == 401

    def test_list_scoped_to_analyst(self, analyst_client, analyst_user, django_user_model):
        other = django_user_model.objects.create_user(username='other_analyst', password='x')
        Sample.objects.create(chn_code='CHN-MINE', patient_ref='A', analyst=analyst_user)
        Sample.objects.create(chn_code='CHN-OTHER', patient_ref='B', analyst=other)

        url = reverse('samples:sample-list-create')
        resp = analyst_client.get(url)
        assert resp.status_code == 200
        chn_codes = [item['chn_code'] for item in resp.data]
        assert 'CHN-MINE' in chn_codes
        assert 'CHN-OTHER' not in chn_codes

    def test_list_supervisor_sees_all(self, supervisor_client, analyst_user):
        Sample.objects.create(chn_code='CHN-A', patient_ref='A', analyst=analyst_user)
        Sample.objects.create(chn_code='CHN-B', patient_ref='B', analyst=analyst_user)

        url = reverse('samples:sample-list-create')
        resp = supervisor_client.get(url)
        assert resp.status_code == 200
        assert len(resp.data) == 2


@pytest.mark.django_db
class TestSampleListFilters:
    """Filtros server-side de GET /samples/ (SPEC-008 UC-S-002, decisión
    2026-07-16: shape de respuesta se mantiene array plano)."""

    def test_filtro_status(self, supervisor_client, analyst_user):
        from apps.samples.models import SampleStatus
        Sample.objects.create(chn_code='CHN-READY', patient_ref='A', analyst=analyst_user, status=SampleStatus.READY)
        Sample.objects.create(chn_code='CHN-PENDING', patient_ref='B', analyst=analyst_user, status=SampleStatus.PENDING_AI)

        resp = supervisor_client.get(reverse('samples:sample-list-create'), {'status': 'READY'})

        assert resp.status_code == 200
        chn_codes = [item['chn_code'] for item in resp.data]
        assert chn_codes == ['CHN-READY']

    def test_filtro_chn_query_contains(self, supervisor_client, analyst_user):
        Sample.objects.create(chn_code='CHN-2026-07-01-0001', patient_ref='A', analyst=analyst_user)
        Sample.objects.create(chn_code='CHN-2026-08-01-0002', patient_ref='B', analyst=analyst_user)

        resp = supervisor_client.get(reverse('samples:sample-list-create'), {'chn_query': '2026-07'})

        assert resp.status_code == 200
        chn_codes = [item['chn_code'] for item in resp.data]
        assert chn_codes == ['CHN-2026-07-01-0001']

    def test_filtro_fecha_rango(self, supervisor_client, analyst_user):
        from datetime import date
        s1 = Sample.objects.create(chn_code='CHN-JUL', patient_ref='A', analyst=analyst_user)
        Sample.objects.filter(pk=s1.pk).update(created_at=date(2026, 7, 5))
        s2 = Sample.objects.create(chn_code='CHN-AGO', patient_ref='B', analyst=analyst_user)
        Sample.objects.filter(pk=s2.pk).update(created_at=date(2026, 8, 5))

        resp = supervisor_client.get(
            reverse('samples:sample-list-create'),
            {'date_from': '2026-07-01', 'date_to': '2026-07-31'},
        )

        assert resp.status_code == 200
        chn_codes = [item['chn_code'] for item in resp.data]
        assert chn_codes == ['CHN-JUL']

    def test_filtros_combinados_analista_scoped(self, analyst_client, analyst_user, django_user_model):
        from apps.samples.models import SampleStatus
        other = django_user_model.objects.create_user(username='other_analyst4', password='x')
        Sample.objects.create(chn_code='CHN-MINE-READY', patient_ref='A', analyst=analyst_user, status=SampleStatus.READY)
        Sample.objects.create(chn_code='CHN-MINE-PENDING', patient_ref='B', analyst=analyst_user, status=SampleStatus.PENDING_AI)
        Sample.objects.create(chn_code='CHN-OTHER-READY', patient_ref='C', analyst=other, status=SampleStatus.READY)

        resp = analyst_client.get(reverse('samples:sample-list-create'), {'status': 'READY'})

        assert resp.status_code == 200
        chn_codes = [item['chn_code'] for item in resp.data]
        assert chn_codes == ['CHN-MINE-READY']

    def test_sin_filtros_retorna_todas_las_scoped(self, analyst_client, analyst_user):
        Sample.objects.create(chn_code='CHN-1', patient_ref='A', analyst=analyst_user)
        Sample.objects.create(chn_code='CHN-2', patient_ref='B', analyst=analyst_user)

        resp = analyst_client.get(reverse('samples:sample-list-create'))

        assert resp.status_code == 200
        assert len(resp.data) == 2
