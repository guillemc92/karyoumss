"""Girar 180° y voltear en el cariograma (DD-KARYO-007 D7, T7).

Se fija:
- la orientación va a `measures['orientacion']` y NO toca `bbox` ni `contour`;
- emite ORIENT con la de antes y la de después;
- valores fuera de {0, 180} / no booleanos → 400; caso validado 409; ajeno 403;
- no es deshacible: «Deshacer» la salta y sigue apuntando a la última edición.
"""
from decimal import Decimal

import pytest

from apps.samples.models import AuditEvent, AuditEventType, Chromosome, Karyotype, Sample
from apps.samples.services import (
    CaseLockedError, ObjetoInactivoError, orient_chromosome, reject_object, ultima_edicion_deshacible,
)

pytestmark = pytest.mark.django_db

CAJA = {'x': 10, 'y': 20, 'w': 30, 'h': 90}
SILUETA = [[10, 20], [40, 20], [40, 110], [10, 110]]


def _caso(dueno, chn, status='READY'):
    s = Sample.objects.create(chn_code=chn, patient_ref='ANON', analyst=dueno, status=status)
    return s, Karyotype.objects.create(sample=s, model_version='test-v0')


def _crom(k, activo=True, measures=None):
    return Chromosome.objects.create(
        karyotype=k, predicted_class='1', position_index=0, order=0, is_active=activo,
        confidence_score=Decimal('0.950'), bbox=dict(CAJA), contour=SILUETA,
        measures=measures if measures is not None else {'length_um': 5.2},
    )


class TestServicio:
    def test_guarda_la_orientacion_sin_tocar_caja_ni_silueta(self, analyst_user):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0401')
        c = _crom(k)
        orient_chromosome(s, c, 180, True, analyst_user)
        c.refresh_from_db()
        assert c.measures == {'length_um': 5.2, 'orientacion': {'giro': 180, 'volteo': True}}
        assert c.bbox == CAJA and c.contour == SILUETA

    def test_evento_con_la_de_antes_y_la_de_despues(self, analyst_user):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0402')
        c = _crom(k)
        orient_chromosome(s, c, 180, False, analyst_user)
        orient_chromosome(s, c, 180, True, analyst_user)
        eventos = list(AuditEvent.objects.filter(sample=s, event_type=AuditEventType.ORIENT).order_by('created_at'))
        assert [e.payload for e in eventos] == [
            {'previa': {'giro': 0, 'volteo': False}, 'nueva': {'giro': 180, 'volteo': False}},
            {'previa': {'giro': 180, 'volteo': False}, 'nueva': {'giro': 180, 'volteo': True}},
        ]

    def test_measures_vacio(self, analyst_user):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0403')
        c = _crom(k, measures={})
        orient_chromosome(s, c, 0, True, analyst_user)
        c.refresh_from_db()
        assert c.measures == {'orientacion': {'giro': 0, 'volteo': True}}

    @pytest.mark.parametrize('giro, volteo', [(90, False), (None, False), (True, False), (0, 'si'), (180, None)])
    def test_valores_invalidos(self, analyst_user, giro, volteo):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0404')
        c = _crom(k)
        with pytest.raises(ValueError):
            orient_chromosome(s, c, giro, volteo, analyst_user)
        assert not AuditEvent.objects.filter(sample=s).exists()

    def test_descartado(self, analyst_user):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0405')
        with pytest.raises(ObjetoInactivoError):
            orient_chromosome(s, _crom(k, activo=False), 180, False, analyst_user)

    def test_caso_validado(self, analyst_user):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0406', status='ANALYST_VALIDATED')
        with pytest.raises(CaseLockedError):
            orient_chromosome(s, _crom(k), 180, False, analyst_user)

    def test_deshacer_salta_la_orientacion(self, analyst_user):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0407')
        a, b = _crom(k), _crom(k)
        reject_object(s, a, 'otro', analyst_user)
        orient_chromosome(s, b, 180, False, analyst_user)
        assert ultima_edicion_deshacible(s, analyst_user)['tipo'] == 'REJECT_OBJECT'


@pytest.fixture
def otro_analista(django_user_model):
    return django_user_model.objects.create_user(username='otra_analista_orientar', password='x')


def _url(s, c):
    return f'/api/clinic/samples/{s.id}/chromosomes/{c.id}/orient/'


class TestVista:
    def test_200_y_el_cariotipo_la_sirve(self, analyst_client, analyst_user):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0411')
        c = _crom(k)
        r = analyst_client.post(_url(s, c), {'giro': 180, 'volteo': False}, format='json')
        assert r.status_code == 200
        assert r.data['measures']['orientacion'] == {'giro': 180, 'volteo': False}
        cariotipo = analyst_client.get(f'/api/clinic/samples/{s.id}/karyotype/').data
        assert cariotipo['chromosomes'][0]['measures']['orientacion'] == {'giro': 180, 'volteo': False}

    @pytest.mark.parametrize('cuerpo', [{}, {'giro': 90, 'volteo': False}, {'giro': 0, 'volteo': 1}])
    def test_400(self, analyst_client, analyst_user, cuerpo):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0412')
        r = analyst_client.post(_url(s, _crom(k)), cuerpo, format='json')
        assert r.status_code == 400
        assert r.data['code'] == 'VALIDATION_ERROR'

    def test_409(self, analyst_client, analyst_user):
        s, k = _caso(analyst_user, 'CHN-2026-10-23-0413')
        r = analyst_client.post(_url(s, _crom(k, activo=False)), {'giro': 0, 'volteo': True}, format='json')
        assert r.data['code'] == 'OBJECT_INACTIVE'
        s2, k2 = _caso(analyst_user, 'CHN-2026-10-23-0414', status='VALIDATED')
        r = analyst_client.post(_url(s2, _crom(k2)), {'giro': 0, 'volteo': True}, format='json')
        assert r.status_code == 409 and r.data['code'] == 'CASE_LOCKED'

    def test_analista_ajeno_403(self, analyst_client, otro_analista):
        s, k = _caso(otro_analista, 'CHN-2026-10-23-0415')
        r = analyst_client.post(_url(s, _crom(k)), {'giro': 180, 'volteo': False}, format='json')
        assert r.status_code == 403
