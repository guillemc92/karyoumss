"""
Tests de Apariencia (P6 — DD-ADMIN-002 §7, ADR-0014).

Cobertura objetivo (RN-09): ≥90% lines/branches en las porciones nuevas
de apps/config/models.py, serializers.py, views.py.

Cubre (DD §7.5 + adicionales):
- choices válidos (constraint DB + validación DRF)
- get_or_create idempotente
- PATCH parcial
- health_view sections incluye 'appearance'
"""
from __future__ import annotations

import pytest
from django.db import IntegrityError, transaction

from apps.config.models import AppearancePreference
from apps.config.serializers import AppearancePreferenceSerializer


pytestmark = pytest.mark.django_db

ME_APPEARANCE_URL = '/api/admin/me/appearance/'


class TestAppearancePreferenceModel:
    def test_defaults(self, auth_user):
        prefs = AppearancePreference.objects.create(user=auth_user)
        assert prefs.theme == 'light'
        assert prefs.density == 'comfortable'
        assert prefs.language == 'es'
        assert prefs.font_size == 'md'

    def test_str_representation(self, auth_user):
        prefs = AppearancePreference.objects.create(user=auth_user, theme='dark')
        assert auth_user.email in str(prefs)
        assert 'dark' in str(prefs)

    def test_one_to_one_constraint(self, auth_user):
        AppearancePreference.objects.create(user=auth_user)
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                AppearancePreference.objects.create(user=auth_user)

    def test_invalid_theme_rejected_by_constraint(self, auth_user):
        prefs = AppearancePreference(user=auth_user, theme='invalid')
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                prefs.save()

    def test_invalid_density_rejected_by_constraint(self, auth_user):
        prefs = AppearancePreference(user=auth_user, density='invalid')
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                prefs.save()

    def test_invalid_language_rejected_by_constraint(self, auth_user):
        prefs = AppearancePreference(user=auth_user, language='fr')
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                prefs.save()

    def test_invalid_font_size_rejected_by_constraint(self, auth_user):
        prefs = AppearancePreference(user=auth_user, font_size='xl')
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                prefs.save()


class TestAppearancePreferenceSerializer:
    def test_serializes_all_fields(self, auth_user):
        prefs = AppearancePreference.objects.create(user=auth_user, theme='dark', density='spacious')
        data = AppearancePreferenceSerializer(prefs).data
        assert data['theme'] == 'dark'
        assert data['density'] == 'spacious'

    def test_rejects_invalid_theme_choice(self):
        s = AppearancePreferenceSerializer(data={'theme': 'invalid'}, partial=True)
        assert not s.is_valid()
        assert 'theme' in s.errors

    def test_id_and_updated_at_read_only(self, auth_user):
        prefs = AppearancePreference.objects.create(user=auth_user)
        s = AppearancePreferenceSerializer(
            prefs, data={'id': '00000000-0000-0000-0000-000000000000'}, partial=True,
        )
        s.is_valid(raise_exception=True)
        assert 'id' not in s.validated_data


class TestMeAppearanceView:
    def test_get_creates_preferences_if_missing(self, admin_client, auth_user):
        assert not AppearancePreference.objects.filter(user=auth_user).exists()
        resp = admin_client.get(ME_APPEARANCE_URL)
        assert resp.status_code == 200
        assert resp.json()['theme'] == 'light'

    def test_get_idempotent(self, admin_client, auth_user):
        admin_client.get(ME_APPEARANCE_URL)
        admin_client.get(ME_APPEARANCE_URL)
        assert AppearancePreference.objects.filter(user=auth_user).count() == 1

    def test_patch_updates_theme_and_density(self, admin_client):
        resp = admin_client.patch(ME_APPEARANCE_URL, {'theme': 'dark', 'density': 'compact'}, format='json')
        assert resp.status_code == 200
        assert resp.json()['theme'] == 'dark'
        assert resp.json()['density'] == 'compact'

    def test_patch_invalid_theme_rejected(self, admin_client):
        resp = admin_client.patch(ME_APPEARANCE_URL, {'theme': 'invalid'}, format='json')
        assert resp.status_code == 400
        assert 'theme' in resp.json()

    def test_patch_persists_to_db(self, admin_client, auth_user):
        admin_client.patch(ME_APPEARANCE_URL, {'language': 'en'}, format='json')
        prefs = AppearancePreference.objects.get(user=auth_user)
        assert prefs.language == 'en'

    def test_get_without_auth_returns_401(self, anon_client):
        resp = anon_client.get(ME_APPEARANCE_URL)
        assert resp.status_code == 401

    def test_patch_without_auth_returns_401(self, anon_client):
        resp = anon_client.patch(ME_APPEARANCE_URL, {'theme': 'dark'}, format='json')
        assert resp.status_code == 401


def test_health_view_includes_appearance_section(admin_client):
    resp = admin_client.get('/api/admin/config/health/')
    assert resp.status_code == 200
    assert 'appearance' in resp.json()['sections']
