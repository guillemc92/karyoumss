"""DD-E3-001 T2 — la bitácora extraída: cliente HTTP con protecciones y servicio interno.

El cliente se prueba con un transporte falso de httpx, sin red. Así cada caso
decide exactamente qué responde «el otro servicio» y cuántas veces se le
llamó. El breaker se prueba con un reloj falso: nada espera de verdad.
"""
import httpx
import pytest

from apps.samples import bitacora as modulo_bitacora
from apps.samples.bitacora import BitacoraNoDisponible, bitacora
from apps.samples.bitacora.http import Breaker, BitacoraHttp
from apps.samples.models import AuditEventType, Sample
from apps.samples.services import emit_audit_event

SID = '11111111-2222-3333-4444-555555555555'
EVENTOS = [{'id': 'e1', 'event_type': 'XAI_VIEWED'}]


class Reloj:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


class Servicio:
    """Un «otro servicio» de mentira: responde lo que diga la lista `guion`."""

    def __init__(self, *guion):
        self.guion = list(guion)
        self.llamadas: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.llamadas.append(request)
        paso = self.guion.pop(0) if len(self.guion) > 1 else self.guion[0]
        if isinstance(paso, Exception):
            raise paso
        return paso


def _ok():
    return httpx.Response(200, json=EVENTOS)


def _cliente(servicio, intentos=2, plazo_total_s=0.8, breaker=None):
    return BitacoraHttp(
        base_url='http://bitacora', secreto='s3creto-de-prueba', plazo_intento_s=0.3, intentos=intentos,
        plazo_total_s=plazo_total_s, breaker=breaker or Breaker(3, 2.0), transport=httpx.MockTransport(servicio),
    )


class TestCliente:
    def test_devuelve_los_eventos_y_manda_el_secreto(self):
        srv = Servicio(_ok())
        assert _cliente(srv).listar(SID) == EVENTOS
        assert srv.llamadas[0].url.path == f'/internal/bitacora/{SID}/'
        assert srv.llamadas[0].headers['X-Internal-Secret'] == 's3creto-de-prueba'

    def test_reintenta_tras_un_plazo_vencido(self):
        srv = Servicio(httpx.ReadTimeout('colgado'), _ok())
        assert _cliente(srv).listar(SID) == EVENTOS
        assert len(srv.llamadas) == 2

    def test_no_pasa_de_los_intentos(self):
        srv = Servicio(httpx.ConnectError('caído'))
        with pytest.raises(BitacoraNoDisponible, match='ConnectError'):
            _cliente(srv, intentos=2).listar(SID)
        assert len(srv.llamadas) == 2

    def test_un_500_es_un_fallo(self):
        with pytest.raises(BitacoraNoDisponible, match='HTTPStatusError'):
            _cliente(Servicio(httpx.Response(500))).listar(SID)

    def test_un_cuerpo_que_no_es_json_es_un_fallo(self):
        with pytest.raises(BitacoraNoDisponible):
            _cliente(Servicio(httpx.Response(200, content=b'<html>'))).listar(SID)

    def test_con_el_plazo_total_vencido_no_llama(self):
        srv = Servicio(_ok())
        with pytest.raises(BitacoraNoDisponible, match='plazo total'):
            _cliente(srv, plazo_total_s=0).listar(SID)
        assert srv.llamadas == []

    def test_el_plazo_de_cada_intento_llega_a_httpx(self):
        srv = Servicio(_ok())
        _cliente(srv).listar(SID)
        assert srv.llamadas[0].extensions['timeout']['read'] == pytest.approx(0.3)


class TestBreaker:
    def test_tres_llamadas_fallidas_lo_abren_y_la_cuarta_no_sale(self):
        srv = Servicio(httpx.ConnectError('caído'))
        cliente = _cliente(srv, intentos=1)
        for _ in range(3):
            with pytest.raises(BitacoraNoDisponible):
                cliente.listar(SID)
        assert cliente.breaker.estado == 'abierto'
        with pytest.raises(BitacoraNoDisponible, match='breaker abierto'):
            cliente.listar(SID)
        assert len(srv.llamadas) == 3

    def test_un_exito_reinicia_la_cuenta(self):
        srv = Servicio(httpx.ConnectError('a'), httpx.ConnectError('b'), _ok(), httpx.ConnectError('c'))
        cliente = _cliente(srv, intentos=1)
        for _ in range(2):
            with pytest.raises(BitacoraNoDisponible):
                cliente.listar(SID)
        cliente.listar(SID)
        with pytest.raises(BitacoraNoDisponible):
            cliente.listar(SID)
        assert cliente.breaker.estado == 'cerrado'

    def test_pasado_el_reset_prueba_una_vez_y_se_cierra(self):
        reloj = Reloj()
        b = Breaker(1, 2.0, reloj=reloj)
        b.fallo()
        assert b.estado == 'abierto' and not b.permite()
        reloj.t += 2.0
        assert b.estado == 'semiabierto'
        assert b.permite() is True
        assert b.permite() is False, 'en semiabierto solo sale UNA llamada de prueba'
        b.exito()
        assert b.estado == 'cerrado' and b.permite()

    def test_si_la_prueba_falla_vuelve_a_abrir(self):
        reloj = Reloj()
        b = Breaker(3, 2.0, reloj=reloj)
        for _ in range(3):
            b.fallo()
        reloj.t += 2.0
        assert b.permite()
        b.fallo()
        assert b.estado == 'abierto'
        reloj.t += 1.9
        assert not b.permite()


