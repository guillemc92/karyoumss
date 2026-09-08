"""Tests del servicio y endpoint ISCN — fase S3 (ADR-0023 D4, ADR-0025).

Lo que se protege acá: el gate de estado (solo se reporta lo firmado), la
inmutabilidad de RN-04, y que el override quede auditado. El motor puro se
prueba aparte en `test_iscn.py`.
"""
from decimal import Decimal

import pytest

from apps.samples.iscn import IscnError
from apps.samples.models import AuditEvent, Chromosome, Karyotype, Sample
from apps.samples.services import (
    IscnAlreadyGeneratedError,
    NotReportableError,
    generate_case_iscn,
)

pytestmark = pytest.mark.django_db


def _caso(analyst, status='SIGNED', trisomia=None, sexo='XY'):
    """Caso con un cariotipo completo de 46 cromosomas."""
    s = Sample.objects.create(
        chn_code=f'CHN-ISCN-{Sample.objects.count():04d}',
        analyst=analyst, status=status, sample_type='sangre',
    )
    k = Karyotype.objects.create(sample=s)
    orden = 0

    def _add(cls, n):
        nonlocal orden
        for i in range(n):
            Chromosome.objects.create(
                karyotype=k, predicted_class=cls, position_index=i,
                confidence_score=Decimal('0.950'), order=orden,
            )
            orden += 1

    for autosoma in [str(n) for n in range(1, 23)]:
        _add(autosoma, 3 if autosoma == trisomia else 2)
    if sexo == 'XX':
        _add('X', 2)
    else:
        _add('X', 1)
        _add('Y', 1)
    return s


class TestGeneracion:
    def test_cariotipo_normal(self, analyst_user, supervisor_user):
        s = _caso(analyst_user)
        generate_case_iscn(s, supervisor_user)
        s.refresh_from_db()
        assert s.iscn_nomenclature == '46,XY'
        assert s.status == 'REPORTED'
        assert s.iscn_generated_at is not None
        assert s.iscn_is_override is False

    def test_trisomia_21_detectada_del_conteo_real(self, analyst_user, supervisor_user):
        """El diagnóstico sale de los cromosomas validados, no de un parámetro."""
        s = _caso(analyst_user, trisomia='21')
        generate_case_iscn(s, supervisor_user)
        s.refresh_from_db()
        assert s.iscn_nomenclature == '47,XY,+21'

    def test_femenino(self, analyst_user, supervisor_user):
        s = _caso(analyst_user, sexo='XX')
        generate_case_iscn(s, supervisor_user)
        s.refresh_from_db()
        assert s.iscn_nomenclature == '46,XX'

    def test_ignora_los_cromosomas_desactivados(self, analyst_user, supervisor_user):
        """separar/unir (P3) desactiva sin borrar: no deben contarse."""
        s = _caso(analyst_user, trisomia='21')
        extra = Chromosome.objects.filter(karyotype__sample=s, predicted_class='21').first()
        extra.is_active = False
        extra.save(update_fields=['is_active'])
        generate_case_iscn(s, supervisor_user)
        s.refresh_from_db()
        assert s.iscn_nomenclature == '46,XY'   # vuelve a 2 copias del 21

    def test_la_generacion_normal_no_emite_evento(self, analyst_user, supervisor_user):
        """Solo el override se audita: es la excepción, no la regla (ADR-0023 D4)."""
        s = _caso(analyst_user)
        generate_case_iscn(s, supervisor_user)
        assert not AuditEvent.objects.filter(sample=s, event_type='ISCN_OVERRIDE').exists()


class TestGateDeEstado:
    """El ISCN se reporta DESPUÉS de la firma del Supervisor (ADR-0025 D5)."""

    @pytest.mark.parametrize('estado', [
        'PENDING_AI', 'READY', 'IN_ANALYSIS', 'ANALYST_VALIDATED', 'REPORTED',
    ])
    def test_rechaza_si_no_esta_firmado(self, analyst_user, supervisor_user, estado):
        s = _caso(analyst_user, status=estado)
        with pytest.raises(NotReportableError):
            generate_case_iscn(s, supervisor_user)

    def test_caso_sin_cromosomas_no_inventa_un_iscn(self, analyst_user, supervisor_user):
        s = Sample.objects.create(
            chn_code='CHN-ISCN-VACIO', analyst=analyst_user, status='SIGNED')
        with pytest.raises(IscnError, match='sin cromosomas'):
            generate_case_iscn(s, supervisor_user)


class TestInmutabilidadRN04:
    def test_regenerar_sin_override_es_rechazado(self, analyst_user, supervisor_user):
        s = _caso(analyst_user)
        generate_case_iscn(s, supervisor_user)
        s.refresh_from_db()
        s.status = 'SIGNED'          # aun volviendo al estado firmado
        s.save(update_fields=['status'])
        with pytest.raises(IscnAlreadyGeneratedError):
            generate_case_iscn(s, supervisor_user)

    def test_el_iscn_no_cambia_tras_un_intento_fallido(self, analyst_user, supervisor_user):
        s = _caso(analyst_user)
        generate_case_iscn(s, supervisor_user)
        s.refresh_from_db()
        original = s.iscn_nomenclature
        s.status = 'SIGNED'
        s.save(update_fields=['status'])
        with pytest.raises(IscnAlreadyGeneratedError):
            generate_case_iscn(s, supervisor_user)
        s.refresh_from_db()
        assert s.iscn_nomenclature == original


