"""GET /api/v1/inferencias/ — estado del límite de inferencias.

Hace visible en vivo el límite de la issue #2 (DD-AUD-001 F1): cuántas
inferencias admite el servicio a la vez, cuántas hay en curso y cuánto espera
una nueva antes de recibir 503.
"""
from __future__ import annotations

import threading

from fastapi.testclient import TestClient

import app.main as main
from app.concurrencia import LimiteInferencias

client = TestClient(main.app)


def _usar(monkeypatch, limite):
    monkeypatch.setattr(main, 'limite', limite)
    return limite


class TestEstadoDelLimite:
    def test_en_reposo_todas_las_plazas_libres(self):
        limite = LimiteInferencias(maximo=2, espera_s=7.5)
        assert limite.estado() == {'maximo': 2, 'en_curso': 0, 'libres': 2, 'espera_max_s': 7.5}

    def test_cuenta_las_inferencias_en_curso(self):
        limite = LimiteInferencias(maximo=2, espera_s=1)
        with limite.turno():
            assert limite.estado()['en_curso'] == 1
            assert limite.estado()['libres'] == 1
        assert limite.estado()['en_curso'] == 0

    def test_libera_la_cuenta_aunque_falle_la_inferencia(self):
        limite = LimiteInferencias(maximo=1, espera_s=0.05)
        try:
            with limite.turno():
                raise RuntimeError('fallo')
        except RuntimeError:
            pass
        assert limite.estado()['en_curso'] == 0

    def test_un_rechazo_por_espera_no_cuenta_como_en_curso(self):
        limite = LimiteInferencias(maximo=1, espera_s=0.05)
        with limite.turno():
            try:
                with limite.turno():
                    pass
            except Exception:        # 503: no llegó a entrar
                pass
            assert limite.estado()['en_curso'] == 1

    def test_la_cuenta_es_correcta_con_hilos_a_la_vez(self):
        limite = LimiteInferencias(maximo=4, espera_s=1)
        dentro, salir = threading.Barrier(5), threading.Event()

        def ocupar():
            with limite.turno():
                dentro.wait()
                salir.wait()

        hilos = [threading.Thread(target=ocupar) for _ in range(4)]
        for h in hilos:
            h.start()
        dentro.wait()
        try:
            assert limite.estado() == {'maximo': 4, 'en_curso': 4, 'libres': 0, 'espera_max_s': 1}
        finally:
            salir.set()
            for h in hilos:
                h.join()
        assert limite.estado()['en_curso'] == 0


class TestEndpoint:
    def test_devuelve_el_estado_del_limite_del_servicio(self, monkeypatch):
        _usar(monkeypatch, LimiteInferencias(maximo=1, espera_s=25))
        r = client.get('/api/v1/inferencias/')
        assert r.status_code == 200
        assert r.json() == {'maximo': 1, 'en_curso': 0, 'libres': 1, 'espera_max_s': 25.0}

    def test_con_una_inferencia_en_curso_lo_dice_y_no_espera_turno(self, monkeypatch):
        # Consultar el estado no es una inferencia: no pasa por el semáforo,
        # así que responde aunque no quede ninguna plaza.
        limite = _usar(monkeypatch, LimiteInferencias(maximo=1, espera_s=0.05))
        with limite.turno():
            r = client.get('/api/v1/inferencias/')
        assert r.status_code == 200
        assert r.json()['en_curso'] == 1
        assert r.json()['libres'] == 0
