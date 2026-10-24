"""
Django settings for clinic_backend (bounded context Muestras clínico — ADR-0015).

Stack: Django 5 + DRF + SimpleJWT + SQLite (dev).
Satélite del clínico FastAPI (pipeline U-Net + EfficientNet intacto).
Puerto :8002. Cero acoplamiento con backend-admin (:8001).
"""

from datetime import timedelta
from pathlib import Path
import os

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')


def env(key: str, default=None, required=False):
    val = os.environ.get(key, default)
    if required and val is None:
        raise RuntimeError(f"Missing required env var: {key}")
    return val


# ============================================================================
# Core Django
# ============================================================================

# DD-AUD-001 F3 (F12-02): sin valor por defecto. Un despliegue que olvidara la
# variable arrancaría con una clave que conoce cualquiera con acceso al repo.
SECRET_KEY = env('DJANGO_SECRET_KEY', required=True)
# Apagado salvo que se pida, como en backend-admin (F12-01).
DEBUG = env('DJANGO_DEBUG', 'False').lower() in ('true', '1', 'yes')
ALLOWED_HOSTS = [h.strip() for h in env('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',') if h.strip()]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'drf_spectacular',  # DD-API-001: el contrato OpenAPI se genera desde el código

    # Local apps (bounded context Muestras clínico)
    'apps.samples',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'clinic_backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'clinic_backend.wsgi.application'

# ============================================================================
# Database — SQLite dev/demo, físicamente separado de backend-admin (ADR-0015 #3/#4)
# ============================================================================

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / env('CLINIC_DB_NAME', 'clinic_demo.sqlite3'),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 8}},
]

# ============================================================================
# DRF + SimpleJWT — SSO (ADR-0020): backend-admin es la ÚNICA autoridad de
# JWT del sistema. backend-clinic ya NO emite tokens de login propio (D1);
# solo VALIDA los de backend-admin, con el mismo secreto compartido.
# SharedJWTAuthentication (apps/samples/auth_bridge.py) sincroniza el User
# local a partir de los claims {email, role} del token (D2). Deroga
# parcialmente ADR-0015 D5 ("JWT independiente del admin, por diseño").
# ============================================================================

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'apps.samples.auth_bridge.SharedJWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
    ],
    # DD-API-001: drf-spectacular genera el contrato (`manage.py spectacular`).
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# DD-API-001 — contrato OpenAPI de backend-clinic (`backend-clinic/openapi.json`).
# Se exporta con `python manage.py spectacular --file openapi.json --validate` y el
# CI comprueba que el archivo del repositorio es el que genera el código (drift).
SPECTACULAR_SETTINGS = {
    'TITLE': 'BIOMED UMSS — API clínica',
    'DESCRIPTION': (
        'API del servicio clínico (muestras, cariotipo y su corrección manual, supervisor). '
        'Contrato generado desde el código; ver docs/design/DD-API-001.md.'
    ),
    'VERSION': '8.2.0',
    'CONTACT': {'name': 'Ing. Guillermo Mamani Chambi', 'url': 'https://github.com/guillemc92/karyoumss'},
    'SERVERS': [{'url': 'http://localhost:8002', 'description': 'Desarrollo local (detrás de Caddy: http://localhost:3000)'}],
    # Las etiquetas agrupan las operaciones; Spectral exige que estén declaradas.
    'TAGS': [
        {'name': 'Cariotipo', 'description': 'Lectura del cariotipo y de su metafase.'},
        {'name': 'Corrección manual', 'description': 'Corrección de la segmentación sobre la metafase (DD-KARYO-007, FSD-UC-003).'},
        {'name': 'Muestras', 'description': 'Alta, consulta y edición de muestras.'},
        {'name': 'Sin describir', 'description': 'Endpoints que el contrato todavía declara como objeto JSON genérico (DD-API-001 D2).'},
    ],
    # El contrato describe la API, no a sí mismo.
    'SERVE_INCLUDE_SCHEMA': False,
    # Esquemas distintos para lo que entra y lo que sale (campos read_only).
    'COMPONENT_SPLIT_REQUEST': True,
    # Determinista: el drift no puede fallar sin que nadie haya cambiado nada.
    'SORT_OPERATIONS': True,
    'SORT_OPERATION_PARAMETERS': True,
    # Un solo nombre para las 24 clases (1-22, X, Y), las use quien las use.
    'ENUM_NAME_OVERRIDES': {'ClaseCromosomaEnum': 'apps.samples.models.CHROMOSOME_CLASSES'},
}

