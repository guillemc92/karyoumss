"""DD-E3-001 T1 — la bitácora se lee por su interfaz.

Con `BITACORA_MODO=proceso` (el valor por omisión) la vista tiene que devolver
EXACTAMENTE lo que devolvía antes de existir la interfaz: lo que se compara es
la serialización directa de `sample.audit_events.all()`, el código de antes.
"""
import pytest

from apps.samples import bitacora as modulo_bitacora
from apps.samples.bitacora import BitacoraNoDisponible, bitacora
from apps.samples.bitacora.en_proceso import BitacoraEnProceso
from apps.samples.models import AuditEventType, Sample
from apps.samples.serializers import AuditEventSerializer
from apps.samples.services import emit_audit_event

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _bitacora_limpia():
    modulo_bitacora.reiniciar()
    yield
    modulo_bitacora.reiniciar()


@pytest.fixture
def own_sample(analyst_user):
    return Sample.objects.create(chn_code='CHN-2026-11-02-E301', patient_ref='ANON-E3', analyst=analyst_user, status='READY')


def _audit_url(s):
    return f'/api/clinic/samples/{s.id}/audit/'


class _Caida:
    def listar(self, sample_id):
        raise BitacoraNoDisponible('caída de prueba')


class TestFabrica:
    def test_por_omision_es_en_proceso(self, settings):
        assert settings.BITACORA_MODO == 'proceso'
        assert isinstance(bitacora(), BitacoraEnProceso)

    def test_una_sola_instancia_por_proceso(self):
        assert bitacora() is bitacora()

    def test_modo_desconocido_no_arranca(self, settings):
        settings.BITACORA_MODO = 'grpc'
        with pytest.raises(ValueError, match='grpc'):
            bitacora()


class TestEnProceso:
    def test_mismo_json_que_antes_de_la_interfaz(self, analyst_client, own_sample, analyst_user):
        emit_audit_event(own_sample, analyst_user, AuditEventType.XAI_VIEWED)
        emit_audit_event(own_sample, analyst_user, AuditEventType.MARK_ANOMALY, payload={'nota': 'x'})
        emit_audit_event(own_sample, analyst_user, AuditEventType.ANALYST_VALIDATED, mode='degradado')

        resp = analyst_client.get(_audit_url(own_sample))

        antes = AuditEventSerializer(own_sample.audit_events.all(), many=True).data
        assert resp.status_code == 200
        assert resp.json() == [dict(e) for e in antes]
        assert [e['event_type'] for e in resp.json()] == ['XAI_VIEWED', 'MARK_ANOMALY', 'ANALYST_VALIDATED']

    def test_solo_los_eventos_del_caso(self, own_sample, analyst_user):
        otro = Sample.objects.create(chn_code='CHN-2026-11-02-E302', analyst=analyst_user, status='READY')
        emit_audit_event(own_sample, analyst_user, AuditEventType.XAI_VIEWED)
        emit_audit_event(otro, analyst_user, AuditEventType.XAI_VIEWED)
        assert len(BitacoraEnProceso().listar(own_sample.id)) == 1

    def test_caso_sin_eventos_es_lista_vacia(self, own_sample):
        assert BitacoraEnProceso().listar(own_sample.id) == []


class TestVistaConBitacoraCaida:
    def test_503_con_retry_after(self, analyst_client, own_sample, monkeypatch):
        monkeypatch.setattr(modulo_bitacora, '_instancia', _Caida())
        resp = analyst_client.get(_audit_url(own_sample))
        assert resp.status_code == 503
        assert resp.json()['code'] == 'AUDIT_UNAVAILABLE'
        assert resp['Retry-After'] == '2'

    def test_el_permiso_se_comprueba_antes_de_llamar(self, analyst_client, django_user_model, monkeypatch):
        """Un caso ajeno da 403 sin preguntar a la bitácora (que aquí está caída)."""
        otro = django_user_model.objects.create_user(username='otro_e3', password='x')
        ajena = Sample.objects.create(chn_code='CHN-2026-11-02-E399', analyst=otro, status='READY')
        monkeypatch.setattr(modulo_bitacora, '_instancia', _Caida())
        assert analyst_client.get(_audit_url(ajena)).status_code == 403

    def test_la_muestra_inexistente_da_404_sin_llamar(self, analyst_client, monkeypatch):
        monkeypatch.setattr(modulo_bitacora, '_instancia', _Caida())
        resp = analyst_client.get('/api/clinic/samples/00000000-0000-0000-0000-000000000000/audit/')
        assert resp.status_code == 404
