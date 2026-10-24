"""Tests del flujo del Supervisor S2 (ADR-0023 S2, DD-SUP-002).

Firma MFA delegada (admin_client mockeado): segregación (RN-06), gate del 5%,
lockout por 3 fallos, y transición a SIGNED + SIGN_REPORT.
"""
from decimal import Decimal

import pytest

from apps.samples import admin_client as admin_client_mod
from apps.samples.models import AuditEvent, Chromosome, Karyotype, Sample, SignLockout
from apps.samples.services import (
    AuditIncompleteError,
    MfaInvalidError,
    MfaLockedError,
    MfaNotEnrolledError,
    NotSignableError,
    SegregationError,
    decide_audit,
    select_audit_sample,
    sign_report,
)

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _mfa_ok(monkeypatch):
    """Por defecto el MFA verifica OK; cada test lo sobreescribe si necesita."""
    monkeypatch.setattr(admin_client_mod.admin_client, 'verify_mfa', lambda email, code: {'valid': True, 'enrolled': True})


def _mock_mfa(monkeypatch, valid=True, enrolled=True):
    monkeypatch.setattr(admin_client_mod.admin_client, 'verify_mfa', lambda email, code: {'valid': valid, 'enrolled': enrolled})


def _validated_case(analyst, audited=True):
    s = Sample.objects.create(
        chn_code=f'CHN-2026-07-24-{Sample.objects.count():04d}', analyst=analyst, status='ANALYST_VALIDATED',
    )
    k = Karyotype.objects.create(sample=s)
    for i in range(40):
        Chromosome.objects.create(karyotype=k, predicted_class=str((i % 22) + 1), position_index=i, confidence_score=Decimal('0.960'), order=i)
    return s


def _complete_audit(sample, reviewer):
    for r in select_audit_sample(sample):
        decide_audit(sample, r, reviewer, 'CONFIRMED')


class TestSignService:
    def test_sign_success(self, analyst_user, supervisor_user):
        s = _validated_case(analyst_user)
        _complete_audit(s, supervisor_user)
        sign_report(s, supervisor_user, '123456')
        s.refresh_from_db()
        assert s.status == 'SIGNED'
        assert s.signed_by_id == supervisor_user.id and s.signed_at is not None
        assert AuditEvent.objects.filter(sample=s, event_type='SIGN_REPORT').count() == 1

    def test_segregation_blocks_analyst_signer(self, supervisor_user):
        # El supervisor ES el analista del caso → RN-06.
        s = _validated_case(supervisor_user)
        _complete_audit(s, supervisor_user)
        with pytest.raises(SegregationError):
            sign_report(s, supervisor_user, '123456')

    def test_gate_blocks_incomplete_audit(self, analyst_user, supervisor_user):
        s = _validated_case(analyst_user)
        select_audit_sample(s)  # crea reviews PENDING, no decide
        with pytest.raises(AuditIncompleteError):
            sign_report(s, supervisor_user, '123456')

    def test_not_signable_when_not_validated(self, analyst_user, supervisor_user):
        s = _validated_case(analyst_user)
        s.status = 'READY'
        s.save(update_fields=['status'])
        with pytest.raises(NotSignableError):
            sign_report(s, supervisor_user, '123456')

    def test_not_enrolled(self, analyst_user, supervisor_user, monkeypatch):
        s = _validated_case(analyst_user)
        _complete_audit(s, supervisor_user)
        _mock_mfa(monkeypatch, enrolled=False)
        with pytest.raises(MfaNotEnrolledError):
            sign_report(s, supervisor_user, '123456')

    def test_invalid_mfa_increments_and_locks_after_three(self, analyst_user, supervisor_user, monkeypatch):
        s = _validated_case(analyst_user)
        _complete_audit(s, supervisor_user)
        _mock_mfa(monkeypatch, valid=False)
        for _ in range(3):
            with pytest.raises(MfaInvalidError):
                sign_report(s, supervisor_user, '000000')
        lockout = SignLockout.objects.get(user=supervisor_user)
        assert lockout.locked_until is not None
        # 4º intento → bloqueado aunque el código fuera válido.
        _mock_mfa(monkeypatch, valid=True)
        with pytest.raises(MfaLockedError):
            sign_report(s, supervisor_user, '123456')

    def test_success_resets_lockout(self, analyst_user, supervisor_user, monkeypatch):
        s = _validated_case(analyst_user)
        _complete_audit(s, supervisor_user)
        _mock_mfa(monkeypatch, valid=False)
        with pytest.raises(MfaInvalidError):
            sign_report(s, supervisor_user, '000000')
        _mock_mfa(monkeypatch, valid=True)
        sign_report(s, supervisor_user, '123456')
        assert SignLockout.objects.get(user=supervisor_user).failed_attempts == 0


class TestSignEndpoint:
    def _sign_url(self, s):
        return f'/api/clinic/samples/{s.id}/sign/'

    def test_supervisor_signs(self, supervisor_client, analyst_user, supervisor_user):
        s = _validated_case(analyst_user)
        _complete_audit(s, supervisor_user)
        resp = supervisor_client.post(self._sign_url(s), {'mfa_code': '123456'}, format='json')
        assert resp.status_code == 200
        assert resp.data['status'] == 'SIGNED'

    def test_gate_returns_409(self, supervisor_client, analyst_user):
        s = _validated_case(analyst_user)
        select_audit_sample(s)
        resp = supervisor_client.post(self._sign_url(s), {'mfa_code': '123456'}, format='json')
        assert resp.status_code == 409
        assert resp.data['code'] == 'AUDIT_INCOMPLETE'

    def test_invalid_mfa_returns_401(self, supervisor_client, analyst_user, supervisor_user, monkeypatch):
        s = _validated_case(analyst_user)
        _complete_audit(s, supervisor_user)
        _mock_mfa(monkeypatch, valid=False)
        resp = supervisor_client.post(self._sign_url(s), {'mfa_code': '000000'}, format='json')
        assert resp.status_code == 401
        assert resp.data['code'] == 'MFA_INVALID'

    def test_mfa_service_down_returns_503(self, supervisor_client, analyst_user, supervisor_user, monkeypatch):
        s = _validated_case(analyst_user)
        _complete_audit(s, supervisor_user)

        def _boom(email, code):
            raise admin_client_mod.MfaServiceError('down')
        monkeypatch.setattr(admin_client_mod.admin_client, 'verify_mfa', _boom)
        resp = supervisor_client.post(self._sign_url(s), {'mfa_code': '123456'}, format='json')
        assert resp.status_code == 503
        assert resp.data['code'] == 'MFA_SERVICE'

    def test_analyst_forbidden_by_permission(self, analyst_client, analyst_user):
        s = _validated_case(analyst_user)
        resp = analyst_client.post(self._sign_url(s), {'mfa_code': '123456'}, format='json')
        assert resp.status_code == 403
