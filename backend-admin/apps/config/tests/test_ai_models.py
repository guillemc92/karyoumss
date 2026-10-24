"""
Tests de Modelo IA (P3 — DD-ADMIN-002 §4, ADR-0014).

Cobertura objetivo (RN-09): ≥90% lines/branches en las porciones nuevas
de apps/config/models.py, serializers.py, views.py.

Cubre (DD §4.7 + adicionales):
- test_singleton_constraint_prevents_two_active
- test_confidence_below_0_85_sets_compliance_warning
- test_patch_requires_admin_role
- test_metrics_endpoint_filters_by_days
- test_metrics_append_only_no_patch_no_delete
- Serializers: validate_confidence_threshold/detection_sensitivity,
  compliance_warning read-only
- Views: GET crea singleton (get_or_create), GET/PATCH sin auth → 401,
  POST metric crea snapshot, GET latest 204 sin datos, days clamping
  (<1 y >365), health_view sections incluye 'modelos'
"""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.config.models import ModelConfig, ModelMetric
from apps.config.serializers import ModelConfigSerializer, ModelMetricSerializer


pytestmark = pytest.mark.django_db

MODELS_ACTIVE_URL = '/api/admin/models/active/'
MODELS_METRICS_URL = '/api/admin/models/metrics/'
MODELS_METRICS_LATEST_URL = '/api/admin/models/metrics/latest/'


def _metric_payload(**overrides):
    payload = {
        'measured_at': timezone.now().isoformat(),
        'precision_overall': '0.9720',
        'recall_overall': '0.9680',
        'f1_overall': '0.9690',
        'latency_p50_ms': 92,
        'latency_p95_ms': 150,
        'latency_p99_ms': 210,
        'samples_evaluated': 500,
    }
    payload.update(overrides)
    return payload


# =============================================================================
# Model ModelConfig
# =============================================================================
class TestModelConfig:
    def test_singleton_constraint_prevents_two_active(self):
        ModelConfig.objects.create(is_active=True)
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                ModelConfig.objects.create(is_active=True)

    def test_two_inactive_rows_allowed(self):
        ModelConfig.objects.create(is_active=False)
        ModelConfig.objects.create(is_active=False)
        assert ModelConfig.objects.filter(is_active=False).count() == 2

    def test_compliance_warning_true_below_threshold(self):
        config = ModelConfig(confidence_threshold=Decimal('0.700'))
        assert config.compliance_warning is True

    def test_compliance_warning_false_at_or_above_threshold(self):
        config = ModelConfig(confidence_threshold=Decimal('0.850'))
        assert config.compliance_warning is False
        config2 = ModelConfig(confidence_threshold=Decimal('0.900'))
        assert config2.compliance_warning is False

    def test_str_representation(self):
        config = ModelConfig(unet_version='u-net-v9', classifier_version='effnet-v9', is_active=True)
        assert 'u-net-v9' in str(config)
        assert 'effnet-v9' in str(config)

    def test_invalid_analysis_mode_rejected_by_constraint(self):
        config = ModelConfig(analysis_mode='invalid-mode')
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                config.save()

    def test_confidence_out_of_range_rejected_by_constraint(self):
        config = ModelConfig(confidence_threshold=Decimal('1.500'))
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                config.save()


class TestModelMetric:
    def test_str_representation(self):
        m = ModelMetric(
            measured_at=timezone.now(), precision_overall=Decimal('0.97'),
            recall_overall=Decimal('0.96'), f1_overall=Decimal('0.965'),
            latency_p50_ms=90, latency_p95_ms=140, latency_p99_ms=200,
            samples_evaluated=100,
        )
        assert 'precision=0.97' in str(m)

    def test_ordering_most_recent_first(self):
        older = ModelMetric.objects.create(**{
            **_metric_payload(measured_at=timezone.now() - timedelta(days=5)),
        })
        newer = ModelMetric.objects.create(**_metric_payload())
        entries = list(ModelMetric.objects.all())
        assert entries[0].pk == newer.pk
        assert entries[1].pk == older.pk


