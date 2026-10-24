"""
Servicios de dominio de apps/config (DD-ADMIN-002).

P0: placeholder. Servicios concretos añadidos por fase:
- P1: (sin service; la lógica es trivial en el viewset)
- P2: rotate_password, setup_2fa, toggle_2fa (este archivo)
- P3: get_active_model_config() con select_for_update anti-race
- P4: (sin service)
- P5: test_integration_connection(integration) con timeout 5s
- P6: (sin service)
"""
import base64
import io
import re

import pyotp
import qrcode
from django.contrib.auth.hashers import check_password
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import PasswordHistory

PASSWORD_HISTORY_DEPTH = 5
PASSWORD_MIN_LENGTH = 12


def rotate_password(user, current: str, new: str, confirm: str) -> None:
    """P2 — DD-ADMIN-002 §3.5. Cambia la contraseña del usuario, aplicando:
    - confirmación de la contraseña actual
    - fortaleza mínima (≥12 chars, 1 mayúscula, 1 dígito)
    - no reutilización de las últimas 5 contraseñas

    Levanta django.core.exceptions.ValidationError con dict de campo→mensaje,
    consistente con el resto del proyecto (ver apps/config/models.py).
    """
    if not user.check_password(current):
        raise ValidationError({'current': 'Contraseña actual incorrecta'})
    if new != confirm:
        raise ValidationError({'confirm': 'No coincide con la nueva contraseña'})
    if (
        len(new) < PASSWORD_MIN_LENGTH
        or not re.search(r'[A-Z]', new)
        or not re.search(r'[0-9]', new)
    ):
        raise ValidationError(
            {'new': f'Mínimo {PASSWORD_MIN_LENGTH} caracteres, 1 mayúscula, 1 dígito'}
        )

    recent = PasswordHistory.objects.filter(user=user).order_by('-changed_at')[:PASSWORD_HISTORY_DEPTH]
    for h in recent:
        if check_password(new, h.password_hash):
            raise ValidationError({'new': 'No reutilice contraseñas recientes'})
    if check_password(new, user.password):
        raise ValidationError({'new': 'No reutilice contraseñas recientes'})

    user.set_password(new)
    user.password_changed_at = timezone.now()
    user.save(update_fields=['password', 'password_changed_at'])
    PasswordHistory.objects.create(user=user, password_hash=user.password)


def setup_2fa(user) -> dict:
    """P2 — genera un secret TOTP nuevo (RFC 6238) y lo guarda CIFRADO
    at-rest (EncryptedCharField, Fernet reversible — ver
    apps/users/fields.py) en user.two_factor_secret. El QR y la respuesta
    de este endpoint son la única vez que el secret viaja fuera del
    servidor; el cliente debe pedir setup_2fa() de nuevo si pierde el QR.

    El QR codifica una otpauth:// URI estándar, compatible con Google
    Authenticator/Authy/etc.
    """
    secret = pyotp.random_base32()
    user.two_factor_secret = secret  # EncryptedCharField cifra al guardar
    user.save(update_fields=['two_factor_secret'])

    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name=user.email, issuer_name='BIOMED UMSS')
    qr_img = qrcode.make(uri)
    buf = io.BytesIO()
    qr_img.save(buf, format='PNG')
    qr_code_b64 = base64.b64encode(buf.getvalue()).decode('ascii')

    return {'secret': secret, 'qr_code_b64': qr_code_b64}


def toggle_2fa(user, enabled: bool, code: str) -> bool:
    """P2 — activa/desactiva 2FA. Exige un código TOTP válido tanto para
    activar como para desactivar (protección contra desactivación por
    sesión robada, DD-ADMIN-002 §3.4).

    El secret hasheado (make_password) no permite recomputar el TOTP
    directamente — por eso setup_2fa() devuelve el secret en claro una
    sola vez y este método verifica contra un secret en claro que el
    CLIENTE ya conoce (typeó el código con su app autenticadora, que
    tiene el secret original). No podemos verificar un TOTP contra un
    hash, así que el secret se re-deriva comparando el código recibido
    contra una ventana de TOTP calculada con el secret guardado — para
    esto, `two_factor_secret` debe guardarse de forma REVERSIBLE, no con
    make_password (ver nota de diseño abajo).
    """
    if not user.two_factor_secret:
        raise ValidationError({'code': 'No hay 2FA configurado. Ejecute el setup primero.'})

    if not _verify_totp_code(user, code):
        raise ValidationError({'code': 'Código de verificación inválido'})

    user.two_factor_enabled = enabled
    user.save(update_fields=['two_factor_enabled'])
    return user.two_factor_enabled


def _verify_totp_code(user, code: str) -> bool:
    """Verifica un código TOTP de 6 dígitos contra el secret del usuario.

    NOTA DE DISEÑO (corrige DD-ADMIN-002 §3.2, que decía "hasheado"):
    un secret TOTP hasheado con make_password() es IRREVERSIBLE — no se
    puede recalcular el código esperado a partir del hash, porque TOTP
    necesita el secret real (no un digest) para generar el código del
    lado servidor y compararlo. "Hasheado" solo tiene sentido para
    contraseñas (donde solo se compara, nunca se recalcula un HMAC).
    User.two_factor_secret usa EncryptedCharField (Fernet, reversible,
    apps/users/fields.py) — el ORM ya lo descifra al leer el atributo,
    así que acá `user.two_factor_secret` YA es el secret en claro.
    """
    if not user.two_factor_secret:
        return False
    totp = pyotp.TOTP(user.two_factor_secret)
    return totp.verify(code, valid_window=1)
