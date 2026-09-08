import httpx
import pytest

from apps.samples.pipeline_client import MLDegradedError, PipelineClient


def _client(**overrides):
    defaults = dict(base_url='http://localhost:9999', timeout=0.2, threshold=3, cooldown=60)
    defaults.update(overrides)
    return PipelineClient(**defaults)


class TestPipelineClient:
    def test_trigger_processing_success(self, monkeypatch):
        client = _client()

        class FakeResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return {'sample_id': 'x', 'task_id': 'abc', 'status': 'queued'}

        class FakeHttpxClient:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def post(self, *a, **kw):
                return FakeResponse()

        monkeypatch.setattr(httpx, 'Client', lambda **kw: FakeHttpxClient())
        result = client.trigger_processing('sample-1')
        assert result['task_id'] == 'abc'

    def test_trigger_processing_timeout_raises_degraded(self, monkeypatch):
        client = _client()

        class FakeHttpxClient:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def post(self, *a, **kw):
                raise httpx.TimeoutException('timeout')

        monkeypatch.setattr(httpx, 'Client', lambda **kw: FakeHttpxClient())
        with pytest.raises(MLDegradedError):
            client.trigger_processing('sample-1')

    def test_circuit_opens_after_threshold_failures(self, monkeypatch):
        client = _client(threshold=2)

        class FakeHttpxClient:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def post(self, *a, **kw):
                raise httpx.TimeoutException('timeout')

        monkeypatch.setattr(httpx, 'Client', lambda **kw: FakeHttpxClient())
        for _ in range(2):
            with pytest.raises(MLDegradedError):
                client.trigger_processing('sample-1')

        # 3er intento: circuito abierto, ni siquiera llama a httpx
        with pytest.raises(MLDegradedError, match='circuit_open'):
            client.trigger_processing('sample-1')

    def test_get_status_success(self, monkeypatch):
        client = _client()

        class FakeResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return {'sample_id': 'x', 'status': 'READY'}

        class FakeHttpxClient:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def get(self, *a, **kw):
                return FakeResponse()

        monkeypatch.setattr(httpx, 'Client', lambda **kw: FakeHttpxClient())
        result = client.get_status('sample-1')
        assert result['status'] == 'READY'

    def test_get_status_error_raises_degraded(self, monkeypatch):
        client = _client()

        class FakeHttpxClient:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def get(self, *a, **kw):
                raise httpx.ConnectError('refused')

        monkeypatch.setattr(httpx, 'Client', lambda **kw: FakeHttpxClient())
        with pytest.raises(MLDegradedError):
            client.get_status('sample-1')


# --- la frontera con backend-ml ---------------------------------------------
#
# `segment_image`, `xai_heatmap` y `classify_crop` mandan una imagen y esperan
# un resultado del modelo. Las tres comparten estructura (circuito, subida
# multipart, circuito de nuevo), asi que se prueban con la MISMA bateria
# parametrizada en vez de triplicar el fichero: si manana se anade una cuarta,
# se anade una fila, no un bloque.
#
# Lo que NO se afirma aqui es el contenido del resultado — eso lo decide el
# modelo. Se afirma lo que el cliente controla: que sube la imagen ENTERA, que
# el bbox viaja como enteros, que el timeout se ensancha y que una caida es
# MLDegradedError y no un cariotipo vacio.

class RedML:
    """Doble de `httpx.Client` que registra la subida completa."""

    def __init__(self, devuelve=None, lanza=None):
        self.devuelve = devuelve if devuelve is not None else {'ok': True}
        self.lanza = lanza
        self.llamadas = []

    def montar(self, monkeypatch):
        monkeypatch.setattr(httpx, 'Client', lambda **kw: _SesionML(self, kw))
        return self


class _SesionML:
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
        return _RespuestaML(self.red.devuelve)


class _RespuestaML:
    def __init__(self, cuerpo):
        self.cuerpo = cuerpo

    def raise_for_status(self):
        return None

    def json(self):
        return self.cuerpo


IMAGEN = b'BM' + b'\x00' * 64
BBOX = {'x': 10.7, 'y': 20.2, 'w': 30.9, 'h': 40.0}

# (metodo, ruta, timeout minimo, manda bbox)
METODOS_ML = [
    ('segment_image', '/api/v1/segment/', 30.0, False),
    ('xai_heatmap', '/api/v1/xai/', 60.0, True),
    ('classify_crop', '/api/v1/classify/', 60.0, True),
]
IDS_ML = [m[0] for m in METODOS_ML]


def _invocar(client, metodo):
    if metodo == 'segment_image':
        return client.segment_image(IMAGEN)
    return getattr(client, metodo)(IMAGEN, BBOX)