# =============================================================================
# Serializers
# =============================================================================
class TestModelConfigSerializer:
    def test_compliance_warning_reflects_model_property(self):
        config = ModelConfig(confidence_threshold=Decimal('0.700'))
        data = ModelConfigSerializer(config).data
        assert data['compliance_warning'] is True

    def test_validate_confidence_threshold_rejects_out_of_range(self):
        s = ModelConfigSerializer(data={'confidence_threshold': '1.5'}, partial=True)
        assert not s.is_valid()
        assert 'confidence_threshold' in s.errors

    def test_validate_detection_sensitivity_rejects_out_of_range(self):
        s = ModelConfigSerializer(data={'detection_sensitivity': '-0.1'}, partial=True)
        assert not s.is_valid()
        assert 'detection_sensitivity' in s.errors

    def test_is_active_is_read_only(self):
        config = ModelConfig.objects.create(is_active=True)
        s = ModelConfigSerializer(config, data={'is_active': False}, partial=True)
        s.is_valid(raise_exception=True)
        assert 'is_active' not in s.validated_data


class TestModelMetricSerializer:
    def test_serializes_all_fields(self):
        m = ModelMetric.objects.create(**_metric_payload())
        data = ModelMetricSerializer(m).data
        assert data['precision_overall'] == '0.9720'
        assert data['samples_evaluated'] == 500

    def test_rejects_missing_required_field(self):
        payload = _metric_payload()
        del payload['precision_overall']
        s = ModelMetricSerializer(data=payload)
        assert not s.is_valid()
        assert 'precision_overall' in s.errors


# =============================================================================
# Views — ModelConfigView
# =============================================================================
class TestModelConfigView:
    def test_get_creates_singleton_if_missing(self, admin_client):
        assert not ModelConfig.objects.exists()
        resp = admin_client.get(MODELS_ACTIVE_URL)
        assert resp.status_code == 200
        body = resp.json()
        assert body['unet_version'] == 'u-net-v2.1'
        assert body['classifier_version'] == 'efficientnet-b3-v1.4'
        assert ModelConfig.objects.filter(is_active=True).count() == 1

    def test_get_idempotent(self, admin_client):
        admin_client.get(MODELS_ACTIVE_URL)
        admin_client.get(MODELS_ACTIVE_URL)
        assert ModelConfig.objects.count() == 1

    def test_patch_updates_confidence_threshold(self, admin_client):
        resp = admin_client.patch(MODELS_ACTIVE_URL, {'confidence_threshold': '0.900'}, format='json')
        assert resp.status_code == 200
        assert resp.json()['confidence_threshold'] == '0.900'

    def test_patch_updates_detection_sensitivity(self, admin_client):
        resp = admin_client.patch(MODELS_ACTIVE_URL, {'detection_sensitivity': '0.600'}, format='json')
        assert resp.status_code == 200
        assert resp.json()['detection_sensitivity'] == '0.600'

    def test_confidence_below_0_85_sets_compliance_warning(self, admin_client):
        resp = admin_client.patch(MODELS_ACTIVE_URL, {'confidence_threshold': '0.700'}, format='json')
        assert resp.status_code == 200
        assert resp.json()['compliance_warning'] is True

    def test_confidence_at_0_85_no_compliance_warning(self, admin_client):
        resp = admin_client.patch(MODELS_ACTIVE_URL, {'confidence_threshold': '0.850'}, format='json')
        assert resp.status_code == 200
        assert resp.json()['compliance_warning'] is False

    def test_patch_sets_updated_by(self, admin_client, auth_user):
        resp = admin_client.patch(MODELS_ACTIVE_URL, {'analysis_mode': 'fast'}, format='json')
        assert resp.status_code == 200
        config = ModelConfig.objects.get(is_active=True)
        assert config.updated_by_id == auth_user.id

    def test_patch_invalid_analysis_mode_rejected(self, admin_client):
        resp = admin_client.patch(MODELS_ACTIVE_URL, {'analysis_mode': 'ultra'}, format='json')
        assert resp.status_code == 400
        assert 'analysis_mode' in resp.json()

    def test_patch_requires_admin_role(self, supervisor_client):
        resp = supervisor_client.patch(MODELS_ACTIVE_URL, {'analysis_mode': 'fast'}, format='json')
        assert resp.status_code == 403

    def test_get_allowed_for_non_admin_authenticated(self, supervisor_client):
        # IsAdminRole: SAFE_METHODS abiertos a cualquier autenticado.
        resp = supervisor_client.get(MODELS_ACTIVE_URL)
        assert resp.status_code == 200

    def test_get_without_auth_returns_401(self, anon_client):
        resp = anon_client.get(MODELS_ACTIVE_URL)
        assert resp.status_code == 401

    def test_patch_without_auth_returns_401(self, anon_client):
        resp = anon_client.patch(MODELS_ACTIVE_URL, {'analysis_mode': 'fast'}, format='json')
        assert resp.status_code == 401


