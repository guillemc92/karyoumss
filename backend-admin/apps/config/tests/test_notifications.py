"""
Tests de Notificaciones (P4 — DD-ADMIN-002 §5, ADR-0014).

Cobertura objetivo (RN-09): ≥90% lines/branches en las porciones nuevas
de apps/config/models.py, serializers.py, views.py.

Cubre (DD §5.5 + adicionales):
- get_or_create idempotente (incluye el fix de formato de tiempo:
  refresh_from_db tras creación para que quiet_hours_start/end no
  queden como string crudo del default)
- PATCH parcial (email/inapp booleans, quiet_hours)
- Views: GET/PATCH sin auth → 401, health_view sections incluye
  'notifications'
"""
from __future__ import annotations

import pytest

from apps.config.models import NotificationPreference
from apps.config.serializers import NotificationPreferenceSerializer


pytestmark = pytest.mark.django_db

ME_NOTIFICATIONS_URL = '/api/admin/me/notifications/'


# =============================================================================
# Model NotificationPreference
# =============================================================================
class TestNotificationPreferenceModel:
    def test_str_representation(self, auth_user):
        prefs = NotificationPreference.objects.create(user=auth_user)
        assert auth_user.email in str(prefs)

    def test_defaults(self, auth_user):
        prefs = NotificationPreference.objects.create(user=auth_user)
        # Los defaults de TimeField quedan como string crudo en la instancia
        # recién creada hasta el próximo round-trip a la DB (mismo quirk que
        # motiva el refresh_from_db() en MeNotificationsView.get_object).
        prefs.refresh_from_db()
        assert prefs.email_review_pending is True
        assert prefs.email_training_completed is False
        assert prefs.inapp_training_completed is True
        assert prefs.quiet_hours_enabled is False
        assert str(prefs.quiet_hours_start) == '20:00:00'
        assert str(prefs.quiet_hours_end) == '07:00:00'

    def test_one_to_one_constraint(self, auth_user):
        from django.db import IntegrityError, transaction
        NotificationPreference.objects.create(user=auth_user)
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                NotificationPreference.objects.create(user=auth_user)


# =============================================================================
# Serializer
# =============================================================================
class TestNotificationPreferenceSerializer:
    def test_serializes_all_fields(self, auth_user):
        prefs = NotificationPreference.objects.create(user=auth_user)
        prefs.refresh_from_db()
        data = NotificationPreferenceSerializer(prefs).data
        assert data['email_review_pending'] is True
        assert data['quiet_hours_start'] == '20:00:00'

    def test_id_and_updated_at_read_only(self, auth_user):
        prefs = NotificationPreference.objects.create(user=auth_user)
        s = NotificationPreferenceSerializer(
            prefs, data={'id': '00000000-0000-0000-0000-000000000000'}, partial=True,
        )
        s.is_valid(raise_exception=True)
        assert 'id' not in s.validated_data


# =============================================================================
# View MeNotificationsView
# =============================================================================
class TestMeNotificationsView:
    def test_get_creates_preferences_if_missing(self, admin_client, auth_user):
        assert not NotificationPreference.objects.filter(user=auth_user).exists()
        resp = admin_client.get(ME_NOTIFICATIONS_URL)
        assert resp.status_code == 200
        assert NotificationPreference.objects.filter(user=auth_user).exists()

    def test_get_idempotent(self, admin_client, auth_user):
        admin_client.get(ME_NOTIFICATIONS_URL)
        admin_client.get(ME_NOTIFICATIONS_URL)
        assert NotificationPreference.objects.filter(user=auth_user).count() == 1

    def test_get_on_creation_returns_normalized_time_format(self, admin_client):
        """Regresión: la primera creación (get_or_create) no debe devolver
        el string crudo del default ('20:00') sin segundos."""
        resp = admin_client.get(ME_NOTIFICATIONS_URL)
        assert resp.status_code == 200
        assert resp.json()['quiet_hours_start'] == '20:00:00'
        assert resp.json()['quiet_hours_end'] == '07:00:00'

    def test_patch_updates_email_preference(self, admin_client):
        resp = admin_client.patch(ME_NOTIFICATIONS_URL, {'email_training_completed': True}, format='json')
        assert resp.status_code == 200
        assert resp.json()['email_training_completed'] is True

    def test_patch_updates_quiet_hours(self, admin_client):
        resp = admin_client.patch(ME_NOTIFICATIONS_URL, {
            'quiet_hours_enabled': True,
            'quiet_hours_start': '22:00:00',
            'quiet_hours_end': '06:30:00',
        }, format='json')
        assert resp.status_code == 200
        body = resp.json()
        assert body['quiet_hours_enabled'] is True
        assert body['quiet_hours_start'] == '22:00:00'
        assert body['quiet_hours_end'] == '06:30:00'

    def test_patch_persists_to_db(self, admin_client, auth_user):
        admin_client.patch(ME_NOTIFICATIONS_URL, {'inapp_system_errors': False}, format='json')
        prefs = NotificationPreference.objects.get(user=auth_user)
        assert prefs.inapp_system_errors is False

    def test_get_without_auth_returns_401(self, anon_client):
        resp = anon_client.get(ME_NOTIFICATIONS_URL)
        assert resp.status_code == 401

    def test_patch_without_auth_returns_401(self, anon_client):
        resp = anon_client.patch(ME_NOTIFICATIONS_URL, {'email_review_pending': False}, format='json')
        assert resp.status_code == 401


def test_health_view_includes_notifications_section(admin_client):
    resp = admin_client.get('/api/admin/config/health/')
    assert resp.status_code == 200
    assert 'notifications' in resp.json()['sections']
