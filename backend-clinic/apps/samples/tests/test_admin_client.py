"""Frontera con backend-admin: la verificacion MFA de la firma del supervisor.

Es la unica llamada de red de la que depende un acto de cumplimiento (21 CFR
Part 11, ADR-0023 D3). Por eso lo que se prueba aqui no es "que la peticion
funcione", sino las tres decisiones que toma el cliente cuando la red falla:

    responde         -> devuelve el veredicto TAL CUAL, no lo reinterpreta
    no responde      -> MfaServiceError; NUNCA un veredicto inventado
    sigue sin ir     -> abre el circuito y deja de preguntar

La segunda es la importante. Degradar a `{'valid': True}` seria firmar sin
segundo factor. Degradar a `{'valid': False}` en silencio seria mas seguro pero
igual de malo de otra forma: el supervisor creeria que su codigo esta mal
cuando el problema es que backend-admin esta caido.

Doble **solo en la frontera** (`httpx.Client`). El circuit breaker —contador,
umbral y cooldown— es el real: es logica del cliente, no de la red.
"""
import time

import httpx
import pytest

from apps.samples.admin_client import AdminClient, MfaServiceError, admin_client

UMBRAL = 3
COOLDOWN = 60


def cliente(**cambios):
    ajustes = dict(base_url='http://admin.local', secret='s3cr3t', timeout=0.2,
                   threshold=UMBRAL, cooldown=COOLDOWN)
    ajustes.update(cambios)
    return AdminClient(**ajustes)


class Red:
    """Doble de `httpx.Client` que ademas cuenta y guarda lo que se le mando.

    Contar importa: la mitad de las afirmaciones de este modulo son sobre
    llamadas que NO deben ocurrir.
    """

    def __init__(self, devuelve=None, lanza=None):
        self.devuelve = devuelve if devuelve is not None else {'valid': True,
                                                               'enrolled': True}
        self.lanza = lanza
        self.llamadas = []

    def montar(self, monkeypatch):
        monkeypatch.setattr(httpx, 'Client', lambda **kw: _Sesion(self, kw))
        return self


class _Sesion:
    def __init__(self, red, kwargs):
        self.red = red
        self.kwargs = kwargs

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def post(self, url, **kw):
        self.red.llamadas.append(
            {'url': url, 'timeout': self.kwargs.get('timeout'), **kw})
        if self.red.lanza is not None:
            raise self.red.lanza
        return _Respuesta(self.red.devuelve)


class _Respuesta:
    def __init__(self, cuerpo):
        self.cuerpo = cuerpo

    def raise_for_status(self):
        return None

    def json(self):
        return self.cuerpo


# --- el camino feliz --------------------------------------------------------

def test_devuelve_el_veredicto_tal_cual(monkeypatch):
    """El cliente transporta la respuesta; no decide sobre ella.

    `enrolled` viaja aparte de `valid` a proposito: "no tiene MFA dado de alta"
    y "el codigo esta mal" son dos situaciones distintas para el supervisor.
    Si el cliente colapsara ambas en un booleano, la pantalla no podria
    distinguirlas.
    """
    Red(devuelve={'valid': False, 'enrolled': False}).montar(monkeypatch)
    assert cliente().verify_mfa('sup@umss.bo', '000000') == {'valid': False,
                                                             'enrolled': False}


def test_manda_el_secreto_interno_y_el_codigo_donde_corresponde(monkeypatch):
    """El secreto va en cabecera y las credenciales en el cuerpo, no en la URL.

    Un codigo MFA en la query string acabaria en los logs del proxy.
    """
    red = Red().montar(monkeypatch)
    cliente().verify_mfa('sup@umss.bo', '123456')

    (llamada,) = red.llamadas
    assert llamada['url'] == 'http://admin.local/api/internal/mfa/verify/'
    assert llamada['headers'] == {'X-Internal-Secret': 's3cr3t'}
    assert llamada['json'] == {'email': 'sup@umss.bo', 'code': '123456'}
    assert '123456' not in llamada['url']
    assert llamada['timeout'] == 0.2