# =============================================================================
# Views — ModelMetricListCreateView / ModelMetricLatestView
# =============================================================================
class TestModelMetricViews:
    def test_post_creates_snapshot(self, admin_client):
        resp = admin_client.post(MODELS_METRICS_URL, _metric_payload(), format='json')
        assert resp.status_code == 201
        assert ModelMetric.objects.count() == 1

    def test_post_requires_admin_role(self, supervisor_client):
        resp = supervisor_client.post(MODELS_METRICS_URL, _metric_payload(), format='json')
        assert resp.status_code == 403

    def test_metrics_append_only_no_patch_no_delete(self, admin_client):
        m = ModelMetric.objects.create(**_metric_payload())
        detail_url = f'{MODELS_METRICS_URL}{m.pk}/'
        resp = admin_client.patch(detail_url, {'samples_evaluated': 999}, format='json')
        assert resp.status_code == 404  # no hay ruta de detalle: no expuesto
        resp = admin_client.delete(detail_url)
        assert resp.status_code == 404

    def test_metrics_endpoint_filters_by_days(self, admin_client):
        ModelMetric.objects.create(**_metric_payload(measured_at=timezone.now() - timedelta(days=40)))
        ModelMetric.objects.create(**_metric_payload(measured_at=timezone.now() - timedelta(days=5)))
        resp = admin_client.get(f'{MODELS_METRICS_URL}?days=30')
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_metrics_days_param_clamped_below_minimum(self, admin_client):
        ModelMetric.objects.create(**_metric_payload())
        resp = admin_client.get(f'{MODELS_METRICS_URL}?days=0')
        assert resp.status_code == 200
        assert len(resp.json()) == 1  # clamped a 1, sigue incluyendo snapshot de hoy

    def test_metrics_days_param_clamped_above_maximum(self, admin_client):
        ModelMetric.objects.create(**_metric_payload(measured_at=timezone.now() - timedelta(days=400)))
        resp = admin_client.get(f'{MODELS_METRICS_URL}?days=9999')
        assert resp.status_code == 200
        assert len(resp.json()) == 0  # 400 días > 365 clamp → sigue fuera de rango

    def test_metrics_days_param_non_numeric_falls_back_to_default(self, admin_client):
        ModelMetric.objects.create(**_metric_payload())
        resp = admin_client.get(f'{MODELS_METRICS_URL}?days=abc')
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_latest_returns_204_when_empty(self, admin_client):
        resp = admin_client.get(MODELS_METRICS_LATEST_URL)
        assert resp.status_code == 204

    def test_latest_returns_most_recent(self, admin_client):
        ModelMetric.objects.create(**_metric_payload(measured_at=timezone.now() - timedelta(days=10)))
        newest = ModelMetric.objects.create(**_metric_payload())
        resp = admin_client.get(MODELS_METRICS_LATEST_URL)
        assert resp.status_code == 200
        assert resp.json()['id'] == newest.pk

    def test_metrics_list_without_auth_returns_401(self, anon_client):
        resp = anon_client.get(MODELS_METRICS_URL)
        assert resp.status_code == 401


# =============================================================================
# config_health_view — sections incluye 'modelos'
# =============================================================================
def test_health_view_includes_modelos_section(admin_client):
    resp = admin_client.get('/api/admin/config/health/')
    assert resp.status_code == 200
    assert 'modelos' in resp.json()['sections']


def test_validation_error_response_without_message_dict_uses_detail():
    """_validation_error_response (compartido por P2/P3): rama fallback
    para un ValidationError sin message_dict (lista/string plano)."""
    from django.core.exceptions import ValidationError
    from apps.config.views import _validation_error_response

    resp = _validation_error_response(ValidationError('Mensaje plano'))
    assert resp.status_code == 400
    assert resp.data == {'detail': ['Mensaje plano']}
