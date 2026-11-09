"""La inferencia no congela backend-ml (DD-AUD-001 F1, issue #2, CON-02).

Medido en la auditoría: una segmentación son ~19 s de CPU. Si corre dentro de
un `async def`, el único event loop de uvicorn deja de atender TODO lo demás,
`/health/` incluido.

Estas pruebas reproducen ese escenario en un solo event loop, como uvicorn, con
`httpx.AsyncClient` sobre la app ASGI. `TestClient` no serviría: cada petición
abre su propio loop y el bloqueo no se vería nunca.
"""
from __future__ import annotations

import asyncio
import threading
import time

import httpx
import pytest

import app.main as main
import app.pipeline as pipeline
from app.concurrencia import LimiteInferencias

LENTA_S = 1.0   # inferencia simulada; la real son ~19 s


def _png(synthetic_png_bytes):
    return {'file': ('m.png', synthetic_png_bytes, 'image/png')}


class _ClasificadorCargado:
    """Modelo ya en memoria: `/health/` no debe pagar aquí la carga (~16 s),
    que es otro coste; esta prueba mide solo el bloqueo del event loop."""
    is_trained = True
    name = 'cargado'


@pytest.fixture
def inferencia_lenta(monkeypatch):
    """Sustituye el pipeline por una espera de CPU síncrona, como la real."""
    monkeypatch.setattr(pipeline, '_classifier_singleton', _ClasificadorCargado())
    def lenta(gray):
        time.sleep(LENTA_S)
        return pipeline.SegmentResult(
            model_version='lenta', segmenter='-', classifier='-', image_width=1,
            image_height=1, chromosome_count=0, confidence_avg=0.0, chromosomes=[])
    monkeypatch.setattr(main, 'run_pipeline', lenta)


async def _peticiones(*llamadas):
    transporte = httpx.ASGITransport(app=main.app)
    async with httpx.AsyncClient(transport=transporte, base_url='http://ml') as cliente:
        return await asyncio.gather(*(llamada(cliente) for llamada in llamadas))


def test_health_responde_durante_una_inferencia(inferencia_lenta, synthetic_png_bytes):
    # Los instantes se miden desde un origen COMÚN. La primera versión medía
    # /health/ desde que terminaba su propio sleep(0.2); con el loop bloqueado
    # ese sleep también se retrasa, el cronómetro arrancaba con el bloqueo ya
    # pasado y la prueba seguía verde con `async def`. Lo cazó la mutación.
    fin = {}
    origen = time.perf_counter()

    async def segmentar(cliente):
        r = await cliente.post('/api/v1/segment/', files=_png(synthetic_png_bytes))
        fin['segment'] = time.perf_counter() - origen
        return r

    async def salud(cliente):
        await asyncio.sleep(0.2)            # la inferencia ya está en marcha
        r = await cliente.get('/health/')
        fin['health'] = time.perf_counter() - origen
        return r

    seg, health = asyncio.run(_peticiones(segmentar, salud))

    assert seg.status_code == 200
    assert health.status_code == 200
    # Con el loop bloqueado, /health/ solo termina cuando acaba la inferencia.
    assert fin['health'] < fin['segment'], fin
    assert fin['health'] < 0.2 + 0.5, f"/health/ terminó a los {fin['health']:.2f} s"


def test_si_la_espera_se_agota_responde_503_con_retry_after(
        inferencia_lenta, synthetic_png_bytes, monkeypatch):
    monkeypatch.setattr(main, 'limite', LimiteInferencias(maximo=1, espera_s=0.2))

    async def segmentar(cliente):
        return await cliente.post('/api/v1/segment/', files=_png(synthetic_png_bytes))

    respuestas = asyncio.run(_peticiones(segmentar, segmentar))

    codigos = sorted(r.status_code for r in respuestas)
    assert codigos == [200, 503]
    rechazada = next(r for r in respuestas if r.status_code == 503)
    assert int(rechazada.headers['Retry-After']) > 0


def test_con_hueco_libre_las_dos_inferencias_terminan(
        inferencia_lenta, synthetic_png_bytes, monkeypatch):
    # La segunda espera su turno (no se rechaza) si la espera alcanza.
    monkeypatch.setattr(main, 'limite', LimiteInferencias(maximo=1, espera_s=5))

    async def segmentar(cliente):
        return await cliente.post('/api/v1/segment/', files=_png(synthetic_png_bytes))

    respuestas = asyncio.run(_peticiones(segmentar, segmentar))

    assert [r.status_code for r in respuestas] == [200, 200]


def test_xai_y_classify_tambien_pasan_por_el_limite(synthetic_png_bytes, monkeypatch):
    # Un límite ya ocupado: cualquier endpoint de inferencia debe rechazar.
    limite = LimiteInferencias(maximo=1, espera_s=0.05)
    monkeypatch.setattr(main, 'limite', limite)
    with limite.turno():
        for ruta in ('/api/v1/xai/', '/api/v1/classify/'):
            respuesta = asyncio.run(_peticiones(
                lambda c, ruta=ruta: c.post(ruta, files=_png(synthetic_png_bytes),
                                            data={'x': 1, 'y': 1, 'w': 5, 'h': 5})))[0]
            assert respuesta.status_code == 503, ruta


def test_el_modelo_se_carga_una_sola_vez_con_peticiones_simultaneas(monkeypatch):
    import app.efficientnet as efficientnet
    cargas = []

    class ModeloLento:
        is_trained = True
        name = 'lento'

        def __init__(self):
            cargas.append(1)
            time.sleep(0.3)                 # la carga real son ~16 s

    monkeypatch.setattr(efficientnet, 'EfficientNetClassifier', ModeloLento)
    monkeypatch.setattr(pipeline, '_classifier_singleton', None)

    hilos = [threading.Thread(target=pipeline.get_classifier) for _ in range(4)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()

    assert len(cargas) == 1


class TestLimiteInferencias:
    def test_lee_el_entorno(self, monkeypatch):
        monkeypatch.setenv('ML_MAX_INFERENCIAS', '3')
        monkeypatch.setenv('ML_ESPERA_MAX_S', '7.5')
        limite = LimiteInferencias.desde_entorno()
        assert (limite.maximo, limite.espera_s) == (3, 7.5)

    def test_valores_por_defecto(self, monkeypatch):
        monkeypatch.delenv('ML_MAX_INFERENCIAS', raising=False)
        monkeypatch.delenv('ML_ESPERA_MAX_S', raising=False)
        limite = LimiteInferencias.desde_entorno()
        assert (limite.maximo, limite.espera_s) == (1, 25.0)

    @pytest.mark.parametrize('maximo, espera', [('0', '25'), ('-1', '25'), ('1', '-3'), ('x', '25')])
    def test_rechaza_valores_invalidos(self, monkeypatch, maximo, espera):
        # Un límite de 0 bloquearía toda inferencia sin decir por qué.
        monkeypatch.setenv('ML_MAX_INFERENCIAS', maximo)
        monkeypatch.setenv('ML_ESPERA_MAX_S', espera)
        with pytest.raises(ValueError):
            LimiteInferencias.desde_entorno()

    def test_libera_el_turno_aunque_falle_la_inferencia(self):
        limite = LimiteInferencias(maximo=1, espera_s=0.05)
        with pytest.raises(RuntimeError):
            with limite.turno():
                raise RuntimeError('fallo dentro de la inferencia')
        with limite.turno():                # si no se liberó, aquí daría 503
            pass
