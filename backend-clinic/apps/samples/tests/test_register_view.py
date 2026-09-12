import pytest
from django.urls import reverse

from apps.samples.models import Sample

VALID_IMAGE = 'data:image/jpeg;base64,aGVsbG8gd29ybGQ='


def _payload(**overrides):
    base = {
        'patient': {'full_name': 'ANON-VIEW', 'birth_date': '1998-03-15'},
        'sample': {'chn_code': 'CHN-2026-07-12-0099', 'sample_type': 'sangre', 'gender': 'M'},
        'clinical_history': {'indication': 'x', 'family_history': ''},
        'analysis_requests': ['karyotype_high_res'],
        'images': [{'data_base64': VALID_IMAGE, 'source': 'camera'}] * 3,
        'is_draft': False,
    }
    base.update(overrides)
    return base


@pytest.mark.django_db
class TestSampleRegisterView:
    def test_register_complete_returns_201(self, analyst_client):
        url = reverse('samples:sample-register')
        resp = analyst_client.post(url, _payload(), format='json')
        assert resp.status_code == 201
        assert resp.data['status'] == 'PENDING_AI'

    def test_register_draft_returns_201(self, analyst_client):
        url = reverse('samples:sample-register')
        payload = _payload(is_draft=True, patient={'full_name': ''}, images=[])
        resp = analyst_client.post(url, payload, format='json')
        assert resp.status_code == 201
        assert resp.data['status'] == 'DRAFT'

    def test_register_unauthenticated_returns_401(self, api_client):
        url = reverse('samples:sample-register')
        resp = api_client.post(url, _payload(), format='json')
        assert resp.status_code == 401

    def test_register_invalid_chn_format_returns_400(self, analyst_client):
        url = reverse('samples:sample-register')
        payload = _payload(sample={'chn_code': 'not-a-chn', 'sample_type': 'sangre'})
        resp = analyst_client.post(url, payload, format='json')
        assert resp.status_code == 400
        assert resp.data['code'] == 'INVALID_CHN_FORMAT'

    def test_register_missing_patient_name_returns_400(self, analyst_client):
        url = reverse('samples:sample-register')
        payload = _payload(patient={'full_name': ''})
        resp = analyst_client.post(url, payload, format='json')
        assert resp.status_code == 400
        assert resp.data['code'] == 'PATIENT_NAME_REQUIRED'

    def test_register_insufficient_images_returns_400(self, analyst_client):
        url = reverse('samples:sample-register')
        payload = _payload(images=[{'data_base64': VALID_IMAGE, 'source': 'camera'}])
        resp = analyst_client.post(url, payload, format='json')
        assert resp.status_code == 400
        assert resp.data['code'] == 'INSUFFICIENT_IMAGES'

    def test_register_duplicate_chn_returns_409(self, analyst_client):
        url = reverse('samples:sample-register')
        analyst_client.post(url, _payload(), format='json')
        resp = analyst_client.post(url, _payload(), format='json')
        assert resp.status_code == 409
        assert resp.data['code'] == 'CHN_DUPLICATE'

    def test_register_invalid_analysis_request_returns_400(self, analyst_client):
        url = reverse('samples:sample-register')
        payload = _payload(analysis_requests=['not_a_real_analysis'])
        resp = analyst_client.post(url, payload, format='json')
        assert resp.status_code == 400

    def test_register_persists_analysis_requests(self, analyst_client):
        url = reverse('samples:sample-register')
        resp = analyst_client.post(url, _payload(analysis_requests=['karyotype_high_res', 'fish']), format='json')
        sample = Sample.objects.get(id=resp.data['id'])
        assert sample.analysis_requests == ['karyotype_high_res', 'fish']

    def test_register_supervisor_can_register(self, supervisor_client):
        url = reverse('samples:sample-register')
        payload = _payload(sample={'chn_code': 'CHN-2026-07-12-0100', 'sample_type': 'medula'})
        resp = supervisor_client.post(url, payload, format='json')
        assert resp.status_code == 201
