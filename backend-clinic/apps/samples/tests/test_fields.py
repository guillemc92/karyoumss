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


@pytest.mark.django_db
class TestValorNoCifradoEnLaBase:
    """Que pasa cuando lo guardado NO es un token Fernet valido.

    Ocurre de verdad en dos situaciones: filas escritas antes de que el campo se
    cifrara, y filas cifradas con otra clave (una rotacion mal hecha, o un dump
    restaurado de otro entorno).

    La decision del campo es **devolver el valor tal cual** en vez de lanzar. Es
    deliberada y hay que fijarla: si `from_db_value` lanzara, una sola fila
    corrupta tumbaria cualquier consulta que la incluyera —incluido el listado de
    muestras— y el laboratorio se quedaria sin poder trabajar por un dato viejo.
    """

    def _escribir_en_crudo(self, chn, valor):
        PatientVault.objects.create(chn_code=chn, full_name='X')
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE clinic_patient_vault SET full_name = %s WHERE chn_code = %s",
                [valor, chn],
            )

    def test_un_valor_en_claro_heredado_se_lee_sin_romper(self):
        self._escribir_en_crudo('CHN-2026-01-01-0005', 'Texto en claro heredado')
        vault = PatientVault.objects.get(chn_code='CHN-2026-01-01-0005')
        assert vault.full_name == 'Texto en claro heredado'

    def test_un_token_de_otra_clave_tampoco_tumba_la_consulta(self):
        from cryptography.fernet import Fernet

        ajeno = Fernet(Fernet.generate_key()).encrypt(b'Ana Garcia').decode()
        self._escribir_en_crudo('CHN-2026-01-01-0006', ajeno)

        vault = PatientVault.objects.get(chn_code='CHN-2026-01-01-0006')
        # No se descifra —no se puede— pero tampoco se pierde la fila: se
        # devuelve el token, que es lo unico honesto que se puede hacer.
        assert vault.full_name == ajeno

    def test_una_fila_ilegible_no_impide_listar_las_demas(self):
        """El caso que justifica la decision: una fila mala no puede costar el
        listado entero."""
        self._escribir_en_crudo('CHN-2026-01-01-0007', 'no es un token')
        PatientVault.objects.create(chn_code='CHN-2026-01-01-0008', full_name='Ana')

        nombres = {v.chn_code: v.full_name for v in PatientVault.objects.all()}
        assert nombres['CHN-2026-01-01-0007'] == 'no es un token'
        assert nombres['CHN-2026-01-01-0008'] == 'Ana'
