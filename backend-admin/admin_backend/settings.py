"""
Django settings for backend-admin (bounded context admin — ADR-0013).

Stack: Django 5 + DRF + django-auditlog + django-guardian + PostgreSQL schema 'admin'.
Auth bridge: PyJWT HS256 compartido con FastAPI (ver docs/AUTH_BRIDGE.md).
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

SECRET_KEY = env('DJANGO_SECRET_KEY', required=True)
DEBUG = env('DJANGO_DEBUG', 'False').lower() in ('true', '1', 'yes')
ALLOWED_HOSTS = [h.strip() for h in env('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',') if h.strip()]

# Aplicaciones: Django core + DRF + django-auditlog + django-guardian + nuestras apps
INSTALLED_APPS = [
    # Django
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party
    'rest_framework',
    'rest_framework.authtoken',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'auditlog',
    'guardian',

    # Local apps (bounded context admin)
    'apps.users',
    'apps.audit',
    'apps.config',
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

    # django-auditlog (debe ir DESPUÉS de auth)
    'auditlog.middleware.AuditlogMiddleware',
]

ROOT_URLCONF = 'admin_backend.urls'

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

WSGI_APPLICATION = 'admin_backend.wsgi.application'

# ============================================================================
# Database — PostgreSQL schema 'admin' (separado del clínico)
# ============================================================================

DATABASES = {
    'default': {
        # === DEMO-ONLY OVERRIDE (2026-07-01) ============================================
        # Postgres local no está disponible. Forzando SQLite para que el demo levante.
        # Esto ELIMINA el aislamiento de schema 'admin' vs 'public' (regla ADR-0012).
        # RESTAURAR LA CONFIGURACIÓN POSTGRES ANTES DE COMMIT/CI.
        # Marcado: settings.py:91 — quitar este bloque si DB_ENGINE != 'sqlite'.
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'demo_admin.sqlite3',
    } if env('DB_ENGINE', 'postgres') == 'sqlite' else {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('POSTGRES_DB', 'biomed'),
        'USER': env('POSTGRES_USER', 'biomed_admin_service'),
        'PASSWORD': env('POSTGRES_PASSWORD', ''),
        'HOST': env('POSTGRES_HOST', 'localhost'),
        'PORT': env('POSTGRES_PORT', '5432'),
        'OPTIONS': {
            'options': '-c search_path=admin,public',  # Busca primero en schema admin
        },
        # El rol biomed_admin_service debe tener GRANT solo sobre schema 'admin'.
        # Sin permisos sobre public ni schemas clínicos (cases, samples, edits).
    }
}

# ============================================================================
# Auth (F0 bridge + DRF Token)
# ============================================================================

AUTH_USER_MODEL = 'users.User'  # Custom user model (rol + email)

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 12}},
]

# Django custom User lives at apps/users/models.py
# Roles: admin | supervisor | analista
# Auth flow: User se crea vía /api/admin/auth/exchange desde FastAPI JWT

# ============================================================================
# DRF
# ============================================================================

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        # ADR-0017: JWTAuthentication se agrega ANTES de TokenAuthentication.
        # Es aditivo, no reemplaza — DRF prueba cada clase en orden hasta que
        # una produzca una credencial válida. auth_exchange (Token) sigue
        # funcionando sin cambios.
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.TokenAuthentication',  # Django Token (exchange F0)
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
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.ScopedRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'admin_users': env('ADMIN_API_RATE_LIMIT', '60/min'),
        'auth_exchange': '10/min',
        'login': '10/min',
    },
}

# ============================================================================
# Auth Bridge (F0) — secret compartido con FastAPI (ver nota de desactualización
# en docs/AUTH_BRIDGE.md — ADR-0017 introduce el login primario, ver bloque siguiente)
# ============================================================================

AUTH_BRIDGE_SECRET = env('AUTH_BRIDGE_SECRET', required=True)
AUTH_BRIDGE_ALGORITHM = 'HS256'
# Claims requeridos en el JWT FastAPI
AUTH_BRIDGE_REQUIRED_CLAIMS = ['sub', 'email', 'role', 'exp']
# Roles válidos (DRF los usa para validación adicional)
AUTH_BRIDGE_VALID_ROLES = ['analista', 'supervisor', 'admin']

# ============================================================================
# Login unificado (ADR-0017) — SimpleJWT con secret PROPIO
# ============================================================================

AUTH_ADMIN_JWT_SECRET = env('AUTH_ADMIN_JWT_SECRET', required=True)

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': AUTH_ADMIN_JWT_SECRET,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# ============================================================================
# django-auditlog
# ============================================================================

# Solo auditar cambios en apps locales (no Django core)
# django-auditlog espera formato (app_label, model_name) o dict por modelo.
# El registro efectivo se hace explícitamente en apps/users/models.py vía auditlog.register().
AUDITLOG_INCLUDE_TRACKING_MODELS = ()

# ============================================================================
# django-guardian
# ============================================================================

ANONYMOUS_USER_NAME = 'anonymous'

# django-guardian requiere su backend para usar object permissions
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'guardian.backends.ObjectPermissionBackend',
]

# ============================================================================
# CORS
# ============================================================================

CORS_ALLOWED_ORIGINS = [
    o.strip() for o in env('CORS_ALLOWED_ORIGINS',
                          'http://localhost:5173,http://localhost:3000').split(',')
    if o.strip()
]

# ============================================================================
# i18n
# ============================================================================

LANGUAGE_CODE = 'es-bo'
TIME_ZONE = 'America/La_Paz'
USE_I18N = True
USE_TZ = True

# ============================================================================
# Static files
# ============================================================================

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ============================================================================
# Logging
# ============================================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'apps': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
        },
        'auditlog': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    },
}