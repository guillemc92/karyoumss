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
