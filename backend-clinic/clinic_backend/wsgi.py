"""
WSGI config for clinic_backend project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_backend.settings')

# DD-OBS-001: las trazas se encienden antes de crear la aplicación, porque Django
# lee la lista de middlewares en ese momento. Sin OTEL_EXPORTER_OTLP_ENDPOINT no
# hace nada. Con gunicorn sin --preload, esto corre en cada worker, después del
# fork: el hilo del exportador nace en el proceso que lo usa.
from clinic_backend import observabilidad  # noqa: E402

observabilidad.configurar('backend-clinic')

application = get_wsgi_application()
