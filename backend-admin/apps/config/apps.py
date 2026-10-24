from django.apps import AppConfig


class ConfigConfig(AppConfig):
    """
    Panel Configuración del Sistema (DD-ADMIN-002).

    label='admin_config' se declara explícito para que coexista con
    apps.users y apps.audit sin colisión de labels en la tabla
    django_migrations.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.config'
    label = 'admin_config'
    verbose_name = 'Configuración del Sistema'

    def ready(self):
        # Registrar signals si los hubiera (audit se hace via django-auditlog auto).
        # Los modelos se importan explícitamente al final de apps.config.models
        # para que django-auditlog pueda descubrirlos en INSTALLED_APPS.
        from . import models  # noqa: F401
        # Registrar AdminProfile en django-auditlog (P1).
        # Se importa dentro de ready() para evitar ciclos en import time.
        from auditlog.registry import auditlog
        from .models import AdminProfile
        auditlog.register(
            AdminProfile,
            include_fields=['full_name', 'email', 'specialty',
                            'professional_license', 'phone', 'location',
                            'avatar_url'],
        )