@pytest.mark.parametrize('metodo,ruta,timeout_min,con_bbox', METODOS_ML, ids=IDS_ML)
def test_sube_la_imagen_entera_a_la_ruta_que_toca(monkeypatch, metodo, ruta,
                                                  timeout_min, con_bbox):
    red = RedML(devuelve={'resultado': metodo}).montar(monkeypatch)
    resultado = _invocar(_client(), metodo)

    (llamada,) = red.llamadas
    assert llamada['url'] == 'http://localhost:9999' + ruta
    assert resultado == {'resultado': metodo}
    # La imagen viaja como fichero multipart, entera y sin recortar: el
    # preprocesado del clasificador usa la altura mediana de TODOS los
    # cromosomas de la metafase como senal de escala (ADR-0007).
    nombre, contenido, _tipo = llamada['files']['file']
    assert contenido == IMAGEN
    assert nombre.endswith('.bmp')


@pytest.mark.parametrize('metodo,ruta,timeout_min,con_bbox', METODOS_ML, ids=IDS_ML)
def test_el_timeout_se_ensancha_para_el_modelo(monkeypatch, metodo, ruta,
                                               timeout_min, con_bbox):
    """El timeout de configuracion (2 s) sirve para pedir estado, no para inferir.

    Sin el suelo, una Grad-CAM sobre CPU se abortaria siempre por timeout y el
    circuito acabaria abierto: el sistema entero pareceria caido cuando lo unico
    que pasa es que el modelo tarda.
    """
    red = RedML().montar(monkeypatch)
    _invocar(_client(timeout=0.2), metodo)
    assert red.llamadas[0]['timeout'] == timeout_min


@pytest.mark.parametrize('metodo', ['xai_heatmap', 'classify_crop'])
def test_el_bbox_viaja_como_enteros(monkeypatch, metodo):
    """Konva devuelve coordenadas en float; el recorte de pixeles es entero."""
    red = RedML().montar(monkeypatch)
    _invocar(_client(), metodo)
    assert red.llamadas[0]['data'] == {'x': 10, 'y': 20, 'w': 30, 'h': 40}


@pytest.mark.parametrize('metodo', ['xai_heatmap', 'classify_crop'])
def test_un_bbox_incompleto_no_revienta_la_llamada(monkeypatch, metodo):
    """Falta una clave -> 0, no KeyError.

    Es deliberado: el backend-ml valida el recuadro. Fallar aqui convertiria un
    dato raro en una caida del cliente, y el circuito contaria ese fallo como
    si backend-ml estuviera caido.
    """
    red = RedML().montar(monkeypatch)
    getattr(_client(), metodo)(IMAGEN, {'x': 5})
    assert red.llamadas[0]['data'] == {'x': 5, 'y': 0, 'w': 0, 'h': 0}


@pytest.mark.parametrize('metodo,ruta,timeout_min,con_bbox', METODOS_ML, ids=IDS_ML)
def test_una_caida_del_modelo_es_degradacion_no_un_resultado_vacio(
        monkeypatch, metodo, ruta, timeout_min, con_bbox):
    """RN-07: degradar es seguir trabajando a mano, no cargar un cariotipo vacio."""
    RedML(lanza=httpx.ConnectError('rechazada')).montar(monkeypatch)
    with pytest.raises(MLDegradedError):
        _invocar(_client(), metodo)


@pytest.mark.parametrize('metodo,ruta,timeout_min,con_bbox', METODOS_ML, ids=IDS_ML)
def test_con_el_circuito_abierto_ni_se_sube_la_imagen(monkeypatch, metodo, ruta,
                                                      timeout_min, con_bbox):
    """Cortar antes de subir es el punto: subir 3 MB para que expire no ayuda."""
    red = RedML(lanza=httpx.TimeoutException('agotado')).montar(monkeypatch)
    client = _client(threshold=1)

    with pytest.raises(MLDegradedError):
        _invocar(client, metodo)
    with pytest.raises(MLDegradedError, match='circuit_open'):
        _invocar(client, metodo)
    assert len(red.llamadas) == 1


def test_un_exito_del_modelo_cierra_el_contador(monkeypatch):
    """Los tres metodos comparten el contador: un exito en uno rehabilita a todos."""
    red = RedML(lanza=httpx.TimeoutException('agotado')).montar(monkeypatch)
    client = _client(threshold=2)

    with pytest.raises(MLDegradedError):
        client.segment_image(IMAGEN)
    red.lanza = None
    client.xai_heatmap(IMAGEN, BBOX)

    red.lanza = httpx.TimeoutException('agotado')
    with pytest.raises(MLDegradedError):
        client.classify_crop(IMAGEN, BBOX)
    assert client._circuit_open() is False
