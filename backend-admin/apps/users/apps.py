from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.users'
    verbose_name = 'Usuarios institucionales'

    def ready(self):
        # Registrar signals si los hubiera (audit se hace via django-auditlog auto)
        pass