"""Campos cifrados at-rest (P2, ADR-0014, DD-ADMIN-002 §3.2).

Mismo patrón que backend-clinic/apps/samples/fields.py (EncryptedTextField,
ADR-0016 D2) — Fernet, transparente para el resto del código: se lee/
escribe como str normal, en DB se persiste el token cifrado.

Usado por User.two_factor_secret: un secret TOTP NO puede guardarse con
un hash irreversible (make_password) porque el servidor necesita el
secret en claro para recalcular el código esperado y compararlo con el
que ingresa el usuario — a diferencia de una contraseña, que solo se
compara, nunca se recalcula un HMAC sobre ella.
"""
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models


def _fernet() -> Fernet:
    key = settings.TOTP_VAULT_KEY
    return Fernet(key.encode() if isinstance(key, str) else key)


class EncryptedCharField(models.CharField):
    """CharField cifrado at-rest con Fernet. El texto cifrado (base64,
    ~100+ bytes) requiere max_length generoso — ver two_factor_secret."""

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


def decrypt_totp_secret(encrypted_or_plain: str) -> str:
    """Descifra un two_factor_secret leído directamente de la DB sin pasar
    por el ORM (ej. en un servicio que ya tiene el valor en mano). En el
    camino normal (user.two_factor_secret vía ORM), from_db_value ya lo
    descifra — esta función es para el caso de tener el valor crudo."""
    try:
        return _fernet().decrypt(encrypted_or_plain.encode()).decode()
    except InvalidToken:
        return encrypted_or_plain
