"""Estado del límite de inferencias — GET /api/v1/inferencias/.

Trazabilidad: FR1 (campos), FR2 (no pasa por el semáforo), FR3 (contadores
correctos con concurrencia), FR4 (secreto interno), NFR1/NFR2 (lectura bajo
lock, comparación en tiempo constante, el secreto no se filtra).

Las pruebas con hilos se sincronizan con `threading.Event`/`Barrier`; la única
espera es un sondeo acotado de `estado()` para `en_espera`, porque entre el
incremento del contador y el `acquire` del semáforo no hay ningún gancho.
"""
from __future__ import annotations

import threading
import time

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import app.main as main
import app.pipeline as pipeline
from app.concurrencia import LimiteInferencias

ESPERA_HILOS_S = 5.0     # tope de seguridad: ninguna prueba debería acercarse
RUTA = '/api/v1/inferencias/'
SECRETO_PRUEBA = 'secreto-de-prueba-no-real'   # valor fijo solo para pruebas


def _esperar_hasta(condicion, tope_s: float = ESPERA_HILOS_S) -> bool:
    """Sondea `condicion()` hasta que se cumpla o pase `tope_s`."""
    pausa = threading.Event()           # nunca se activa: solo cede la CPU
    limite_t = time.monotonic() + tope_s
    while time.monotonic() < limite_t:
        if condicion():
            return True
        pausa.wait(0.005)
    return condicion()


def _ocupar_turno(limite: LimiteInferencias, dentro: threading.Event,
                  soltar: threading.Event) -> threading.Thread:
    """Hilo que entra en `turno()`, avisa con `dentro` y sale al recibir `soltar`."""
    def trabajo():
        with limite.turno():
            dentro.set()
            soltar.wait(ESPERA_HILOS_S)
    hilo = threading.Thread(target=trabajo)
    hilo.start()
    assert dentro.wait(ESPERA_HILOS_S), 'el hilo no obtuvo turno'
    return hilo


# --- Lógica de negocio: LimiteInferencias.estado() --------------------------

class TestEstadoDelLimite:
    def test_estado_en_reposo(self):
        # FR1: los cinco campos, sin inferencias en curso ni en espera.
        limite = LimiteInferencias(maximo=2, espera_s=7.5)
        assert limite.estado() == {
            'maximo': 2, 'en_curso': 0, 'libres': 2,
            'espera_max_s': 7.5, 'en_espera': 0,
        }

    def test_en_curso_sube_con_un_turno_y_baja_al_liberarlo(self):
        # FR3.1, FR1.3: libres = maximo - en_curso.
        limite = LimiteInferencias(maximo=2, espera_s=0.05)
        with limite.turno():
            estado = limite.estado()
            assert (estado['en_curso'], estado['libres']) == (1, 1)
        estado = limite.estado()
        assert (estado['en_curso'], estado['libres']) == (0, 2)

    def test_en_curso_vuelve_a_su_valor_si_la_inferencia_falla(self):
        # FR3.1: también baja cuando la inferencia lanza una excepción.
        limite = LimiteInferencias(maximo=1, espera_s=0.05)
        with pytest.raises(RuntimeError):
            with limite.turno():
                assert limite.estado()['en_curso'] == 1
                raise RuntimeError('fallo dentro de la inferencia')
        assert limite.estado()['en_curso'] == 0
        assert limite.estado()['libres'] == 1

    def test_un_rechazo_por_espera_no_cuenta_en_curso_ni_queda_en_espera(self):
        # FR3.2, FR3.3: el 503 deja en_curso como estaba y en_espera en 0.
        limite = LimiteInferencias(maximo=1, espera_s=0.05)
        with limite.turno():
            with pytest.raises(HTTPException) as rechazo:
                with limite.turno():
                    pytest.fail('no debía obtener turno')
            assert rechazo.value.status_code == 503
            estado = limite.estado()
            assert (estado['en_curso'], estado['en_espera']) == (1, 0)
        assert limite.estado()['en_curso'] == 0

    def test_en_espera_vale_uno_mientras_otra_peticion_espera_turno(self):
        # FR1.5, FR3.2: sube al empezar a esperar y baja al obtener el turno.
        limite = LimiteInferencias(maximo=1, espera_s=ESPERA_HILOS_S)
        dentro, soltar = threading.Event(), threading.Event()
        ocupante = _ocupar_turno(limite, dentro, soltar)

        segunda_dentro = threading.Event()
        def esperar_turno():
            with limite.turno():
                segunda_dentro.set()
        segunda = threading.Thread(target=esperar_turno)
        segunda.start()
        try:
            assert _esperar_hasta(lambda: limite.estado()['en_espera'] == 1)
            estado = limite.estado()
            assert (estado['en_curso'], estado['libres']) == (1, 0)
        finally:
            soltar.set()
            ocupante.join(ESPERA_HILOS_S)
            segunda.join(ESPERA_HILOS_S)

        assert segunda_dentro.is_set()
        assert limite.estado()['en_espera'] == 0
        assert limite.estado()['en_curso'] == 0

    def test_cuentas_correctas_con_varios_hilos_a_la_vez(self):
        # FR3: con 8 hilos compitiendo por 3 plazas nunca hay más de 3 en curso
        # y, al terminar, todo vuelve a cero.
        limite = LimiteInferencias(maximo=3, espera_s=ESPERA_HILOS_S)
        hilos_n, vueltas = 8, 40
        salida = threading.Barrier(hilos_n)
        vistos: list[dict] = []
        errores: list[BaseException] = []
        guarda = threading.Lock()

        def trabajo():
            try:
                salida.wait(ESPERA_HILOS_S)
                for _ in range(vueltas):
                    with limite.turno():
                        estado = limite.estado()
                        with guarda:
                            vistos.append(estado)
            except BaseException as exc:      # se informa abajo, no se traga
                with guarda:
                    errores.append(exc)

        hilos = [threading.Thread(target=trabajo) for _ in range(hilos_n)]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join(ESPERA_HILOS_S * 4)

        assert not errores, errores
        assert len(vistos) == hilos_n * vueltas
        for estado in vistos:
            assert 1 <= estado['en_curso'] <= 3
            assert estado['libres'] == 3 - estado['en_curso']
            assert estado['en_espera'] >= 0
        assert limite.estado() == {
            'maximo': 3, 'en_curso': 0, 'libres': 3,
            'espera_max_s': ESPERA_HILOS_S, 'en_espera': 0,
        }