SIMPLE_JWT = {
    # ACCESS/REFRESH_TOKEN_LIFETIME deben coincidir con backend-admin/
    # admin_backend/settings.py — un token válido en uno no debe expirar
    # "antes" en el otro. Si se cambia acá, cambiar también allá.
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': env('AUTH_ADMIN_JWT_SECRET', required=True),  # compartido con backend-admin, antes: AUTH_CLINIC_SECRET
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# ============================================================================
# PatientVault (ADR-0016 D2) — clave Fernet para cifrado PII at-rest
# ============================================================================

PATIENT_VAULT_KEY = env('PATIENT_VAULT_KEY', required=True)

# ============================================================================
# Pipeline FastAPI (ADR-0015 #6 — cliente con circuit breaker)
# ============================================================================

# backend-ml (motor de inferencia, ADR-0007/DD-ML-001) — el FastAPI de :8000.
# 127.0.0.1 y no localhost: en Windows, `localhost` prueba primero IPv6 (::1),
# uvicorn escucha solo en IPv4 y cada conexión nueva perdía ~2 s (medido 23/10).
CLINIC_FASTAPI_URL = env('CLINIC_FASTAPI_URL', 'http://127.0.0.1:8000')

# Almacenamiento de imágenes de metafase reales (DD-ML-002 §2.1).
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / env('CLINIC_MEDIA_DIR', 'media')
CLINIC_FASTAPI_TIMEOUT = float(env('CLINIC_FASTAPI_TIMEOUT', '2.0'))
CLINIC_FASTAPI_CIRCUIT_THRESHOLD = int(env('CLINIC_FASTAPI_CIRCUIT_THRESHOLD', '3'))
CLINIC_FASTAPI_CIRCUIT_COOLDOWN = int(env('CLINIC_FASTAPI_CIRCUIT_COOLDOWN', '60'))

# ============================================================================
# backend-admin interno (ADR-0023 D3, DD-SUP-002 — verificación MFA delegada)
# ============================================================================

ADMIN_INTERNAL_URL = env('ADMIN_INTERNAL_URL', 'http://localhost:8001')
INTERNAL_SERVICE_SECRET = env('INTERNAL_SERVICE_SECRET', required=True)   # DD-AUD-001 F3

# ============================================================================
# LLM local para la narrativa del informe (ADR-0024 — IA generativa vía SDK)
# ============================================================================

# Ollama en localhost: API compatible con el SDK de OpenAI. Al no salir ningún
# dato de la máquina, RN-03 (cero fuga de PII) se cumple por construcción.
CLINIC_LLM_URL = env('CLINIC_LLM_URL', 'http://localhost:11434/v1')
# Dimensionado para el hardware actual (i5-3317U, sin GPU). Subir de modelo al
# migrar a más memoria es un cambio de config, no de arquitectura (ADR-0024 D2).
CLINIC_LLM_MODEL = env('CLINIC_LLM_MODEL', 'llama3.2:3b')
# Holgado a propósito: la inferencia en CPU va a ~2-5 tok/s. Medido en el
# hardware actual (i5-3317U): 107 s para una narrativa de 367 tokens, y un caso
# con más contexto superó los 190 s. Con GPU basta un valor mucho menor.
CLINIC_LLM_TIMEOUT = float(env('CLINIC_LLM_TIMEOUT', '240.0'))
CLINIC_LLM_CIRCUIT_THRESHOLD = int(env('CLINIC_LLM_CIRCUIT_THRESHOLD', '3'))
CLINIC_LLM_CIRCUIT_COOLDOWN = int(env('CLINIC_LLM_CIRCUIT_COOLDOWN', '120'))
# DD-AUD-001 F2 (CON-04): reintentos explícitos y límite de concurrencia del LLM.
# El SDK reintentaba 2 veces por defecto, también tras un timeout de 240 s.
CLINIC_LLM_MAX_RETRIES = int(env('CLINIC_LLM_MAX_RETRIES', '0'))
CLINIC_LLM_MAX_CONCURRENTES = int(env('CLINIC_LLM_MAX_CONCURRENTES', '2'))
CLINIC_LLM_ESPERA_MAX_S = float(env('CLINIC_LLM_ESPERA_MAX_S', '5.0'))
# Apagado por defecto: sin narrativa el informe se emite igual (RN-07).
CLINIC_LLM_ENABLED = env('CLINIC_LLM_ENABLED', 'false').lower() in ('1', 'true', 'yes')

# ============================================================================
# CORS (ADR-0015 #10 — allowlist frontend-clinic :5174)
# ============================================================================

CORS_ALLOWED_ORIGINS = [
    o.strip() for o in env('CORS_ALLOWED_ORIGINS',
                          'http://localhost:5174,http://localhost:3000').split(',')
    if o.strip()
]

# ============================================================================
# i18n
# ============================================================================

LANGUAGE_CODE = 'es-bo'
TIME_ZONE = 'America/La_Paz'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
