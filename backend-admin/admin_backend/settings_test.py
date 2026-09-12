"""
Settings de testing para backend-admin (F6).

Reemplaza la DB por SQLite en archivo (no :memory: por django-auditlog) y
conserva todo lo demás del settings principal. Lo activamos vía
DJANGO_SETTINGS_MODULE=admin_backend.settings_test en pytest.ini.

Why un settings separado (no pytest-django override):
- _admin_schema_table() en apps/users/models.py lee settings.DATABASES en
  tiempo de import (cuando se evalúa Meta.db_table). Necesitamos que el
  ENGINE ya sea sqlite3 antes de que el modelo se importe.
- pytest-django --db-engine=sqlite3 hace esto también, pero la sustitución
  ocurre después del import de modelos en algunos casos. Más robusto tener
  un settings dedicado.
"""
import os
from pathlib import Path

# Recarga del .env para tener AUTH_BRIDGE_SECRET.
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

# Importamos el settings principal y mutamos solo lo necesario.
from .settings import *  # noqa: F401, F403

# Valores por defecto para tests si .env no los provee (evita RuntimeError en CI).
os.environ.setdefault('DJANGO_SECRET_KEY', 'test-secret-key-not-for-production-' + 'x' * 40)
os.environ.setdefault('AUTH_BRIDGE_SECRET', 'test-bridge-secret-' + 'b' * 50)
os.environ.setdefault('AUTH_ADMIN_JWT_SECRET', 'test-admin-jwt-secret-' + 'c' * 40)
os.environ.setdefault('POSTGRES_PASSWORD', 'test')

# ----------------------------------------------------------------------------
# Override DB → SQLite en archivo. django-auditlog usa signals que requieren
# persistencia entre conexiones (triggers), por eso NO usamos :memory:.
# ----------------------------------------------------------------------------

TEST_DB_FILE = BASE_DIR / 'test_db.sqlite3'
if TEST_DB_FILE.exists():
    TEST_DB_FILE.unlink()

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': str(TEST_DB_FILE),
        # OPTIONS: timeout alto evita "database is locked" en paralelismo.
        # Nota: NO usamos 'init_command' (no soportado por sqlite3.connect);
        # FK enforcement se enciende con PRAGMA en el cursor cuando se necesita.
        'OPTIONS': {
            'timeout': 30,
        },
    }
}

# ----------------------------------------------------------------------------
# Override apps — django.contrib.contenttypes y auditlog son obligatorios.
# ----------------------------------------------------------------------------
INSTALLED_APPS = list(INSTALLED_APPS)  # noqa: F405

# ----------------------------------------------------------------------------
# Debug ON para que los tests fallen con stacktrace detallado en errores.
# ----------------------------------------------------------------------------
DEBUG = True
ALLOWED_HOSTS = ['*']

# ----------------------------------------------------------------------------
# Auth bridge: valores fijos para que los tests sean determinísticos.
# ----------------------------------------------------------------------------
AUTH_BRIDGE_SECRET = 'test-secret-' + 'a' * 60  # 71 chars para HS256
AUTH_BRIDGE_ALGORITHM = 'HS256'
AUTH_BRIDGE_REQUIRED_CLAIMS = ['sub', 'email', 'role', 'exp']
AUTH_BRIDGE_VALID_ROLES = ['analista', 'supervisor', 'admin']

# ----------------------------------------------------------------------------
# Login unificado (ADR-0017): secret fijo determinístico, igual criterio que
# AUTH_BRIDGE_SECRET arriba. Se reconstruye SIMPLE_JWT porque su SIGNING_KEY
# ya quedó fijado con el valor de import-time en `from .settings import *`.
# ----------------------------------------------------------------------------
AUTH_ADMIN_JWT_SECRET = 'test-admin-jwt-secret-' + 'c' * 40
SIMPLE_JWT = {**SIMPLE_JWT, 'SIGNING_KEY': AUTH_ADMIN_JWT_SECRET}  # noqa: F405

# ----------------------------------------------------------------------------
# DRF — sin throttling en tests para no flaky. Default 60/min podría bloquear.
# JWTAuthentication se mantiene (ADR-0017 login real se testea con JWT, no Token).
# ----------------------------------------------------------------------------
REST_FRAMEWORK = {  # noqa: F405
    **REST_FRAMEWORK,  # noqa: F405
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_THROTTLE_CLASSES': [],  # sin throttling en tests
    'DEFAULT_THROTTLE_RATES': {},  # sin rates
}

# ----------------------------------------------------------------------------
# Logging más silencioso en tests.
# ----------------------------------------------------------------------------
LOGGING = {  # noqa: F405
    'version': 1,
    'disable_existing_loggers': True,
    'handlers': {
        'null': {'class': 'logging.NullHandler'},
    },
    'loggers': {
        'apps': {'handlers': ['null'], 'level': 'CRITICAL'},
        'auditlog': {'handlers': ['null'], 'level': 'CRITICAL'},
        'django.db.backends': {'handlers': ['null'], 'level': 'WARNING'},
    },
}