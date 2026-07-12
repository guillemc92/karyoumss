import pytest
from django.db import connection

from apps.samples.models import PatientVault


@pytest.mark.django_db
class TestEncryptedTextField:
    def test_roundtrip_encrypts_and_decrypts(self):
        vault = PatientVault.objects.create(chn_code='CHN-2026-01-01-0001', full_name='Juan Pérez')
        vault.refresh_from_db()
        assert vault.full_name == 'Juan Pérez'

    def test_stored_value_is_not_plaintext(self):
        PatientVault.objects.create(chn_code='CHN-2026-01-01-0002', full_name='Ana García')
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT full_name FROM clinic_patient_vault WHERE chn_code = %s", ['CHN-2026-01-01-0002']
            )
            stored = cursor.fetchone()[0]
        assert stored != 'Ana García'
        assert len(stored) > len('Ana García')

    def test_empty_string_is_not_encrypted(self):
        vault = PatientVault.objects.create(chn_code='CHN-2026-01-01-0003', full_name='X', document_id='')
        vault.refresh_from_db()
        assert vault.document_id == ''

    def test_multiple_encrypted_fields_roundtrip(self):
        vault = PatientVault.objects.create(
            chn_code='CHN-2026-01-01-0004',
            full_name='Carlos Ruiz',
            birth_date='1990-05-20',
            document_id='87654321',
            phone='+591 70000000',
            indication='Consulta genética',
            family_history='Sin antecedentes',
        )
        vault.refresh_from_db()
        assert vault.birth_date == '1990-05-20'
        assert vault.document_id == '87654321'
        assert vault.phone == '+591 70000000'
        assert vault.indication == 'Consulta genética'
        assert vault.family_history == 'Sin antecedentes'