def test_un_mfa_invalido_no_cuenta_como_fallo_del_servicio(monkeypatch):
    """Un codigo equivocado es una respuesta, no una caida.

    Confundirlos abriria el circuito a los tres intentos fallidos de un
    supervisor tecleando mal — y dejaria sin firmar a todo el laboratorio.
    """
    Red(devuelve={'valid': False, 'enrolled': True}).montar(monkeypatch)
    c = cliente()
    for _ in range(UMBRAL + 2):
        assert c.verify_mfa('sup@umss.bo', 'malo')['valid'] is False
    assert c._circuit_open() is False


# --- la red falla -----------------------------------------------------------

@pytest.mark.parametrize('fallo', [
    httpx.TimeoutException('agotado'),
    httpx.ConnectError('conexion rechazada'),
    httpx.HTTPStatusError('500', request=None, response=None),
])
def test_ninguna_caida_se_traduce_en_veredicto(monkeypatch, fallo):
    """Pase lo que pase en la red, el resultado es una excepcion — nunca un dict.

    Esta es la prueba que impide el fallo silencioso: si alguien anadiera un
    `return {'valid': False}` al `except`, la firma seguiria bloqueandose pero
    el supervisor no sabria por que, y la traza no diria que admin estaba caido.
    """
    Red(lanza=fallo).montar(monkeypatch)
    with pytest.raises(MfaServiceError) as exc:
        cliente().verify_mfa('sup@umss.bo', '123456')
    assert str(fallo) in str(exc.value)     # la causa llega al log, no se pierde


def test_el_circuito_se_abre_al_alcanzar_el_umbral(monkeypatch):
    red = Red(lanza=httpx.TimeoutException('agotado')).montar(monkeypatch)
    c = cliente()

    for _ in range(UMBRAL):
        with pytest.raises(MfaServiceError):
            c.verify_mfa('sup@umss.bo', '123456')

    with pytest.raises(MfaServiceError, match='circuit_open'):
        c.verify_mfa('sup@umss.bo', '123456')
    # Lo que define al circuito abierto: dejo de tocar la red.
    assert len(red.llamadas) == UMBRAL


def test_un_exito_borra_el_contador_de_fallos(monkeypatch):
    """El umbral cuenta fallos SEGUIDOS, no fallos acumulados desde el arranque.

    Sin esto, un servicio que falla una vez por semana acabaria abriendo el
    circuito al cabo de tres semanas de funcionamiento normal.
    """
    red = Red(lanza=httpx.TimeoutException('agotado')).montar(monkeypatch)
    c = cliente()
    for _ in range(UMBRAL - 1):
        with pytest.raises(MfaServiceError):
            c.verify_mfa('sup@umss.bo', '123456')

    red.lanza = None
    assert c.verify_mfa('sup@umss.bo', '123456')['valid'] is True

    red.lanza = httpx.TimeoutException('agotado')
    for _ in range(UMBRAL - 1):
        with pytest.raises(MfaServiceError):
            c.verify_mfa('sup@umss.bo', '123456')
    # Van 4 fallos en total, pero solo 2 seguidos: el circuito sigue cerrado.
    assert c._circuit_open() is False


def test_el_circuito_vuelve_a_cerrarse_al_expirar_el_cooldown(monkeypatch):
    """Abrirse es automatico; cerrarse tambien. Nadie reinicia nada a mano."""
    red = Red(lanza=httpx.TimeoutException('agotado')).montar(monkeypatch)
    c = cliente()
    for _ in range(UMBRAL):
        with pytest.raises(MfaServiceError):
            c.verify_mfa('sup@umss.bo', '123456')
    assert c._circuit_open() is True

    ahora = time.time()
    monkeypatch.setattr(time, 'time', lambda: ahora + COOLDOWN + 1)
    assert c._circuit_open() is False

    red.lanza = None
    assert c.verify_mfa('sup@umss.bo', '123456')['valid'] is True


# --- la instancia que usa produccion ----------------------------------------

def test_la_instancia_de_produccion_esta_configurada(settings):
    """El modulo exporta un singleton ya montado: si cambian los ajustes, se nota."""
    assert admin_client.base_url == settings.ADMIN_INTERNAL_URL
    assert admin_client.secret == settings.INTERNAL_SERVICE_SECRET
    assert (admin_client.threshold, admin_client.cooldown) == (UMBRAL, COOLDOWN)
