"""
Tests de la señal de auditoría (django-auditlog) para AdminUser y User.

Verifica que las operaciones CRUD en los modelos registrados generan
LogEntry Append-Only con los campos correctos.
"""
import pytest
from auditlog.models import LogEntry


pytestmark = pytest.mark.django_db


class TestAdminUserAudit:
    def test_create_generates_log_entry(self):
        from apps.users.factories import AdminUserFactory
        u = AdminUserFactory(email='audit-create@biomed.umss.bo')
        entries = LogEntry.objects.filter(object_pk=str(u.pk), content_type__model='adminuser')
        assert entries.count() == 1
        assert entries.first().action == 0  # create

    def test_update_generates_log_entry(self):
        from apps.users.factories import AdminUserFactory
        u = AdminUserFactory(email='audit-update@biomed.umss.bo')
        u.full_name = 'Nombre Cambiado'
        u.save()
        entries = LogEntry.objects.filter(
            object_pk=str(u.pk),
            content_type__model='adminuser',
            action=1,  # update
        )
        assert entries.count() >= 1

    def test_soft_delete_generates_log_entry(self):
        from apps.users.factories import AdminUserFactory
        from apps.users.services import soft_delete_admin_user
        u = AdminUserFactory(email='audit-delete@biomed.umss.bo')
        soft_delete_admin_user(u)
        # La columna active cambió de True→False → genera update log entry
        entries = LogEntry.objects.filter(
            object_pk=str(u.pk),
            content_type__model='adminuser',
        )
        # Al menos 2 entradas: create + update
        assert entries.count() >= 2

    def test_log_entry_records_changes(self):
        from apps.users.factories import AdminUserFactory
        u = AdminUserFactory(email='audit-changes@biomed.umss.bo')
        u.role = 'supervisor'
        u.save()
        updates = LogEntry.objects.filter(
            object_pk=str(u.pk),
            content_type__model='adminuser',
            action=1,
        ).order_by('-timestamp')
        assert updates.exists()
        latest = updates.first()
        # changes es un JSONField: dict {field: [old, new]}
        changes = latest.changes
        assert changes is not None
        assert 'role' in changes
        assert changes['role'] == ['analista', 'supervisor']


class TestUserAudit:
    def test_user_creation_generates_log_entry(self, auth_user):
        # auth_user ya fue creado en el fixture
        entries = LogEntry.objects.filter(
            object_pk=str(auth_user.pk),
            content_type__model='user',
        )
        # django-auditlog registra creación
        assert entries.filter(action=0).exists()

    def test_user_role_change_audited(self, auth_user):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        auth_user.role = 'supervisor'
        auth_user.save()
        updates = LogEntry.objects.filter(
            object_pk=str(auth_user.pk),
            content_type__model='user',
            action=1,
        )
        assert updates.exists()