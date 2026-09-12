from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models


def _fernet() -> Fernet:
    return Fernet(settings.PATIENT_VAULT_KEY.encode() if isinstance(settings.PATIENT_VAULT_KEY, str) else settings.PATIENT_VAULT_KEY)


class EncryptedTextField(models.TextField):
    """Campo cifrado at-rest con Fernet (ADR-0016 D2, RN-03).

    Transparente para el resto del código: se lee/escribe como str
    normal, pero en DB se persiste el token Fernet cifrado.
    """

    def get_prep_value(self, value):
        if value is None or value == '':
            return value
        token = _fernet().encrypt(str(value).encode())
        return token.decode()

    def from_db_value(self, value, expression, connection):
        if value is None or value == '':
            return value
        try:
            return _fernet().decrypt(value.encode()).decode()
        except InvalidToken:
            return value