class TestOverride:
    def test_impone_el_string_del_supervisor(self, analyst_user, supervisor_user):
        s = _caso(analyst_user)
        generate_case_iscn(s, supervisor_user,
                           override='46,XY,del(5p)', justification='Deleción visible en bandeo G')
        s.refresh_from_db()
        assert s.iscn_nomenclature == '46,XY,del(5p)'
        assert s.iscn_is_override is True

    def test_deja_traza_con_el_original_y_la_justificacion(self, analyst_user, supervisor_user):
        s = _caso(analyst_user)
        generate_case_iscn(s, supervisor_user,
                           override='46,XY,del(5p)', justification='Deleción visible')
        ev = AuditEvent.objects.get(sample=s, event_type='ISCN_OVERRIDE')
        assert ev.payload['original_iscn'] == '46,XY'      # lo que el motor calculó
        assert ev.payload['final_iscn'] == '46,XY,del(5p)'
        assert ev.payload['justification'] == 'Deleción visible'
        assert ev.actor_id == supervisor_user.id
        assert len(ev.current_hash) == 64                   # encadenado (ADR-0022)

    def test_exige_justificacion(self, analyst_user, supervisor_user):
        """Sobrescribir un diagnóstico sin explicar por qué no es auditable."""
        s = _caso(analyst_user)
        with pytest.raises(IscnError, match='justificación'):
            generate_case_iscn(s, supervisor_user, override='46,XY,del(5p)')

    def test_rechaza_gramatica_invalida(self, analyst_user, supervisor_user):
        s = _caso(analyst_user)
        with pytest.raises(IscnError):
            generate_case_iscn(s, supervisor_user, override='no es un iscn', justification='x')

    def test_permite_corregir_un_iscn_ya_generado(self, analyst_user, supervisor_user):
        """RN-04 no congela el dato: lo hace inmutable SIN justificación."""
        s = _caso(analyst_user)
        generate_case_iscn(s, supervisor_user)
        s.refresh_from_db()
        s.status = 'SIGNED'
        s.save(update_fields=['status'])
        generate_case_iscn(s, supervisor_user, override='47,XY,+21', justification='Recuento revisado')
        s.refresh_from_db()
        assert s.iscn_nomenclature == '47,XY,+21'


class TestModoDegradado:
    def test_propaga_el_modo_al_evento(self, analyst_user, supervisor_user):
        s = _caso(analyst_user)
        generate_case_iscn(s, supervisor_user, override='46,XY,inv(9)',
                           justification='Variante', mode='degradado')
        ev = AuditEvent.objects.get(sample=s, event_type='ISCN_OVERRIDE')
        assert ev.mode == 'degradado'


class TestEndpoint:
    def _url(self, s):
        return f'/api/clinic/samples/{s.id}/iscn/'

    def test_genera_y_devuelve_el_iscn(self, supervisor_client, supervisor_user):
        s = _caso(supervisor_user, trisomia='21')
        r = supervisor_client.post(self._url(s), {}, format='json')
        assert r.status_code == 200
        assert r.data['iscn_nomenclature'] == '47,XY,+21'
        assert r.data['status'] == 'REPORTED'
        assert r.data['is_override'] is False

    def test_no_reportable_da_409(self, supervisor_client, supervisor_user):
        s = _caso(supervisor_user, status='ANALYST_VALIDATED')
        r = supervisor_client.post(self._url(s), {}, format='json')
        assert r.status_code == 409
        assert r.data['code'] == 'NOT_REPORTABLE'

    def test_regenerar_da_409(self, supervisor_client, supervisor_user):
        s = _caso(supervisor_user)
        supervisor_client.post(self._url(s), {}, format='json')
        s.refresh_from_db()
        s.status = 'SIGNED'
        s.save(update_fields=['status'])
        r = supervisor_client.post(self._url(s), {}, format='json')
        assert r.status_code == 409
        assert r.data['code'] == 'ISCN_ALREADY_GENERATED'

    def test_override_invalido_da_400(self, supervisor_client, supervisor_user):
        s = _caso(supervisor_user)
        r = supervisor_client.post(
            self._url(s), {'override': 'basura', 'justification': 'x'}, format='json')
        assert r.status_code == 400
        assert r.data['code'] == 'INVALID_ISCN'

    def test_no_hay_patch(self, supervisor_client, supervisor_user):
        """RN-04 / prohibición explícita de CLAUDE.md."""
        s = _caso(supervisor_user)
        assert supervisor_client.patch(self._url(s), {'iscn_nomenclature': '46,XX'},
                                       format='json').status_code == 405

    def test_el_analista_no_puede_reportar(self, analyst_client, analyst_user):
        s = _caso(analyst_user)
        assert analyst_client.post(self._url(s), {}, format='json').status_code == 403

    def test_anonimo_rechazado(self, supervisor_user):
        from rest_framework.test import APIClient
        s = _caso(supervisor_user)
        # Medido: el endpoint devuelve 401 de forma determinista. El
        # `in (401, 403)` que habia aqui aceptaba un codigo que el sistema
        # nunca produce, asi que habria seguido verde si la autenticacion
        # pasara a 403 — que significa otra cosa (credencial valida sin
        # permiso, no ausencia de credencial).
        assert APIClient().post(self._url(s), {}, format='json').status_code == 401