class TestFabricaHttp:
    def test_modo_http_construye_el_cliente_desde_settings(self, settings):
        modulo_bitacora.reiniciar()
        settings.BITACORA_MODO = 'http'
        settings.BITACORA_URL = 'http://toxiproxy:8666'
        settings.BITACORA_PLAZO_INTENTO_MS = 250
        settings.BITACORA_BREAKER_FALLOS = 4
        try:
            b = bitacora()
            assert isinstance(b, BitacoraHttp)
            assert b.plazo_intento_s == 0.25
            assert b.breaker.fallos == 4
            assert str(b._cliente.base_url) == 'http://toxiproxy:8666'
        finally:
            modulo_bitacora.reiniciar()


@pytest.mark.django_db
@pytest.mark.urls('clinic_backend.urls_bitacora')
class TestServicioInterno:
    @pytest.fixture
    def caso(self, analyst_user):
        s = Sample.objects.create(chn_code='CHN-2026-11-02-E310', analyst=analyst_user, status='READY')
        emit_audit_event(s, analyst_user, AuditEventType.XAI_VIEWED)
        emit_audit_event(s, analyst_user, AuditEventType.ANALYST_VALIDATED)
        return s

    def test_sin_secreto_403(self, api_client, caso):
        assert api_client.get(f'/internal/bitacora/{caso.id}/').status_code == 403

    def test_con_secreto_equivocado_403(self, api_client, caso):
        resp = api_client.get(f'/internal/bitacora/{caso.id}/', HTTP_X_INTERNAL_SECRET='otro')
        assert resp.status_code == 403

    def test_con_secreto_los_eventos_del_caso(self, api_client, caso, settings):
        resp = api_client.get(f'/internal/bitacora/{caso.id}/', HTTP_X_INTERNAL_SECRET=settings.INTERNAL_SERVICE_SECRET)
        assert resp.status_code == 200
        assert [e['event_type'] for e in resp.json()] == ['XAI_VIEWED', 'ANALYST_VALIDATED']

    def test_las_rutas_clinicas_no_existen_aqui(self, api_client, caso):
        assert api_client.get(f'/api/clinic/samples/{caso.id}/').status_code == 404

    def test_salud(self, api_client):
        assert api_client.get('/salud/').json() == {'servicio': 'bitacora', 'ok': True}


@pytest.mark.django_db
class TestDeExtremoAExtremo:
    """La API en modo http, con el «otro servicio» siendo la vista interna real."""

    def test_la_api_devuelve_lo_mismo_por_las_dos_formas(self, analyst_client, analyst_user, settings, monkeypatch):
        from django.test import Client

        s = Sample.objects.create(chn_code='CHN-2026-11-02-E320', analyst=analyst_user, status='READY')
        emit_audit_event(s, analyst_user, AuditEventType.XAI_VIEWED)
        emit_audit_event(s, analyst_user, AuditEventType.MARK_ANOMALY, payload={'n': 1})
        en_proceso = analyst_client.get(f'/api/clinic/samples/{s.id}/audit/').json()

        def reenviar(request: httpx.Request) -> httpx.Response:
            with pytest.MonkeyPatch.context() as mp:
                mp.setattr(settings, 'ROOT_URLCONF', 'clinic_backend.urls_bitacora')
                r = Client().get(request.url.path, HTTP_X_INTERNAL_SECRET=request.headers['X-Internal-Secret'])
            return httpx.Response(r.status_code, content=r.content, headers={'content-type': 'application/json'})

        monkeypatch.setattr(modulo_bitacora, '_instancia', BitacoraHttp(
            base_url='http://bitacora', secreto=settings.INTERNAL_SERVICE_SECRET, plazo_intento_s=0.3, intentos=2,
            plazo_total_s=0.8, breaker=Breaker(3, 2.0), transport=httpx.MockTransport(reenviar),
        ))
        extraida = analyst_client.get(f'/api/clinic/samples/{s.id}/audit/').json()
        assert extraida == en_proceso
        assert len(extraida) == 2