# --- API: GET /api/v1/inferencias/ ------------------------------------------

class _ClasificadorCargado:
    """Modelo ya en memoria: `/health/` no debe cargar el real (~16 s)."""
    is_trained = True
    name = 'cargado'


@pytest.fixture
def cliente():
    return TestClient(main.app)


@pytest.fixture
def limite_controlado(monkeypatch):
    """Límite propio de cada prueba; la espera larga delataría un turno."""
    limite = LimiteInferencias(maximo=1, espera_s=ESPERA_HILOS_S)
    monkeypatch.setattr(main, 'limite', limite)
    return limite


@pytest.fixture
def con_secreto(monkeypatch):
    monkeypatch.setenv('INTERNAL_SERVICE_SECRET', SECRETO_PRUEBA)


class TestEndpointEstadoInferencias:
    def test_200_con_el_secreto_correcto_y_el_limite_en_reposo(
            self, cliente, limite_controlado, con_secreto):
        # FR1, FR4.1
        r = cliente.get(RUTA, headers={'X-Internal-Secret': SECRETO_PRUEBA})
        assert r.status_code == 200
        assert r.json() == {
            'maximo': 1, 'en_curso': 0, 'libres': 1,
            'espera_max_s': ESPERA_HILOS_S, 'en_espera': 0,
        }

    def test_200_con_el_limite_ocupado_sin_esperar_turno(
            self, cliente, limite_controlado, con_secreto):
        # FR2, NFR1: si pasara por el semáforo, esperaría 5 s y daría 503.
        with limite_controlado.turno():
            inicio = time.monotonic()
            r = cliente.get(RUTA, headers={'X-Internal-Secret': SECRETO_PRUEBA})
            transcurrido = time.monotonic() - inicio
        assert r.status_code == 200
        assert (r.json()['en_curso'], r.json()['libres']) == (1, 0)
        assert transcurrido < ESPERA_HILOS_S / 2, transcurrido
        assert limite_controlado.estado()['en_curso'] == 0

    def test_403_sin_cabecera(self, cliente, limite_controlado, con_secreto):
        # FR4.2
        r = cliente.get(RUTA)
        assert r.status_code == 403
        assert SECRETO_PRUEBA not in r.text          # NFR2

    def test_403_con_secreto_incorrecto(self, cliente, limite_controlado, con_secreto):
        # FR4.2, NFR2: ni el enviado ni el esperado aparecen en la respuesta.
        r = cliente.get(RUTA, headers={'X-Internal-Secret': 'otro-valor'})
        assert r.status_code == 403
        assert SECRETO_PRUEBA not in r.text
        assert 'otro-valor' not in r.text

    def test_503_sin_secreto_configurado_y_health_sigue_en_200(
            self, cliente, limite_controlado, monkeypatch):
        # FR4.3: solo este endpoint se niega; el servicio sigue atendiendo.
        monkeypatch.delenv('INTERNAL_SERVICE_SECRET', raising=False)
        monkeypatch.setattr(pipeline, '_classifier_singleton', _ClasificadorCargado())
        r = cliente.get(RUTA, headers={'X-Internal-Secret': SECRETO_PRUEBA})
        assert r.status_code == 503
        assert 'no configurado' in r.json()['detail']
        assert cliente.get('/health/').status_code == 200
